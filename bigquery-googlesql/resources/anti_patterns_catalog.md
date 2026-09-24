# BigQuery and GoogleSQL Anti-Patterns Catalog

This catalog documents common query anti-patterns observed in BigQuery and GoogleSQL codebases. It provides the architectural failure mechanism, slot resource impact, and corrected implementations for each pattern.

```sql
-- Anti-Pattern: Self-Join for Deduplication (High Slot MS, Heavy Shuffle)
SELECT o.*
  FROM `retail.orders` AS o
       INNER JOIN
       (
         SELECT customer_id, MAX(order_timestamp) AS max_ts
           FROM `retail.orders`
          GROUP BY customer_id
       ) AS latest
       ON  o.customer_id     = latest.customer_id
       AND o.order_timestamp = latest.max_ts
```

---

## 1. Unnecessary Full Column Projection (`SELECT *`)

### Mechanical Failure and Risk Boundaries
Capacitor stores table columns in isolated physical chunks on Colossus. Declaring `SELECT *` forces worker slots to request, transfer, and decode every column in the schema, bypassing columnar projection pruning.

- **Persistent Tables:** Scanning unneeded columns inflates memory bandwidth and increases scan costs.
- **External Tables (Strictly Prohibited):** Using `SELECT *` on external tables (BigLake, object tables, Cloud Storage formats, Google Drive, Sheets) introduces severe operational failure risks. External schemas evolve without database control; upstream producers can append wide columns or alter layouts, unexpectedly multiplying scan volume by orders of magnitude or breaking downstream contracts.

### Conditioned Exceptions (When `SELECT *` Is Permissible)
Wildcard projection is valid when conditioned on certainty of correctness:
1. **Verifiably Complete Consumption:** When downstream computations or destination pipelines genuinely require all schema columns.
2. **Localized Intermediate Representations (CTEs and Temp Tables):** Projecting `SELECT *` from localized structures (such as `CREATE TEMP TABLE` or CTEs) is completely permissible because the author explicitly defines, bounds, and isolates the projected schema.

```sql
-- Anti-Pattern 1: Unnecessary column scan on wide persistent table (85 columns read)
SELECT *
  FROM `telemetry.raw_events`
 WHERE event_date = CURRENT_DATE();

-- Anti-Pattern 2: Wildcard scan on external table with uncontrolled schema drift
SELECT *
  FROM `external_lake.partner_events_csv`;

-- Compliant Form 1: Explicit column projection on persistent storage
SELECT event_id, user_id, event_timestamp
  FROM `telemetry.raw_events`
 WHERE event_date = CURRENT_DATE();

-- Compliant Form 2: Localized projection from an author-controlled CTE
WITH filtered_events AS (
  SELECT event_id, user_id, event_timestamp
    FROM `telemetry.raw_events`
   WHERE event_date = CURRENT_DATE()
)
SELECT *
  FROM filtered_events;
```

---

## 2. Function-Wrapped Partition Filtering

### Mechanical Failure
Wrapping a partition column inside a scalar function prevents the logical optimizer from resolving static pruning constraints when compiling queries. The query coordinator fails to prune unselected partition directories, initiating a full table scan. Pruning fails completely.

```sql
-- Non-Compliant Form (Evaluates function on every row; scans entire table)
SELECT COUNT(*)
  FROM `analytics.user_actions`
 WHERE EXTRACT(YEAR FROM event_timestamp) = 2026
   AND EXTRACT(MONTH FROM event_timestamp) = 3;

-- Corrected Form (Static bounds enable compilation-time partition pruning)
SELECT COUNT(*)
  FROM `analytics.user_actions`
 WHERE event_timestamp >= '2026-03-01 00:00:00 UTC'
   AND event_timestamp < '2026-04-01 00:00:00 UTC';
```

---

## 3. Self-Joins for Record Deduplication

### Mechanical Failure
Joining a table with an aggregated subquery of itself requires two full scans of the base relation. Both scans redistribute rows across the network shuffle tier, multiplying total slot compute time. Avoid self-joins.

```sql
-- Non-Compliant Form (Two table scans plus distributed hash join)
SELECT o.order_id, o.customer_id, o.order_amount
  FROM `retail.orders` AS o
       INNER JOIN
       (
         SELECT customer_id, MAX(order_timestamp) AS latest_time
           FROM `retail.orders`
          GROUP BY customer_id
       ) AS m
       ON  o.customer_id     = m.customer_id
       AND o.order_timestamp = m.latest_time;

-- Corrected Form (Single table scan with in-memory window filter)
 SELECT order_id, customer_id, order_amount
   FROM `retail.orders`
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY customer_id
              ORDER BY order_timestamp DESC
        ) = 1;
```

---

## 4. Unpinned Multiple CTE Re-Evaluation

### Mechanical Failure
By default, Common Table Expressions act as inline syntactic macros. When a query references a complex CTE in multiple join branches, BigQuery may re-evaluate the CTE pipeline repeatedly, multiplying compute slots and shuffle memory pressure. Pin shared CTEs.

```sql
-- Non-Compliant Form (May evaluate DailyTotals twice across separate joins)
WITH
  DailyTotals AS (
    SELECT customer_id, SUM(amount) AS total_spent
      FROM `finance.transactions`
     WHERE transaction_date = CURRENT_DATE()
     GROUP BY customer_id
  )
SELECT a.customer_id, a.total_spent, b.credit_limit
  FROM DailyTotals AS a
       LEFT JOIN
       `finance.limits` AS b
       ON a.customer_id = b.customer_id
 UNION ALL
SELECT c.customer_id, c.total_spent, 0
  FROM DailyTotals AS c
 WHERE c.total_spent > 5000.00;

-- Corrected Form (Materializes intermediate state into a temporary table)
CREATE TEMP TABLE DailyTotals
AS (
  SELECT customer_id, SUM(amount) AS total_spent
    FROM `finance.transactions`
   WHERE transaction_date = CURRENT_DATE()
   GROUP BY customer_id
);

SELECT a.customer_id, a.total_spent, b.credit_limit
  FROM DailyTotals AS a
       LEFT JOIN
       `finance.limits` AS b
       ON a.customer_id = b.customer_id
 UNION ALL
SELECT c.customer_id, c.total_spent, 0
  FROM DailyTotals AS c
 WHERE c.total_spent > 5000.00;
```

---

## 5. Unfiltered Cross Joins and Cartesian Expansion

### Mechanical Failure
Omitting join conditions generates the Cartesian product ($M \times N$) of input relations. This intermediate volume exhausts worker RAM buffers, forcing gigabytes of shuffle spill to persistent storage. Spills kill throughput.

```sql
-- Non-Compliant Form (Emits billions of synthetic tuples into shuffle)
SELECT o.order_id, p.promotion_code
  FROM `retail.orders` AS o
       CROSS JOIN
       `retail.promotions` AS p
 WHERE o.order_amount >= p.min_order_value;

-- Corrected Form (Translates condition into an explicit theta join)
SELECT o.order_id, p.promotion_code
  FROM `retail.orders` AS o
       INNER JOIN
       `retail.promotions` AS p
       ON o.order_amount >= p.min_order_value;
```

---

## 6. Shuffling Raw `NUMERIC` Instead of Converting Late

### Mechanical Failure
As documented in the GoogleSQL engine analysis, `NUMERIC` occupies 16 bytes and executes through scalar ALU carry chains. Shuffling raw `NUMERIC` columns doubles network bandwidth compared to 8-byte `FLOAT64` values. Cast early.

```sql
-- Non-Compliant Form (Shuffles 16-byte NUMERIC values across 100M keys)
SELECT account_id,
       CAST(SUM(transaction_numeric) AS FLOAT64) AS total_float
  FROM `finance.ledger`
 GROUP BY account_id;

-- Corrected Form (Converts to FLOAT64 before shuffle when approximate precision suffices)
SELECT account_id,
       SUM(
         CAST(transaction_numeric AS FLOAT64)
       ) AS total_float
  FROM `finance.ledger`
 GROUP BY account_id;
```
*(Note: Maintain raw `NUMERIC` arithmetic throughout when financial currency precision mandates zero decimal rounding drift).*

---

## 7. Projecting Unrounded `FLOAT64` Calculations in Output Tables

### Mechanical Failure
Arithmetic over `FLOAT64` expressions produces IEEE 754 representation artifacts with noisy trailing decimal fractions. Exposing raw, unrounded transformed floats in resulting tables or views clutters downstream consumption and implies false precision. Restrict output precision by wrapping transformed expressions in `ROUND()` calibrated to domain context.

```sql
-- Non-Compliant Form (Emits unrounded IEEE 754 floating-point noise)
CREATE OR REPLACE TABLE `analytics.daily_order_metrics`
AS (
  SELECT customer_id,
         AVG(order_amount)                                     AS avg_order_amount,
         SUM(order_amount * discount_rate) / SUM(order_amount) AS effective_discount_rate
    FROM `retail.orders`
   GROUP BY customer_id
);

-- Corrected Form (Rounds output fields to sensible domain precision)
CREATE OR REPLACE TABLE `analytics.daily_order_metrics`
AS (
  SELECT customer_id,
         ROUND(AVG(order_amount), 2)                                     AS avg_order_amount,
         ROUND(SUM(order_amount * discount_rate) / SUM(order_amount), 4) AS effective_discount_rate
    FROM `retail.orders`
   GROUP BY customer_id
);
```

---

## 8. The `NOT IN` Subquery with `NULL` Values

### Mechanical Failure
Under ANSI SQL three-valued logic, boolean comparisons against `NULL` yield `UNKNOWN`. The expression `x NOT IN (val1, val2, NULL)` expands logically to the conjunction `x != val1 AND x != val2 AND x != NULL`. Because `x != NULL` evaluates to `UNKNOWN`, the conjoined boolean predicate can never evaluate to `TRUE`. If the subquery in a `NOT IN` clause produces even a single `NULL` value (or if the evaluated column is nullable), the entire `NOT IN` predicate evaluates to `UNKNOWN` or `FALSE` for every candidate row. The query returns zero rows silently without throwing an error.

```sql
-- Non-Compliant Form (Returns zero rows if churned_customers contains any NULL customer_id)
SELECT c.customer_id, c.customer_name
  FROM `retail.customers` AS c
 WHERE c.customer_id NOT IN (
         SELECT customer_id
           FROM `retail.churned_customers`
       );

-- Corrected Form 1: NOT EXISTS preserves correct set exclusion semantics
SELECT c.customer_id, c.customer_name
  FROM `retail.customers` AS c
 WHERE NOT EXISTS(
             SELECT 1
               FROM `retail.churned_customers` AS ch
              WHERE ch.customer_id = c.customer_id
       );

-- Corrected Form 2: Anti-join via LEFT JOIN ... WHERE IS NULL
SELECT c.customer_id, c.customer_name
  FROM `retail.customers` AS c
       LEFT JOIN
       `retail.churned_customers` AS ch
       ON c.customer_id = ch.customer_id
 WHERE ch.customer_id IS NULL;
```

---

## 9. Comma `UNNEST` Silently Dropping Rows on Empty or NULL Arrays

### Mechanical Failure
The comma cross join syntax `FROM table, UNNEST(array_column)` executes an inner relational product between each parent row and the unnested elements of its array. If `array_column` is an empty array (`[]`) or evaluates to `NULL`, unnesting produces zero child tuples. Consequently, the inner join drops the entire parent row from the query output. When calculating parent-level totals or reporting across all entities, this behavior silently discards entities with zero child events.

```sql
-- Non-Compliant Form (Silently drops customers who have placed zero orders)
SELECT c.customer_id, t.transaction_id, t.transaction_amount
  FROM `retail.customers` AS c,
       UNNEST(c.transactions) AS t;

-- Corrected Form (LEFT JOIN preserves parent customer records lacking transactions)
SELECT c.customer_id, t.transaction_id, t.transaction_amount
  FROM `retail.customers` AS c
       LEFT JOIN
       UNNEST(c.transactions) AS t;
```

---

## 10. Relying on Non-Enforced Primary Keys and Duplication Fan-Out

### Mechanical Failure
GoogleSQL permits declaring `PRIMARY KEY (column) NOT ENFORCED` on persistent tables. However, the storage subsystem does not validate uniqueness during ingest (`INSERT`, `LOAD DATA`, or `MERGE`). Upstream ingestion pipelines can append duplicate records without compiler or storage errors.

Crucially, the BigQuery query optimizer leverages declared primary and foreign key constraints as trusted metadata to eliminate joins, reorder join trees, and push down aggregates. If duplicate records exist in a table declared with a non-enforced primary key:
1. Downstream joins may produce unexpected row fan-out, multiplying metric totals.
2. The query optimizer may eliminate dimension joins under the false assumption that every child row joins to exactly one parent row, silently corrupting analytical metrics.

Always enforce uniqueness upstream, or explicitly deduplicate candidate tables prior to join evaluation:

```sql
-- Non-Compliant Form (Relies on non-enforced primary key; fans out on duplicates)
SELECT o.order_id, c.customer_id, c.customer_name
  FROM `retail.orders` AS o
       INNER JOIN
       `retail.customers` AS c
       ON o.customer_id = c.customer_id;

-- Corrected Form (Explicitly deduplicates on primary key prior to joining)
WITH
  unique_customers AS (
     SELECT customer_id, customer_name
       FROM `retail.customers`
    QUALIFY ROW_NUMBER() OVER (
              PARTITION BY customer_id
                  ORDER BY updated_at DESC
            ) = 1
  )
SELECT o.order_id, c.customer_id, c.customer_name
  FROM `retail.orders` AS o
       INNER JOIN
       unique_customers AS c
       ON o.customer_id = c.customer_id;
```

---

## 11. DML and Concurrency Anti-Patterns

### 11.1 High-Frequency Single-Row Mutations
Executing thousands of standalone `INSERT`, `UPDATE`, or `DELETE` statements exhausts project slot quotas. Each statement creates a separate query job compilation DAG and writes small uncoalesced mutation deltas to Capacitor metadata. Slot starvation follows.
Stage incoming mutation records in memory or micro-batch staging tables. Then apply a single set-based `MERGE` statement or stream records through the Storage Write API.

```sql
-- Non-Compliant Form (Iterative single-row updates consume massive slot quotas)
FOR row IN (SELECT order_id, new_status FROM `stage.order_updates`) DO
  UPDATE `sales.orders`
     SET status = row.new_status
   WHERE order_id = row.order_id;
END FOR;

-- Corrected Form (Single atomic set-based MERGE)
MERGE `sales.orders` AS target
USING `stage.order_updates` AS source
   ON target.order_id = source.order_id
 WHEN MATCHED THEN
   UPDATE SET target.status = source.new_status;
```

### 11.2 Fatal Double-Rollback in Procedural Scripts
BigQuery automatically cancels active multi-statement transactions when optimistic concurrency control conflicts occur. Executing an unshielded `ROLLBACK TRANSACTION` statement inside an exception block fails with error code 400 when the runtime already terminated the transaction. The unhandled exception aborts the procedural script prematurely.
Wrap rollback statements within a nested exception block to absorb redundant rollback signals safely.

```sql
-- Non-Compliant Form (Throws 400 when transaction already rolled back)
BEGIN
  BEGIN TRANSACTION;
  UPDATE `finance.ledger` SET balance_amt = balance_amt - 100 WHERE account_id = 'A';
  UPDATE `finance.ledger` SET balance_amt = balance_amt + 100 WHERE account_id = 'B';
  COMMIT TRANSACTION;
EXCEPTION WHEN ERROR THEN
  ROLLBACK TRANSACTION;
  RAISE;
END;

-- Corrected Form (Absorbs redundant rollback signals gracefully)
BEGIN
  BEGIN TRANSACTION;
  UPDATE `finance.ledger` SET balance_amt = balance_amt - 100 WHERE account_id = 'A';
  UPDATE `finance.ledger` SET balance_amt = balance_amt + 100 WHERE account_id = 'B';
  COMMIT TRANSACTION;
EXCEPTION WHEN ERROR THEN
  BEGIN
    ROLLBACK TRANSACTION;
  EXCEPTION WHEN ERROR THEN
    -- Transaction was already cancelled by engine
  END;
  RAISE;
END;
```

### 11.3 MERGE Partition Purge Trap
Combining partition boundary predicates in the `ON` join clause with a `WHEN NOT MATCHED BY SOURCE THEN DELETE` clause purges historical data. Target rows failing the `ON` condition classify as unmatched by the source relation. When an engineer places lookback bounds in the `ON` clause, all historical partitions evaluate to false and undergo deletion.
Confine the `ON` condition to key equality. Place partition lookback filters directly on the `WHEN NOT MATCHED BY SOURCE` clause.

```sql
-- Non-Compliant Form (Places partition boundary in ON clause, purging historical partitions)
MERGE `telemetry.daily_events` AS target
USING `staging.events_delta` AS source
   ON target.event_date >= '2026-03-24'
  AND target.event_id   = source.event_id
 WHEN MATCHED THEN
   UPDATE SET target.payload = source.payload
 WHEN NOT MATCHED BY SOURCE THEN
   DELETE;

-- Corrected Form (Bounds purge scope explicitly on the match clause)
MERGE `telemetry.daily_events` AS target
USING `staging.events_delta` AS source
   ON target.event_date = source.event_date
  AND target.event_id   = source.event_id
 WHEN MATCHED THEN
   UPDATE SET target.payload = source.payload
 WHEN NOT MATCHED BY SOURCE AND target.event_date = '2026-03-24' THEN
   DELETE;
```

---

## 12. Machine Learning and Generative AI Anti-Patterns

### 12.1 Unbounded Full-Table Foundation Model Inference
Calling `AI.GENERATE` or remote Vertex AI models directly over large unpartitioned tables dispatches millions of external API calls. This saturates project API quotas, triggers HTTP 429 timeouts, and incurs runaway inference billing costs.
Filter candidate tables with explicit partition boundaries before running foundation models.

```sql
-- Non-Compliant Form (Dispatches 50 million API calls over unpartitioned table)
SELECT customer_id,
       AI.GENERATE(feedback_txt, connection_id => 'us.vertex_conn') AS sentiment
  FROM `analytics.customer_feedback`;

-- Corrected Form (Filters recent unanalyzed records with explicit bounds)
SELECT customer_id,
       AI.GENERATE(feedback_txt, connection_id => 'us.vertex_conn') AS sentiment
  FROM `analytics.customer_feedback`
 WHERE feedback_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
   AND sentiment_status_cd = 'PENDING';
```

### 12.2 Missing Window Specification on Preprocessing Scalers
Built-in feature scalers such as `ML.STANDARD_SCALER` compute mean and variance over the full training partition. Omitting the mandatory empty analytic clause `OVER ()` triggers a compilation syntax error.
Supply the empty `OVER ()` analytic clause on all Tier 1 distribution transformers in the `TRANSFORM` definition.

```sql
-- Non-Compliant Form (Syntax error: scaler requires empty window specification)
CREATE OR REPLACE MODEL `ml.risk_model`
TRANSFORM (
  ML.STANDARD_SCALER(income_amt) AS scaled_income,
  is_defaulted_ind
)
OPTIONS (model_type = 'LOGISTIC_REG', input_label_cols = ['is_defaulted_ind'])
AS SELECT income_amt, is_defaulted_ind FROM `lending.loans`;

-- Corrected Form (Valid analytic window specification)
CREATE OR REPLACE MODEL `ml.risk_model`
TRANSFORM (
  ML.STANDARD_SCALER(income_amt) OVER () AS scaled_income,
  is_defaulted_ind
)
OPTIONS (model_type = 'LOGISTIC_REG', input_label_cols = ['is_defaulted_ind'])
AS SELECT income_amt, is_defaulted_ind FROM `lending.loans`;
```

### 12.3 Training-Serving Skew from External Ad-Hoc Transforms
Preprocessing features in upstream SQL scripts before training decouples scaling parameters from the compiled model. Production inference pipelines must replicate identical transformations manually. Any divergence in rounding, null imputation, or categorical mappings skews prediction scores.
Embed all feature scaling and encoding steps directly inside the model `TRANSFORM` clause.

```sql
-- Non-Compliant Form (Decoupled transforms force duplicate inference logic)
CREATE TEMP TABLE PreppedFeatures AS (
  SELECT (age - 35.0) / 12.0 AS scaled_age, target_val FROM `ml.training_data`
);
CREATE MODEL `ml.model` OPTIONS (model_type = 'LINEAR_REG', input_label_cols = ['target_val'])
AS SELECT * FROM PreppedFeatures;

-- Corrected Form (Embeds preprocessing into compiled model artifact)
CREATE MODEL `ml.model`
TRANSFORM (
  ML.STANDARD_SCALER(age) OVER () AS scaled_age,
  target_val
)
OPTIONS (model_type = 'LINEAR_REG', input_label_cols = ['target_val'])
AS SELECT age, target_val FROM `ml.training_data`;
```

### 12.4 Point-in-Time Temporal Feature Leakage
Joining predictive event tables to current entity snapshots incorporates feature values generated after the target event occurred. The resulting model learns from future information, producing inflated training accuracy that fails in production.
Execute point-in-time joins using `ML.ENTITY_FEATURES_AT_TIME` to select only feature snapshots that preceded each event.

```sql
-- Non-Compliant Form (Joins future feature values to historic events)
SELECT t.transaction_id, f.customer_credit_score
  FROM `finance.transactions` AS t
  JOIN `analytics.customer_daily_features` AS f
    ON t.customer_id = f.customer_id;

-- Corrected Form (Enforces strict point-in-time temporal boundaries)
SELECT entity.transaction_id, features.customer_credit_score
  FROM ML.ENTITY_FEATURES_AT_TIME(
         TABLE `finance.transactions`,
         'customer_id',
         'transaction_ts',
         TABLE `analytics.customer_daily_features`,
         'snapshot_ts',
         num_rows => 1
       ) AS entity
  JOIN `analytics.customer_daily_features` AS features
    ON entity.customer_id = features.customer_id
   AND entity.snapshot_ts = features.snapshot_ts;
```

### 12.5 CTE Inlining of Remote Model Endpoints
BigQuery treats Common Table Expressions as inline logical views. Referencing a CTE that contains `AI.GENERATE` across multiple query branches invokes remote model APIs repeatedly for identical input rows.
Materialize the intermediate inference results into a temporary table to evaluate remote model endpoints once.

```sql
-- Non-Compliant Form (Inlines CTE, invoking external API multiple times)
WITH Embeddings AS (
  SELECT item_id, AI.EMBED(item_desc, connection_id => 'us.conn') AS vec
    FROM `catalog.items`
)
SELECT a.item_id, b.item_id
  FROM Embeddings AS a
  JOIN Embeddings AS b
    ON AI.SIMILARITY(a.vec, b.vec) > 0.85;

-- Corrected Form (Materializes inference results to evaluate API once)
CREATE TEMP TABLE TempEmbeddings AS (
  SELECT item_id, AI.EMBED(item_desc, connection_id => 'us.conn') AS vec
    FROM `catalog.items`
);
SELECT a.item_id, b.item_id
  FROM TempEmbeddings AS a
  JOIN TempEmbeddings AS b
    ON AI.SIMILARITY(a.vec, b.vec) > 0.85;
```

---

## 13. Graph and GQL Anti-Patterns
 
### 13.1 Unbounded Path Quantifiers in Graph Traversals
Traversing property graphs with unbounded path quantifiers such as `-[e:Transfers]->*` instructs the engine to enumerate all possible paths across cyclic networks. Combinatorial expansion exhausts Borg slot memory.
Enforce finite path lengths with bounded quantifiers `{m, n}` and apply the cycle prevention filter `WHERE IS_ACYCLIC(path)`.

```sql
-- Non-Compliant Form (Unbounded traversal causes combinatorial explosion)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH (src:Account)-[e:Transfers]->*(dst:Account)
         RETURN src.account_id AS src_id, dst.account_id AS dst_id
       );

-- Corrected Form (Bounded traversal with cycle prevention)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH p = (src:Account)-[e:Transfers]->{1, 4}(dst:Account)
         WHERE IS_ACYCLIC(p)
         RETURN src.account_id AS src_id, dst.account_id AS dst_id, PATH_LENGTH(p) AS hops
       );
```

### 13.2 Projecting Raw Graph Element Tokens
Graph node and edge variables reference complex internal element descriptors. Attempting to project raw element tokens directly in the `RETURN` clause triggers query compilation failures.
Project explicit scalar properties, serialize elements to JSON via `TO_JSON()`, or invoke element inspection functions such as `LABELS()` and `ELEMENT_ID()`.

```sql
-- Non-Compliant Form (Compilation error: cannot return raw graph node element directly)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH (n:Account)
         RETURN n
       );

-- Corrected Form (Projects scalar properties and element identifiers)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH (n:Account)
         RETURN n.account_id, LABELS(n) AS account_labels, ELEMENT_ID(n) AS node_guid
       );
```

### 13.3 Property Lookup Trap in Three-Valued Logic
Comparing graph element properties using standard equality against `NULL` evaluates to unknown. The engine silently discards nodes with missing property definitions.
Check property definitions explicitly using `IS NOT NULL` or coalesce expressions.

```sql
-- Non-Compliant Form (Drops nodes where credit_tier property is missing)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH (n:Account)
         WHERE n.credit_tier = NULL
         RETURN n.account_id
       );

-- Corrected Form (Checks nullness explicitly)
SELECT *
  FROM GRAPH_TABLE(
         FinGraph
         MATCH (n:Account)
         WHERE n.credit_tier IS NULL
         RETURN n.account_id
       );
```

### 13.4 Horizontal Subquery Scope Leakage
Relational subqueries placed in an external `SELECT` clause cannot access path variables declared within `GRAPH_TABLE`. The engine cannot resolve graph element references outside the graph pattern scope.
Extract all required path properties within the `RETURN` clause before applying external relational operations.

```sql
-- Non-Compliant Form (Subquery cannot access internal path variable p)
SELECT g.src_id,
       (SELECT COUNT(*) FROM UNNEST(NODES(p))) AS node_count
  FROM GRAPH_TABLE(
         FinGraph
         MATCH p = (src:Account)-[e:Transfers]->{1, 3}(dst:Account)
         RETURN src.account_id AS src_id
       ) AS g;

-- Corrected Form (Computes path metric inside GRAPH_TABLE RETURN clause)
SELECT g.src_id, g.node_count
  FROM GRAPH_TABLE(
         FinGraph
         MATCH p = (src:Account)-[e:Transfers]->{1, 3}(dst:Account)
         RETURN src.account_id AS src_id, PATH_LENGTH(p) + 1 AS node_count
       ) AS g;
```

