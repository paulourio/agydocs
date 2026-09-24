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
| **Array Extraction** | `JSON_QUERY_ARRAY(json_col.items)` | `ARRAY<JSON>` |
| **String Array** | `JSON_VALUE_ARRAY(json_col.tags)` | `ARRAY<STRING>` |
| **Lax Integer** | `LAX_INT64(json_col.user.age)` | `INT64` |
| **Serialize to Text** | `TO_JSON_STRING(struct_expr)` | `STRING` |

### 1.4 Vector Search and Nearest Neighbor Retrieval
Vector search calculates approximate nearest neighbor distances across high-dimensional vector embeddings.

| Search Pattern | Invocation Syntax | Primary Options |
| :--- | :--- | :--- |
| **Create Vector Index** | `CREATE VECTOR INDEX idx ON tbl(col) OPTIONS (...)` | `index_type = 'IVF'`, `distance_type = 'COSINE'` |
| **Batch Vector Search** | `VECTOR_SEARCH(TABLE base, 'vec', TABLE q, query_column_to_search => 'vec')` | `top_k => 10`, `distance_type => 'COSINE'` |
| **Inline Vector Search** | `VECTOR_SEARCH(TABLE base, 'vec', query_value => [0.12, 0.45, ...])` | `top_k => 5`, `distance_type => 'COSINE'` |

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
| **Column Options** | `COLUMN_FIELD_PATHS` | `dataset.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` | Check `description`, `rounding_mode`, `policy_tags` |
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

### 8.1 Model-Less Direct Inference (`AI.*` Family)

The `AI.*` function family executes foundation model inference directly across table rows without declaring relational model objects.

| Routine | Purpose | Invocation Syntax | Key Parameters |
| :--- | :--- | :--- | :--- |
| **`AI.GENERATE`** | LLM text generation | `AI.GENERATE(prompt, connection_id => '...')` | `output_schema`, `temperature`, `max_output_tokens` |
| **`AI.EMBED`** | Vector embedding generation | `AI.EMBED(text, connection_id => '...')` | `model_name`, `task_type` |
| **`AI.SIMILARITY`** | Vector distance metric | `AI.SIMILARITY(vec_a, vec_b, metric => 'COSINE')` | `metric => 'COSINE' \| 'EUCLIDEAN'` |
| **`AI.CLASSIFY`** | Zero-shot text classification | `AI.CLASSIFY(text, labels => [...], connection_id => '...')` | Target category list |
| **`AI.SCORE`** | Quality scoring | `AI.SCORE(text, connection_id => '...')` | Normalized float score output |
| **`AI.FORECAST`** | Foundation time-series model | `AI.FORECAST(TABLE tbl, timestamp_col => '...', ...)` | Uses TimesFM foundation model |
| **`AI.PREDICT`** | Foundation tabular prediction | `AI.PREDICT(TABLE tbl, label_col => '...', ...)` | Uses TabFM foundation model |
| **`AI.DETECT_ANOMALIES`** | Foundation anomaly detection | `AI.DETECT_ANOMALIES(TABLE tbl, ...)` | Multivariate anomaly identification |
| **`AI.SEARCH`** | Direct semantic search | `AI.SEARCH(TABLE tbl, 'col', 'query', ...)` | Searches generated embedding columns |

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

---

## 11. Common Semantic Gotchas and Execution Pitfalls

The table below summarizes common traps and their corrective patterns:

| Operational Domain | Failure Mode / Symptom | Root Mechanism | Recommended Production Pattern |
| :--- | :--- | :--- | :--- |
| **FinOps & Cost** | `LIMIT` does not reduce billable scan bytes | `LIMIT` evaluates at Stage 12 after full storage scan | Project explicit columns; filter on partition/cluster keys |
| **Three-Valued Logic** | `NOT IN (subquery)` returns zero rows | Subquery contains `NULL`, yielding `UNKNOWN` boolean | Use `NOT EXISTS (SELECT 1 ...)` or anti-join |
| **Array Unnesting** | Comma `UNNEST` silently drops parent rows | Inner cross join drops rows with empty or `NULL` arrays | Use `FROM table LEFT JOIN UNNEST(arr)` |
| **Array Subscripting** | `arr[OFFSET(i)]` halts query at runtime | Index out-of-bounds raises query failure | Use `arr[SAFE_OFFSET(i)]` or `arr[SAFE_ORDINAL(i)]` |
| **Numeric Division** | `x / 0` halts query; `5 / 2` yields `2.5` | `/` evaluates `FLOAT64` and fails on zero divisors | Use `SAFE_DIVIDE(x, y)`; use `DIV(x, y)` for `INT64` division |
| **String Operations** | `CONCAT('a', NULL)` evaluates to `NULL` | String concatenation propagates nulls strictly | Wrap in `IFNULL(col, '')` or use `FORMAT('%s%s', ...)` |
| **Temporal Policy** | `CURRENT_DATE()` off-by-one calendar drift | Default timezone is UTC | Standardize queries on UTC; pass civil zone only if documented |
| **Date Arithmetic** | `DATE_DIFF` returns 1 month for a 1-day interval | Function counts crossed calendar boundaries, not elapsed time | Use day-level arithmetic for precise durations |
| **Table Constraints** | Duplicate keys pass into tables with `PRIMARY KEY` | Primary and foreign keys are `NOT ENFORCED` on writes | Validate upstream or deduplicate with `QUALIFY ROW_NUMBER() = 1` |

---

## 12. Property Graph Query Language (GQL) Syntax

GoogleSQL executes graph queries over relational tables configured as property graphs.

| Operation | Statement Syntax | Key Semantics |
| :--- | :--- | :--- |
| **Create Graph** | `CREATE PROPERTY GRAPH g NODE TABLES (...) EDGE TABLES (...)` | Defines graph model over relational tables |
| **Query Pattern** | `SELECT * FROM GRAPH_TABLE(g MATCH (a)-[e]->(b) RETURN a.id, b.id)` | Queries graph structures within SQL |
| **Path Quantifiers**| `MATCH p = (a)-[e]->{1, 3}(b)` | Bounded variable-length traversal |
| **Path Filters** | `WHERE IS_ACYCLIC(p) AND ALL_DIFFERENT(NODES(p))` | Cycle suppression and unique element assertions |
| **Shortest Paths** | `MATCH SHORTEST (a)-[e]->+(b)` | Evaluates minimal hop trajectories |
| **Cheapest Paths** | `MATCH ANY CHEAPEST (a)-[e COST weight]->{1, 5}(b)` | Evaluates minimum cumulative edge weight |
| **Graph Predicates**| `WHERE a IS SOURCE OR b IS DESTINATION OR SAME(a, b)` | Validates element directionality and identity |
| **Graph Functions** | `NODES(p)`, `EDGES(p)`, `PATH_LENGTH(p)`, `LABELS(n)` | Extracts arrays of vertices, edges, and counts |
| **Graph Expand** | `SELECT * FROM GRAPH_EXPAND('FinGraph')` | TVF that expands graph edges into relational rows |

---

## 13. Procedural Scripting Statements

Procedural SQL orchestrates multi-step workflows, variable states, and conditional branching within scripts.

| Scripting Construct | Canonical Syntax | Operational Behavior |
| :--- | :--- | :--- |
| **Block Scoping** | `BEGIN ... END;` | Defines variable and exception scope boundaries |
| **Variable Decl** | `DECLARE var_name INT64 DEFAULT 0;` | Declares typed session variables |
| **Tuple Assignment**| `SET (x, y) = (10, 'alpha');` | Assigns scalar or tuple values atomically |
| **Branching** | `IF cond THEN ... ELSEIF cond THEN ... END IF;` | Conditional execution path selection |
| **Iteration Loop** | `LOOP ... IF done THEN LEAVE; END IF; END LOOP;` | Unbounded iterative loop with manual break |
| **While Loop** | `WHILE cond DO ... END WHILE;` | Pre-checked conditional loop execution |
| **Repeat Loop** | `REPEAT ... UNTIL cond END REPEAT;` | Post-checked loop executing at least once |
| **Cursor Loop** | `FOR row IN (SELECT id FROM tbl) DO ... END FOR;` | Iterates over relational query results |
| **Dynamic SQL** | `EXECUTE IMMEDIATE query_str USING param INTO var;` | Compiles and executes parameterized SQL at runtime |
| **Exception Block** | `BEGIN ... EXCEPTION WHEN ERROR THEN ... END;` | Traps runtime errors and executes recovery |
| **User Exception** | `RAISE USING MESSAGE = 'Custom error';` | Raises explicit exception terminating block |
| **Assertion Gating**| `ASSERT condition AS 'Assertion failed description';` | Validates pipeline data invariants |

---

## 14. Administrative Procedures and System Variables

BigQuery exposes administrative routines under `BQ.*` and system telemetry through `@@` variables.

### 14.1 System Procedures (`BQ.*`)

System procedures perform operational administration across jobs, sessions, and caches.

| System Procedure | Signature and Arguments | Administrative Purpose |
| :--- | :--- | :--- |
| **`BQ.ABORT_SESSION`** | `CALL BQ.ABORT_SESSION('session_id');` | Terminates active multi-statement session |
| **`BQ.JOBS.CANCEL`** | `CALL BQ.JOBS.CANCEL('job_id');` | Cancels running query job asynchronously |
| **`BQ.CANCEL_INDEX_ALTERATION`** | `CALL BQ.CANCEL_INDEX_ALTERATION('tbl', 'idx');` | Halts vector or search index mutation job |
| **`BQ.REFRESH_EXTERNAL_METADATA_CACHE`** | `CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE('tbl');` | Synchronizes metadata cache for BigLake tables |
| **`BQ.REFRESH_MATERIALIZED_VIEW`** | `CALL BQ.REFRESH_MATERIALIZED_VIEW('mv_name');` | Forces immediate refresh of materialized view |
| **`BQ.SHOW_GRAPH_EXPAND_SCHEMA`** | `CALL BQ.SHOW_GRAPH_EXPAND_SCHEMA('graph', out);` | Displays column schema emitted by `GRAPH_EXPAND` |

### 14.2 System Variables (`@@*`)

System variables provide contextual metadata and execution telemetry within procedural scripts.

| Variable Name | Data Type | Contextual Value |
| :--- | :--- | :--- |
| **`@@project_id`** | `STRING` | Current billing project identifier |
| **`@@dataset_id`** | `STRING` | Default dataset identifier for unadorned references |
| **`@@current_job_id`** | `STRING` | Job identifier of the currently executing statement |
| **`@@last_job_id`** | `STRING` | Job identifier of the immediately preceding statement |
| **`@@row_count`** | `INT64` | Rows modified by the most recent DML statement |
| **`@@time_zone`** | `STRING` | Session default time zone for timestamp parsing |
| **`@@script.bytes_billed`** | `INT64` | Cumulative billable bytes across current script |
| **`@@script.slot_ms`** | `INT64` | Cumulative slot execution milliseconds in script |
| **`@@script.num_child_jobs`** | `INT64` | Number of child jobs executed within script |
| **`@@error.message`** | `STRING` | Error message captured inside exception block |
| **`@@error.statement_text`** | `STRING` | Text of SQL statement that raised exception |
| **`@@error.formatted_stack_trace`** | `STRING` | Complete call stack of procedural error |




