# BigQuery and GoogleSQL Engineering Cheat Sheet

This cheat sheet summarizes query execution ordering, pipe syntax operators, numeric types, diagnostic thresholds, DDL statements, DML transactions, INFORMATION_SCHEMA views, and CLI commands.

```text
GoogleSQL Query Syntax Execution Sequence:
Textual Syntax:     WITH -> SELECT -> FROM -> WHERE -> GROUP BY -> HAVING -> QUALIFY -> WINDOW -> ORDER BY -> LIMIT
Engine Execution:   WITH -> FROM   -> WHERE -> GROUP BY -> HAVING -> WINDOW  -> QUALIFY -> SELECT   -> ORDER BY -> LIMIT
```

---

## 1. Syntax Comparison and Clause Mapping

GoogleSQL provides two equivalent syntax styles for relational algebra. Classic SQL uses declarative blocks, whereas pipe syntax chains operators linearly from source tables. The table below contrasts clause pairs across common operational patterns.

| Operational Goal | Classic GoogleSQL Syntax | GoogleSQL Pipe Syntax (`\|>`) |
| :--- | :--- | :--- |
| **Initial Source** | `SELECT ... FROM table` | `FROM table` |
| **Base Row Filter** | `WHERE condition` | `\|> WHERE condition` |
| **Column Derivation** | `SELECT *, expr AS alias` | `\|> EXTEND expr AS alias` |
| **In-Place Mutation** | `SELECT * REPLACE (expr AS col)` | `\|> SET col = expr` |
| **Column Exclusion** | `SELECT * EXCEPT (col1, col2)` | `\|> DROP col1, col2` |
| **Column Renaming** | `SELECT col AS new_col` | `\|> RENAME col AS new_col` |
| **Aggregation** | `SELECT k, SUM(v) GROUP BY k` | `\|> AGGREGATE SUM(v) GROUP BY k` |
| **Aggregated Filter** | `HAVING condition` | `\|> AGGREGATE ... \|> WHERE condition` |
| **Window Ranking** | `WINDOW w AS (...) QUALIFY rank <= 3` | `\|> EXTEND ROW_NUMBER() OVER (...) AS r \|> WHERE r <= 3` |
| **Relational Join** | `FROM a JOIN b ON a.id = b.id` | `FROM a \|> JOIN b ON a.id = b.id` |
| **Set Union** | `SELECT ... UNION ALL SELECT ...` | `FROM a \|> UNION ALL BY NAME (FROM b)` |
| **Table Creation** | `CREATE TABLE target AS SELECT ...` | `CREATE TABLE target AS FROM source \|> ...` |

### 1.1 Scalar Expression Invocations: Nested vs. Chained Functions
Chained function syntax evaluates scalar expressions from left to right using dot syntax (.).

| Operation Type | Classic Nested Syntax | Chained Function Syntax (`.`) |
| :--- | :--- | :--- |
| **String Normalization** | `UPPER(TRIM(name))` | `(name).TRIM().UPPER()` |
| **Substring Substitution** | `SUBSTR(REPLACE(val, ' ', '_'), 1, 10)` | `(val).REPLACE(' ', '_').SUBSTR(1, 10)` |
| **Aggregate Modifiers** | `COUNT(DISTINCT user_id)` | `(user_id).COUNT(DISTINCT)` |
| **Namespace-Scoped Calls** | `SAFE.SQRT(metric_val)` | `(metric_val).(SAFE.SQRT)()` |
| **Transformed Rounding** | `ROUND(AVG(latency), 1)` | `(latency).AVG().ROUND(1)` |

### 1.2 Multi-Level Aggregation Syntax (Inner `GROUP BY` Modifier)
Multi-level aggregation nests an inner aggregate function inside an outer aggregate wrapper using an internal `GROUP BY` modifier. This construct computes hierarchical summaries in a single step without subqueries.

| Analytical Goal | Multi-Level Aggregation Syntax | Classic Subquery Equivalent |
| :--- | :--- | :--- |
| **Hierarchical Rollup** | `AVG(SUM(revenue) GROUP BY DATE(time))` | `AVG(daily_sales) FROM (SELECT SUM(revenue) ...)` |
| **Join Deduplication** | `AVG(ANY_VALUE(salary) GROUP BY empno)` | `AVG(sal) FROM (SELECT ANY_VALUE(salary) ...)` |
| **Filtered Subgroups** | `AVG(SUM(rev) GROUP BY day HAVING SUM(rev) > 100)` | Filter inner aggregate groups before outer average |

### 1.3 Native JSON Operators and Functions
GoogleSQL provides native binary `JSON` support, permitting schema-agnostic extraction without repeated string parsing.

| Operation | Syntax Pattern | Return Type |
| :--- | :--- | :--- |
| **Parse JSON String** | `SAFE.PARSE_JSON(raw_text_col)` | `JSON` |
| **Path Navigation** | `json_col.user.profile.email` | `JSON` |
| **Bracket Subscript** | `json_col['user']['addresses'][0]` | `JSON` |
| **Extract String** | `STRING(json_col.user.name)` | `STRING` |
| **Extract Integer** | `INT64(json_col.user.age)` | `INT64` |
| **Extract Float** | `FLOAT64(json_col.metrics.score)` | `FLOAT64` |
| **Extract Boolean** | `BOOL(json_col.flags.is_active)` | `BOOL` |
| **Array Extraction** | `JSON_EXTRACT_ARRAY(json_col.items)` | `ARRAY<STRING>` |
| **Serialize to Text** | `TO_JSON_STRING(struct_expr)` | `STRING` |

### 1.4 Vector Search and Nearest Neighbor Retrieval
Vector search calculates approximate nearest neighbor distances across high-dimensional vector embeddings.

| Search Pattern | Invocation Syntax | Primary Options |
| :--- | :--- | :--- |
| **Create Vector Index** | `CREATE VECTOR INDEX idx ON tbl(col) OPTIONS (...)` | `index_type = 'IVF'`, `distance_type = 'COSINE'` |
| **Batch Vector Search** | `VECTOR_SEARCH(TABLE base, 'vec', TABLE query, 'vec')` | `top_k => 10`, `distance_type => 'COSINE'` |
| **Inline Vector Search** | `VECTOR_SEARCH(TABLE base, 'vec', (query_subquery))` | `top_k => 5`, `options => '{"fraction_lists_to_search": 0.05}'` |

---


## 2. Numeric Type Representation and Arithmetic Cost

Memory layout dictates arithmetic latency and serialization costs. Fixed-point types prevent rounding drift while consuming scalar ALU cycles.

| Data Type | Physical Storage | Scaling Factor | Decimal Precision | CPU Arithmetic Processing | Cache Line Density | Network Wire Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`INT64`** | 8 bytes | 1 | 19 digits | Native 64-bit integer ALU | 8 values / 64B | 8 bytes fixed |
| **`FLOAT64`** | 8 bytes | N/A | 53-bit mantissa | Native 64-bit IEEE-754 FPU | 8 values / 64B | 8 bytes fixed |
| **`NUMERIC`** | 16 bytes | $10^9$ | 38 digits (29.9) | 128-bit multi-word integer arithmetic | 4 values / 64B | 1–16 bytes varint |
| **`BIGNUMERIC`**| 32 bytes | $10^{38}$ | 77 digits (39.38) | 256-bit multi-limb integer routines | 2 values / 64B | 1–32 bytes varint |

*Output Precision Rule for Transformed `FLOAT64`:*
Wrap transformed `FLOAT64` fields in `ROUND(expr, N)` when creating tables. Calibrate precision to domain requirements. Assign currency two decimal places, ratios four, and latencies one. Eliminate unrounded floating-point noise without exaggerating decimal precision.

---

## 3. Execution Plan Diagnostic Triage

Execution plans reveal bottlenecks across compute, memory, and shuffle boundaries. Profiling slot milliseconds measures compute resource consumption accurately.

| Observed Stage Metric | Underlying Root Cause | Architectural Remediation |
| :--- | :--- | :--- |
| **High Wait Milliseconds** | Slot starvation or upstream shuffle dependency | Switch job priority to `BATCH` or size reservation slots |
| **High Read Milliseconds** | Unpartitioned scan or non-clustered scan | Add partition filter; align predicates with cluster keys |
| **High Compute Milliseconds** | Heavy scalar functions or unvectorized math | Pre-aggregate data; convert intermediate `NUMERIC` to `FLOAT64` |
| **Shuffle Spilled to Disk** | Worker memory exhaustion during repartitioning | Break complex DAG with temp tables; filter keys early |
| **Max Slot MS $\gg$ Avg Slot MS** | Data skew on join keys or grouping attributes | Salt hot keys; filter `NULL` and default keys prior to join |
| **Input Rows $\gg$ Output Rows** | Filter applied late after shuffle transfer | Push filter predicates into earliest CTE or subquery |

---

## 4. BigQuery CLI (`bq`) Production Operations

The `bq` utility extracts schemas, estimates dry-run scan costs, and executes asynchronous batch jobs. Scripts invoke these flags to validate production workloads.

```bash
# 1. Validate query syntax and inspect billable scan bytes without running slots
bq query \
  --use_legacy_sql=false \
  --dry_run \
  --format=prettyjson \
  'SELECT customer_id, SUM(order_amount) FROM `project.dataset.orders` GROUP BY customer_id'

# 2. Extract table schema to standard JSON
bq show --schema --format=prettyjson project:dataset.table_name > table_schema.json

# 3. Create a partitioned and clustered table from schema JSON
bq mk \
  --table \
  --schema=table_schema.json \
  --time_partitioning_field=event_timestamp \
  --time_partitioning_type=DAY \
  --require_partition_filter=true \
  --clustering_fields=tenant_id,event_type \
  project:dataset.events_partitioned

# 4. Execute asynchronous batch query with operational labels
bq query \
  --use_legacy_sql=false \
  --priority=BATCH \
  --label=pipeline:reconciliation \
  --label=tier:p1 \
  --destination_table=project:dataset.daily_summary \
  --replace \
  'SELECT event_id, user_id, event_timestamp FROM `project.dataset.raw_events` WHERE event_date = CURRENT_DATE()'
```

---

## 5. Data Definition Language (DDL) Statements

DDL statements declare datasets, tables, views, indexes, and routines.

| Operation | Statement Syntax | Key Options / Constraints |
| :--- | :--- | :--- |
| **Dataset Setup** | `CREATE SCHEMA [IF NOT EXISTS] dataset` | `location`, `storage_billing_model`, `default_table_expiration_days` |
| **Partitioned Table** | `CREATE TABLE target (cols) PARTITION BY date_col CLUSTER BY k1, k2` | `require_partition_filter = TRUE`, `partition_expiration_days` |
| **Table Clone** | `CREATE TABLE clone_tbl CLONE source FOR SYSTEM_TIME AS OF ...` | Zero-copy writeable clone; charges delta storage only |
| **Snapshot Table** | `CREATE SNAPSHOT TABLE snap CLONE source OPTIONS (...)` | Read-only point-in-time snapshot with `expiration_timestamp` |
| **Materialized View**| `CREATE MATERIALIZED VIEW mv PARTITION BY date_col AS SELECT ...` | `enable_refresh`, `refresh_interval_minutes`, `max_staleness` |
| **Search Index** | `CREATE SEARCH INDEX idx ON tbl(ALL COLUMNS)` | `analyzer = 'LOG_ANALYZER'` for text retrieval |
| **Vector Index** | `CREATE VECTOR INDEX idx ON tbl(vector_col) OPTIONS (...)` | `index_type = 'IVF'`, `distance_type = 'COSINE'` |
| **Scalar SQL UDF** | `CREATE FUNCTION fn(x FLOAT64) RETURNS FLOAT64 AS (ROUND(x, 2))` | Inlines scalar transformations across SQL queries |
| **Table Function** | `CREATE TABLE FUNCTION tvf(k INT64) RETURNS TABLE <...> AS (...)` | Parameterized table-valued query routines |
| **Evolution** | `ALTER TABLE tbl ADD COLUMN col TYPE, DROP COLUMN col` | Schema mutation without data restructurings |

---

## 6. Data Manipulation Language (DML) and Transactions

DML statements execute row mutations and multi-statement transactional workflows.

| Operation | Canonical Syntax | Performance and Concurrency Rules |
| :--- | :--- | :--- |
| **Bulk Insert** | `INSERT INTO target (cols) SELECT ...` | Distributed append pass; avoids single-row write paths |
| **Pruned Update** | `UPDATE target SET col = expr WHERE partition_date = ...` | Always provide partition filter to avoid full-table scan |
| **Pruned Delete** | `DELETE FROM target WHERE partition_date = ... AND cond` | Prunes target partitions using boundary predicates |
| **Instant Purge** | `TRUNCATE TABLE target` | Catalog-level metadata wipe; zero slot cost |
| **Incremental Merge** | `MERGE target t USING delta d ON t.month_dt IN UNNEST(g_months) AND t.k = d.k ... WHEN MATCHED AND t.data_hd != d.data_hd THEN UPDATE ...` | Prunes target partitions via `IN UNNEST`; skips unchanged rows via `data_hd` |
| **ACID Transaction**| `BEGIN TRANSACTION; ... COMMIT TRANSACTION;` | Snapshot isolation; aborts on concurrent partition write conflicts |

---

## 7. INFORMATION_SCHEMA System Views

System views report catalog schemas, storage bytes, query runtime telemetry, and slot capacity.

| Operational Goal | System View | Scoping Syntax | Key Filter Rule |
| :--- | :--- | :--- | :--- |
| **Expensive Queries** | `JOBS_BY_PROJECT` | `region-*.INFORMATION_SCHEMA.JOBS_BY_PROJECT` | Filter `creation_time >= TIMESTAMP_SUB(..., INTERVAL N DAY)` |
| **Slot Starvation** | `JOBS_TIMELINE_BY_PROJECT` | `region-*.INFORMATION_SCHEMA.JOBS_TIMELINE_BY_PROJECT` | Filter `period_start` to detect concurrency spikes |
| **Storage Savings** | `TABLE_STORAGE` | `region-*.INFORMATION_SCHEMA.TABLE_STORAGE` | Compare `total_logical_bytes` vs `total_physical_bytes` |
| **Partition Skew** | `PARTITIONS` | `dataset.INFORMATION_SCHEMA.PARTITIONS` | Filter out `__NULL__` and `__UNPARTITIONED__` |
| **Nested Structs** | `COLUMN_FIELD_PATHS` | `dataset.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` | Flattens nested paths (`user.address.street`) |
| **Table Options** | `TABLE_OPTIONS` | `dataset.INFORMATION_SCHEMA.TABLE_OPTIONS` | Check `require_partition_filter` and retention days |
| **Column Options** | `COLUMN_OPTIONS` | `dataset.INFORMATION_SCHEMA.COLUMN_OPTIONS` | Check `description`, `rounding_mode`, `policy_tags` |
| **Slot Commitments** | `RESERVATIONS` | `region-*.INFORMATION_SCHEMA.RESERVATIONS` | Track baseline slots and autoscale ceilings |

---

## 8. BigQuery Machine Learning Operations

The table below outlines built-in predictive modeling routines:

| Operation | GoogleSQL Statement | Target Model Types |
| :--- | :--- | :--- |
| **Model Creation** | `CREATE MODEL m OPTIONS(model_type='LOGISTIC_REG') AS SELECT ...` | Supervised regression, classification, boosted trees |
| **Model Assessment** | `SELECT * FROM ML.EVALUATE(MODEL m, (SELECT ...))` | Computes ROC AUC, accuracy, log loss, RMSE |
| **Batch Inference** | `SELECT * FROM ML.PREDICT(MODEL m, (SELECT ...))` | Generates predictions across input feature sets |
| **Time Series** | `SELECT * FROM ML.FORECAST(MODEL m, STRUCT(30 AS horizon))` | Computes forward forecasts with confidence bands |
| **Feature Weights** | `SELECT * FROM ML.WEIGHTS(MODEL m)` | Inspects linear coefficients and categorical offsets |

---

## 9. Data Ingestion and Export Statements

The table below details data movement syntax across external cloud storage:

| Operation | GoogleSQL Statement | Key Execution Flags |
| :--- | :--- | :--- |
| **Load Append** | `LOAD DATA INTO tbl FROM FILES (format='PARQUET', uris=[...])` | Atomic append; rolls back on schema errors |
| **Load Overwrite** | `LOAD DATA OVERWRITE tbl FROM FILES (format='CSV', uris=[...])` | Truncates target before ingesting files |
| **Data Export** | `EXPORT DATA OPTIONS (uri=..., format='PARQUET') AS SELECT ...` | Writes compressed columnar files to buckets |
| **Scheduled Job** | `bq mk --transfer_config --data_source=scheduled_query ...` | Automates periodic query execution via DTS |

---

## 10. Service Quotas and Architectural Boundaries

Engineers adhere to strict service thresholds during analytical pipeline design:

| Resource Dimension | System Quota Limit | Operational Consequence |
| :--- | :--- | :--- |
| **Partition Mutations** | 5,000 modifications per table per day | Consolidate single-row DML into scheduled MERGE jobs |
| **Table Operations** | 1,500 operations per table per day | Batch table creation and drop statements |
| **Concurrent Queries** | 100 concurrent interactive queries | Queue batch jobs using BATCH priority mode |
| **Query Duration** | 6 hours maximum execution timeout | Split complex pipelines into intermediate tables |
| **Query String Size** | 1 megabyte maximum text length | Parameterize queries and reference shared views |
| **Referenced Tables** | 1,000 tables maximum per SQL query | Union intermediate tables before final analysis |


