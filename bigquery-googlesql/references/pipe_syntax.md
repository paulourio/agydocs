# BigQuery Pipe Query Syntax Specification

This document provides a technical specification of BigQuery Pipe Query Syntax (`|>`). It details the linear dataflow execution paradigm, the complete suite of supported pipe operators, statement integration with Data Definition Language (DDL) and Data Manipulation Language (DML), and practical debugging protocols.

```sql
FROM `project.dataset.orders`
|> WHERE order_status = 'COMPLETED'
|> EXTEND order_amount * 0.90 AS discounted_total
|> AGGREGATE
     COUNT(*)              AS total_orders,
     SUM(discounted_total) AS total_revenue
   GROUP BY customer_id
|> WHERE total_revenue > 1000.00
|> ORDER BY total_revenue DESC
|> LIMIT 50
```

---

## 1. The Pipe Paradigm: Linear Relational Dataflow

Classic SQL forces an inverted evaluation sequence where column projections appear textually prior to relational inputs. In contrast, BigQuery Pipe Syntax enforces a top-to-bottom algebraic dataflow starting directly from a relational data source.

```
Relational Dataflow Stream:
Source (`FROM`) -> Filter (`WHERE`) -> Derive (`EXTEND`) -> Group (`AGGREGATE`) -> Limit (`LIMIT`)
```

### 1.1 Structural Invariants
- **Source Initialization:** Every pipeline begins with a relational data source, typically `FROM table_name` or a parenthesized query expression `(SELECT ...)`.
- **Sequential Composition:** Each subsequent operation is prefixed by `|>`. The operator receives the relation emitted by the immediate upstream operator as its implicit input.
- **Lexical Scoping:** An operator can address only columns present in the incoming relation. Columns excluded by upstream operators cannot be referenced.
- **Unified Filtering:** The `|> WHERE` operator serves as a universal relational filter, replacing `WHERE`, `HAVING`, and `QUALIFY` based solely on where it appears in the pipeline.

### 1.2 Relational Pipes vs. Scalar Chained Function Calls
Engineers must maintain the structural distinction between relational pipe operators and scalar chained function calls:
- **Relational Pipes (`|>`):** Transform and repartition table streams across query execution stages. Each pipe operator takes a relation as input and emits a modified relation.
- **Scalar Chained Calls (`.`):** Transform individual scalar values from left to right within an expression (such as `(email).TRIM().LOWER()`).

These two features compose harmoniously. In pipe queries, scalar function chains evaluate inside `|> EXTEND`, `|> SET`, and `|> AGGREGATE` expressions:

```sql
FROM `retail.orders`
|> WHERE order_status = 'COMPLETED'
|> EXTEND (customer_email).TRIM().LOWER()                AS clean_email,
          (order_total * (1.0 - discount_rate)).ROUND(2) AS net_total
|> AGGREGATE (net_total).SUM().ROUND(2) AS total_revenue
   GROUP BY clean_email
```

---

## 2. BigQuery Pipe Operator Suite

BigQuery supports a curated suite of pipe operators tailored to distributed data warehousing workloads.

### 2.1 Filtering and Projection Operators

#### 1. `|> WHERE`
Filters the input relation using a boolean predicate. Placing `|> WHERE` after `FROM` filters base rows; placing it after `AGGREGATE` filters aggregated groups; placing it after `EXTEND` filters window calculations.

```sql
FROM `retail.produce`
|> EXTEND ROW_NUMBER() OVER (
            PARTITION BY category
                ORDER BY sales_volume DESC
          ) AS category_rank
|> WHERE category_rank <= 3
```

#### 2. `|> SELECT`
Produces a new relation containing only the listed columns, pruning unlisted attributes from the downstream stream.

```sql
FROM `retail.orders`
|> SELECT order_id, customer_id, total_amount * 0.90 AS discounted_amount
```

#### 3. `|> EXTEND`
Appends new computed columns to the input relation without dropping existing attributes. It serves as the primary mechanism for declaring analytical window calculations and derived values prior to filtering.

```sql
FROM `corp.employees`
|> EXTEND AVG(salary) OVER (PARTITION BY department_id)          AS dept_avg_salary,
          salary - AVG(salary) OVER (PARTITION BY department_id) AS salary_deviation
```

#### 4. `|> SET`
Replaces the values of existing columns in-place using new evaluation expressions, functionally matching classic `SELECT * REPLACE (expr AS col)`.

```sql
FROM `web.sessions`
|> SET session_duration_seconds = GREATEST(session_duration_seconds, 0)
```

#### 5. `|> DROP`
Removes specified columns from the input relation without requiring an exhaustive column projection list, functionally matching classic `SELECT * EXCEPT (col1, col2)`.

```sql
FROM `finance.transactions`
|> DROP internal_tracking_token, transient_hash
```

#### 6. `|> RENAME`
Renames specified columns in the input relation: `|> RENAME old_name AS new_name [, ...]`.

```sql
FROM `retail.customers`
|> RENAME id AS customer_id, addr AS delivery_address
```

#### 7. `|> AS`
Assigns a new table alias to the input relation, invalidating prior table aliases. This operator is essential after schema-synthesizing operations prior to joins.

```sql
FROM `retail.orders`
|> AGGREGATE SUM(amount) AS customer_total
   GROUP BY customer_id
|> AS o
|> INNER JOIN
   `retail.customers` AS c
   ON o.customer_id = c.customer_id
```

#### 8. `|> DISTINCT`
Prunes duplicate rows across all visible columns while preserving current table aliases.

```sql
FROM `telemetry.page_views`
|> SELECT user_id, page_path
|> DISTINCT
```

---

### 2.2 Aggregation and Windowing Operators

#### 9. `|> AGGREGATE`
Performs explicit relational aggregation over declared grouping keys or across the entire table. Grouping columns are projected automatically into the resulting relation.

The operator natively supports multi-level aggregation expressions. Inner `GROUP BY` modifiers nest inside aggregate arguments to compute hierarchical summaries directly within the linear pipeline:

```sql
-- bqfmt: skip
FROM `retail.produce`
|> AGGREGATE
     COUNT(*)          AS total_items,
     SUM(sales_volume) AS total_sales ASC
   GROUP AND ORDER BY category, item_name DESC;

-- Multi-level aggregation in pipe syntax: Average daily revenue per region
FROM `retail.orders`
|> WHERE order_status = 'COMPLETED'
|> AGGREGATE ROUND(AVG(SUM(order_amount) GROUP BY DATE(order_timestamp)), 2) AS avg_daily_revenue
   GROUP BY region_code;
```

---

### 2.3 Relational Joins and Set Operations

#### 10. `|> JOIN`
Merges the incoming pipeline stream (as the left input) with a right-hand relation: `|> [join_type] JOIN from_item [[AS] alias] [{ ON bool_expr | USING (column_list) }]`.

```sql
FROM `retail.orders` AS o
|> LEFT JOIN
   `retail.customers` AS c
   ON o.customer_id = c.customer_id
|> LEFT JOIN
   UNNEST(o.line_items) AS items
```

#### 11. `|> CALL`
Invokes a Table-Valued Function (TVF), passing the pipe input table implicitly as the first relational argument.

```sql
FROM `sensor.raw_metrics`
|> CALL CleanseAnomalies(3.5)
|> CALL NormalizeTimestamps('UTC')
```

#### 12. `|> UNION`, `|> INTERSECT`, `|> EXCEPT`
Executes set operations between the pipeline stream and one or more parenthesized query blocks: `|> SET_OP { ALL | DISTINCT } [ BY NAME ] (query) [, ...]`.

```sql
FROM `sales.north_america`
|> UNION ALL BY NAME
   (
     SELECT order_id, order_date, order_amount
       FROM `sales.europe`
   ),
   (
     SELECT order_id, order_date, order_amount
       FROM `sales.asia`
   )
```

---

### 2.4 Reshaping, Sampling, and Scoping Operators

#### 13. `|> PIVOT` and `|> UNPIVOT`
Applies row-to-column or column-to-row transformations directly within the linear dataflow.

```sql
FROM `finance.quarterly_metrics`
|> PIVOT (
     SUM(revenue)
     FOR quarter_id IN ('Q1', 'Q2', 'Q3', 'Q4')
   )
|> UNPIVOT (
     revenue
     FOR quarter_name IN (q1, q2, q3, q4)
   )
```

#### 14. `|> TABLESAMPLE`
Selects a random sample of physical data blocks from the input relation using BigQuery block sampling.

```sql
FROM `telemetry.clickstream`
|> TABLESAMPLE SYSTEM (0.1 PERCENT)
```

#### 15. `|> MATCH_RECOGNIZE`
Applies complex row pattern recognition across partitioned, ordered streams within the pipeline.

```sql
FROM `finance.stock_ticks`
|> MATCH_RECOGNIZE (
     PARTITION BY ticker
     ORDER BY tick_time
     MEASURES FIRST(price) AS start_price, LAST(price) AS peak_price
     PATTERN (up + down +)
     DEFINE
       up AS   price > PREV(price),
       down AS price < PREV(price)
   )
```

#### 16. `|> WITH`
Declares Common Table Expressions mid-pipeline: `|> WITH [RECURSIVE] alias AS (query) [, ...]`. The pipeline input relation passes through completely unchanged to the subsequent operator.

```sql
FROM `retail.orders`
|> WITH
     TaxRates AS (
       SELECT state_code, rate
         FROM `finance.tax_rates`
     )
|> INNER JOIN
   TaxRates
   USING (state_code)
|> EXTEND order_amount * rate AS tax_due
```

#### 17. `|> ORDER BY` and `|> LIMIT`
Sorts output tuples and bounds output row cardinality:

```sql
FROM `retail.orders`
|> ORDER BY order_date DESC
|> LIMIT 100 OFFSET 20
```

---

## 3. Integrating Pipe Queries with BigQuery Statements

In BigQuery, pipe query expressions integrate natively with Data Definition Language (DDL) and Data Manipulation Language (DML) statements. Rather than placing destination operators at the tail of a pipe, developers write standard statement headers consuming a pipe query body.

### 3.1 Table Creation (CTAS)
Create persistent or temporary tables by assigning a pipe query expression to `AS`:

```sql
CREATE OR REPLACE TABLE `analytics.daily_order_summary`
PARTITION BY order_date
  CLUSTER BY customer_id
AS (
  FROM `retail.orders`
  |> WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  |> AGGREGATE
       COUNT(*)          AS order_count,
       SUM(order_amount) AS total_spend
     GROUP BY customer_id, order_date
)
```

### 3.2 Data Insertion
Append pipeline results into existing tables:

```sql
INSERT INTO `analytics.reconciled_payments`
  (payment_id, account_id, cleared_amount)
FROM `finance.incoming_transfers`
|> WHERE transfer_status = 'CLEARED'
|> SELECT transfer_id AS payment_id,
          account_id,
          amount AS cleared_amount
```

### 3.3 Data Export to Cloud Storage
Export query streams into Google Cloud Storage objects:

```sql
EXPORT DATA
OPTIONS (
  uri         = 'gs://my-bucket/exports/orders_*.parquet',
  format      = 'PARQUET',
  compression = 'SNAPPY'
)
AS (
  FROM `retail.orders`
  |> WHERE order_date = CURRENT_DATE()
  |> DROP internal_notes, billing_hash
)
```

---

## 4. Compiler Execution Model: Compile-Time Scope vs. Physical Stages

Pipe syntax provides a linear compositional model without introducing execution overhead compared to handwritten classic SQL.

### 4.1 Zero-Cost Compile-Time Operators
Certain pipe operators mutate the compiler column visibility scope without generating physical relational scan nodes:
- The `|> DROP col1, col2` operator excludes identifiers from the active column list during query compilation. It emits zero physical projection or scan operators in the resulting execution graph.
- The `|> RENAME old_col AS new_col` operator updates column identifier bindings in compiler metadata. It renames output attributes without data movement or execution cycle consumption.
- The `|> AS alias` operator assigns a relation-level identifier alias in compiler scope with zero physical transformation overhead.

Because these operations evaluate entirely in compiler memory, engineers can prune unused fields and clarify column names frequently without performance penalties.

### 4.2 Physical Relational Operators
Other pipe operators generate corresponding physical relational nodes in the execution DAG:
- The `|> EXTEND expr AS col` operator wraps the current scan in a projection node, evaluating expressions during stage worker execution.
- The `|> WHERE condition` operator inserts a filter scan operator, pruning rows according to boolean predicate criteria.
- The `|> AGGREGATE ... GROUP BY ...` operator constructs an aggregate scan operator, establishing a stage boundary and writing intermediate partitions to the remote shuffle tier.
- The `|> JOIN ...` operator constructs a binary hash join operator, triggering broadcast or repartition shuffle mechanics across slot workers.

---

## 5. Interactive Debugging and Verification Protocol

BigQuery Pipe Syntax streamlines iterative query engineering by eliminating nested subquery wrappers.

### 5.1 Incremental Pipeline Testing
Engineers can isolate regressions by commenting out downstream operators. Each pipeline prefix forms an independently valid query:

```sql
FROM `telemetry.api_logs`
|> WHERE response_status >= 500
-- |> AGGREGATE COUNT(*) AS error_count GROUP BY endpoint
-- |> ORDER BY error_count DESC
```

### 5.2 In-Place Window Inspection
Inspect intermediate rankings or deviations without nesting queries inside wrapper layers:

```sql
FROM `sales.transactions`
|> EXTEND DENSE_RANK() OVER (
            PARTITION BY region
                ORDER BY transaction_amount DESC
          ) AS rank_in_region
|> WHERE rank_in_region <= 5
```

---

## 6. Related References and Operational Tooling

- **Language Syntax:** Consult [Language and Syntax Reference](language_and_syntax.md) for classic clause sequence and semantics.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for execution cost models and stage diagnostics.
- **Data Ingestion and Export:** Consult [Data Loading and Export](data_loading_and_export.md) for EXPORT DATA pipe integrations.
- **Machine Learning:** Consult [BigQuery Machine Learning](bigquery_ml.md) for ML.PREDICT pipe integration.


