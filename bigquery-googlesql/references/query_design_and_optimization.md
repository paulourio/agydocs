# Large-Scale Query Design Framework and Optimization Guide

This document provides a seven-step engineering methodology for designing, structuring, and optimizing analytical queries in GoogleSQL and BigQuery. It details column pruning, join optimization, window function deduplication, Common Table Expression materialization, and auxiliary query acceleration engines.

```sql
-- Optimal Query Blueprint: Partition Pruning, Early Filter, and QUALIFY
 SELECT customer_id,
        order_date,
        total_amount
   FROM `enterprise.orders`
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) -- Prunes partitions
    AND status = 'COMPLETED'                                    -- Prunes clustered blocks
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY customer_id
              ORDER BY total_amount DESC
        ) <= 3
```

---

## 1. The Seven-Step Query Design Framework

Constructing queries that execute efficiently over billions of rows requires deliberate planning before drafting code.

```
Design Pipeline:
1. Physical Access -> 2. Minimal Projection -> 3. Partition Pruning -> 4. Early Aggregation ->
5. Join Topography -> 6. Windowing (QUALIFY) -> 7. Plan Audit & Dry Run
```

### Step 1: Storage Contract and Access Pattern Definition
Analyze the underlying physical layout before writing expressions:
- Identify table partitioning keys (`DATE`, `TIMESTAMP`, or integer range).
- Identify clustering columns and their declared order ($C_1, C_2, C_3, C_4$).
- Confirm whether `require_partition_filter = true` is enabled on the schema.

### Step 2: Minimal Column Projection (Pruning Columns)
Because Capacitor is a columnar storage engine, reading an unneeded column incurs unnecessary network I/O from Colossus to worker slots:
- Prohibit unnecessary `SELECT *` in production queries. Wildcard projection is permissible only when conditioned on certainty of correctness: when all schema columns are verifiably required, or when selecting from localized intermediate structures (such as CTEs and temporary tables) where the developer maintains complete schema control.
- Strictly avoid `SELECT *` on external tables (BigLake, Cloud Storage, Google Drive/Sheets) because uncontrolled external schema drift can introduce unexpected columns and cause severe scan inflation.
- Prune unused struct fields using `SELECT * EXCEPT (unneeded_field)` or explicit field selection (`user.address.country`).
- Never unnest repeated arrays unless child fields are required for downstream filters or joins.
- Enforce sensible precision on transformed `FLOAT64` projections: When computing, aggregating, or transforming floating-point metrics (such as ratios, averages, or percentage growth) for resulting destination tables or views, wrap expressions in `ROUND()`. Select precision grounded in business context (such as 2 decimal places for financial amounts or 4 places for conversion rates) to eliminate uninformative IEEE 754 noise without exaggerating precision.

### Step 3: Filter Placement and Pruning Verification
Filter predicates must align with storage structures:
- Ensure the `WHERE` clause applies static constraints to the primary partitioning column.
- Order secondary filter predicates to match clustering column declarations. Filtering on $C_1$ yields the highest block pruning; filtering on $C_2$ without $C_1$ yields significantly reduced pruning.
- Avoid wrapping partition columns in functions (for example, use `WHERE event_timestamp >= TIMESTAMP('2026-01-01')` instead of `WHERE EXTRACT(YEAR FROM event_timestamp) = 2026`). Wrapping columns in functions prevents metadata pruning at compilation.

### Step 4: Cardinality Reduction Before Shuffling
Reduce record volume before transmitting rows across the network:
- Push filter predicates into the earliest possible Common Table Expression or subquery.
- Aggregate metrics early. If a query calculates customer-level metrics from a 500-million-row transaction table before joining with an account table, aggregate transactions down to distinct customer IDs first. Early aggregation replaces a 500-million-row shuffle join with a compact hash join.
- Eliminate join overcounting with multi-level aggregation: When queries join one-to-many parent and child tables (such as customers to orders), child rows duplicate parent attributes. Wrapping parent metrics in multi-level aggregates (such as `AVG(ANY_VALUE(parent_metric) GROUP BY parent_id)`) guarantees each parent value contributes once without intermediate subquery joins.

### Step 5: Join Topography and Sizing
Structure joins according to table volume:
- Place the largest relation on the left side of the `JOIN` and the smaller relation on the right side.
- Filter and prune dimension tables to allow the query optimizer to select a Broadcast Hash Join (under $100\text{ MB}$).
- Avoid join conditions on high-cardinality string columns; prefer integer surrogate keys or hashed integer identifiers to minimize memory hash table size.

### Step 6: Windowing and Deduplication
Replace expensive self-joins and subqueries with window functions:
- Use `QUALIFY ROW_NUMBER() OVER (PARTITION BY key ORDER BY ts DESC) = 1` for deduplication. This construct evaluates within a single analytical pass without requiring self-joins or nested CTEs.

### Step 7: Execution Plan Audit and Dry Run
Validate the query prior to execution:
- Run a dry-run query (`bq query --dry_run`) to inspect `totalBytesProcessed`.
- After execution, inspect total slot milliseconds, stage execution breakdowns, and verify that `Shuffle Spilled to Disk` is zero bytes.

---

## 2. Common Table Expressions vs. Temp Tables vs. Subqueries

Managing intermediate results requires balancing human readability against distributed execution costs.

```
Relational Abstraction Hierarchy:
Inline Subquery: Syntactically compact, hard to read, planner can optimize freely.
Common Table Expression (CTE): High readability, modular, non-materialized by default.
Temporary Table: Explicit materialization barrier, writes to disk, resets stats.
```

### 2.1 The CTE Re-Evaluation Risk
By default, BigQuery treats CTEs as non-materialized inline query views.
- If a query references `CTE_A` once, the planner inlines the logic into the execution DAG.
- If a query references `CTE_A` multiple times across separate joins, the planner may execute the entire subquery DAG of `CTE_A` multiple times, multiplying slot computation and byte scan costs.

### 2.2 Optimizer Subquery Inlining vs Temporary Tables
BigQuery's query planner evaluates Common Table Expressions dynamically. The optimizer decides whether to inline the subquery expression or cache intermediate tuples into shuffle memory based on subquery cost and cardinality estimates. When an intermediate reduction is heavy and referenced multiple times across disparate joins, create a temporary table (`CREATE TEMP TABLE ... AS SELECT ...`) to guarantee that the computation runs only once.

```sql
CREATE TEMP TABLE DailyAggregates
AS (
  SELECT customer_id, SUM(amount) AS daily_spend
    FROM `retail.transactions`
   WHERE transaction_date = CURRENT_DATE()
   GROUP BY customer_id
);

SELECT a.customer_id, a.daily_spend, b.credit_limit
  FROM DailyAggregates AS a
       INNER JOIN
       `retail.accounts` AS b
       ON a.customer_id = b.customer_id
 WHERE a.daily_spend > b.credit_limit;
```

### 2.3 When to Use Temporary Tables
In multi-statement scripts or stored procedures, use `CREATE TEMP TABLE` under the following conditions:
- **High-Reuse Intermediate Results:** The intermediate relation is referenced by three or more independent queries.
- **Pipeline Checkpointing:** Breaking an extremely complex DAG ($> 15$ stages) into discrete steps prevents coordinator planning timeouts and slot memory exhaustion.
- **Statistics Recalculation:** Materializing intermediate rows into a temporary table allows the optimizer to collect fresh cardinality statistics, resulting in better join algorithm selection in subsequent statements.

| Relational Container | Execution Lifecycle | Memory / Disk Impact | Best Use Case |
| :--- | :--- | :--- | :--- |
| **CTE (Default)** | Query statement scope | Inlined into DAG | Logical structuring, single-use readability |
| **CTE (Optimizer-Cached)** | Query statement scope | Retained in shuffle | Automatic engine caching across multi-branch reads |
| **Temporary Table** | Script / Session scope | Written to Colossus | Multi-statement scripts, pipeline checkpointing |
| **View (Standard)** | Persistent catalog | Inlined on invocation | Logical schema abstraction, security access control |
| **Materialized View** | Persistent catalog | Precomputed storage | Real-time incremental aggregation acceleration |

---

## 3. Advanced Query Optimization Techniques

### 3.1 Approximate Aggregations
For exploratory data analysis or dashboards spanning hundreds of millions of records, exact distinct counts introduce massive shuffle overhead. Approximate functions execute in a fraction of slot time using bounded streaming algorithms:
- **`APPROX_COUNT_DISTINCT(x)`:** Computes cardinalities using the HyperLogLog++ algorithm with typical statistical error within $1\%$.
- **`APPROX_QUANTILES(x, 100)`:** Calculates percentiles using bounded memory buffers.
- **`APPROX_TOP_COUNT(x, 10)`:** Returns top $K$ most frequent items using the Space-Saving sketch algorithm.

```sql
SELECT APPROX_COUNT_DISTINCT(user_id)        AS estimated_active_users,
       APPROX_QUANTILES(session_duration, 4) AS duration_quartiles
  FROM `telemetry.user_sessions`
 WHERE session_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
```

### 3.2 BigQuery Search Indexes
For semi-structured text search over large log tables, regular expressions (`REGEXP_CONTAINS`) scan every byte of the column. Creating a search index eliminates raw byte scans:

```sql
-- Query logs using the indexed SEARCH() function over partition-pruned storage
SELECT log_timestamp, severity, message
  FROM `telemetry.application_logs`
 WHERE SEARCH(message, 'NullPointerException `UserAuthService`')
```

### 3.3 BI Engine In-Memory Acceleration
BigQuery BI Engine provisions dedicated RAM capacity in selected project regions:
- Frequently accessed tables and materialized views are cached in memory in a columnar, compressed format.
- Queries matching supported SQL operations execute with sub-second latency, bypassing Colossus storage reads and remote shuffle stages entirely.
- In query plans, accelerated stages report `BI Engine Mode: FULL`. If certain expressions are unsupported, the plan reports `BI Engine Mode: PARTIAL`, falling back to standard Borg slot workers.

### 3.4 Shuffle Boundary Type-Slimming vs. Aggregate Reduction Cardinality
Physical execution costs depend on where type conversions occur relative to the distributed shuffle boundary. Because `SUM(NUMERIC)` and `SUM(FLOAT64)` maintain distinct numerical precision and overflow invariants, the optimizer cannot push conversion functions through an aggregation operator.

Query planners balance input computation against network shuffle volume using a two-stage cost model:
$$\text{Cost} = N \cdot C_{\text{compute}} + G \cdot S_{\text{shuffle}}$$
where $N$ represents raw input rows, $G$ represents grouped intermediate rows written to shuffle, and $R = N / G$ represents the aggregation reduction ratio.

Engineers choose conversion placement by evaluating $R$:

- **High Reduction Ratio ($R \gg 1$, e.g., $10^6 \to 10^2$ rows):**
  Accumulate raw metrics in their native storage type and evaluate conversions during the final projection phase:
  ```sql
  -- Evaluates CAST once per output group (G times) rather than per row (N times)
  SELECT category_id,
         CAST(SUM(amount_num) AS FLOAT64) AS category_revenue_num
    FROM `retail.transactions`
   GROUP BY category_id;
  ```
  Evaluating conversions inside the aggregate (`SUM(CAST(...))`) forces the engine to run $N$ conversion operations during stage 1 input processing. When groups collapse millions of rows into dozens, shuffle savings approach zero, and upfront casting burns slot processing time unnecessarily.

- **Low Reduction with Heavy Network Shuffle ($R \approx 1$, e.g., high-cardinality keys or small unnested arrays):**
  Convert wide decimal structures to compact numeric representations prior to shuffle:
  ```sql
  -- Slims 16-byte NUMERIC down to 8-byte FLOAT64 before cross-network shuffle
  SELECT user_id,
         order_id,
         SUM(CAST(item_price_num AS FLOAT64)) AS order_total_num
    FROM `retail.orders`
   GROUP BY user_id, order_id;
  ```
  Converting 16-byte `NUMERIC` values to 8-byte `FLOAT64` values prior to aggregation slims the intermediate payload emitted into the Jupiter shuffle tier. When shuffle volume is heavy and reduction per worker is minimal, halving wire serialization and compression workloads offsets the upfront CPU conversion cost.

---

## 4. Related References and Operational Tooling

- **Stage Diagnostics:** Consult [Query Planning and Execution](query_planning_and_execution.md) for slot contention triage.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for sargable layouts.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](../resources/anti_patterns_catalog.md) for concrete refactoring examples.
- **Workflows:** Consult [Engineering Workflows](engineering_workflows.md) for step-by-step query design procedures.

