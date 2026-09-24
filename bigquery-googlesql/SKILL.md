---
name: bigquery-googlesql
description: >-
  Expert reference and tooling for Google Cloud BigQuery and GoogleSQL (ZetaSQL).
  Use this skill when the user asks to write, optimize, debug, or format BigQuery queries
  (including Classic SQL and Pipe Syntax |>), compute statistical scorecard metrics (Gini,
  AUC, KS, PSI), design partitioning and clustering strategies, triage stage execution
  metrics (shuffle spills, slot starvation, data skew), train or run BigQuery ML models
  (CREATE MODEL, ML.PREDICT), execute data movement (LOAD DATA, EXPORT DATA, scheduled queries),
  estimate scan costs via dry runs, or implement Go/Python BigQuery SDK pipelines.
---

# GoogleSQL and BigQuery Engineering Skill

Google Cloud BigQuery separates multi-tenant compute from petabyte-scale storage. Distributed Borg slots process analytical queries over an external Jupiter network fabric, reading columnar data persisted on Colossus. The GoogleSQL engine executes declarative relational queries, compiling expressions into physical execution directed acyclic graphs (DAGs). This skill provides reference architectures, syntax specifications, engine internal models, optimization protocols, formatting rules, and client tooling for GoogleSQL engineering.

```sql
-- Production baseline: sargable partition filtering and explicit projection
SELECT event_id, user_id, event_ts
  FROM `telem_traffic_01_lnd.event_fact`
 WHERE event_ts >= TIMESTAMP('2026-03-01 00:00:00 UTC')
   AND event_ts < TIMESTAMP('2026-03-08 00:00:00 UTC')
```

---

## Core Engineering Invariants

Production analytical queries and schema definitions must adhere to six non-negotiable engineering invariants:

- **Strict Column Projection:** Every query must project only necessary columns. Scanning unused columns forces Capacitor to read unneeded column stripes from Colossus disk blocks, burning memory bandwidth and increasing scan costs. Wildcard projection (`SELECT *`) is permissible only when conditioned on certainty of correctness: specifically, when every schema column is verifiably required by downstream logic, or when selecting from localized intermediate structures (such as Common Table Expressions and temporary tables) where the author maintains full schema control. Conversely, `SELECT *` is strictly prohibited on external tables (BigLake, object tables, CSV/JSON, Google Sheets) due to lack of schema control and risk of uncontrolled schema drift, and on persistent warehouse tables when only a subset of attributes is needed.
- **Partition and Cluster Gating:** Analytical queries across partitioned tables must supply static or bounded partition filters in top-level `WHERE` clauses. The storage engine uses partition headers to eliminate unreferenced blocks before reading data chunks. Pruning saves budget.
- **Controlling Intermediate CTE Expressions:** BigQuery treats CTEs as non-materialized inline query views and inlines them dynamically. Common Table Expressions strictly follow standard GoogleSQL syntax (`WITH cte AS (...)`). When multiple query branches consume the same complex intermediate reduction, materialize the dataset into a temporary table (`CREATE TEMP TABLE ... AS SELECT ...`) to evaluate intermediate rows once and collect fresh optimizer statistics.
- **Numeric Precision Discipline:** Store quantitative metrics in `INT64` or `FLOAT64` where exact decimal precision (such as currency) is unnecessary. The `NUMERIC` type requires 16 bytes per value and `BIGNUMERIC` requires 32 bytes per value, doubling or quadrupling memory footprint, cache line usage, and network shuffle wire transfer compared to 8-byte `INT64` or `FLOAT64` values. When projecting computed, aggregated, or transformed `FLOAT64` fields into resulting tables, wrap expressions in `ROUND()` to enforce sensible precision and suppress uninformative IEEE 754 noise.
- **Mitigating Key Skew in Distributed Joins:** In large-scale shuffle joins, skewed join keys concentrate disproportionate row volumes onto solitary Borg slots, generating long tail execution latency. Salting skewed keys distributes compute work uniformly across the worker pool. Prevent stragglers.
- **Universal Code Style and Architectural Naming Compliance:** Every emitted query, routine, and DDL statement must strictly conform to [Style and Formatting Guidelines](references/style_and_formatting.md) and [Naming Conventions](references/naming_conventions.md):
  - **Lexical Casing:** Keywords (`SELECT`, `FROM`, `WHERE`), data types (`INT64`, `FLOAT64`, `STRING`), built-in functions (`COUNT`, `ROUND`, `APPROX_QUANTILES`), and literals (`TRUE`, `FALSE`, `NULL`) must remain uppercase. String literals must use single quotes (`'val'`).
  - **Clause Alignment Gutter:** Primary clauses align to a right-aligned gutter starting arguments at column 8 (`SELECT `, `  FROM `, ` WHERE `, `HAVING `, `   AND `, `    OR `). Multi-line column projections indent subsequent attributes by seven spaces.
  - **Multi-Line Join Geometry:** Multi-line joins indent by seven spaces under `FROM` (`       INNER JOIN\n       table\n       ON condition`).
  - **Conditional Formatting (`CASE`):** Place `WHEN condition THEN result` on a single line, align `ELSE` with the `THEN` result column, and align `END` flush with `CASE`.
  - **Architectural Naming:** Dataset identifiers must declare domain, subdomain, and lifecycle layer (`<domain>_<subdomain>_<layer>`, such as `risk_monitoring_08_met`). Table identifiers must declare approved suffixes (`_fact`, `_dim`, `_met`, `_pred`, `_feat`, `_jnl`). Column identifiers must conclude with ISO 11179 class words (`_id`, `_bk`, `_nm`, `_dt`, `_ts`, `_amt`, `_qty`, `_val`, `_rt`, `_p`, `_ind`, `_cd`).

---

## Unified Technical Architecture and Routing Matrix

| Operational Goal / Domain | Primary Specification Link | Subsystem Scope and Core Topics |
| :--- | :--- | :--- |
| **Drafting or Refactoring Classic SQL** | [Language Reference](references/language_and_syntax.md) | 12 execution phases, UNNEST, PIVOT, QUALIFY, native JSON operators, MATCH_RECOGNIZE |
| **Constructing Pipe Syntax Pipelines** | [Pipe Syntax Guide](references/pipe_syntax.md) | Linear relational dataflows (`\|>`), 26 pipe operators, subpipelines |
| **Accelerating Slow or Expensive Queries** | [Query Optimization](references/query_design_and_optimization.md) | 7-phase optimization framework, CTE materialization, BI Engine |
| **Triaging Slot Spills and Data Skew** | [Planning & Execution](references/query_planning_and_execution.md) | Borg slots, DAG repartitioning, shuffle spills to Colossus |
| **Configuring Partitions and Clusters** | [Partitioning & Clustering](references/partitioning_and_clustering_guide.md) | Sizing boundaries ($\ge 10\text{ GB}$ vs $\ge 1\text{ GB}$), column order ($C_1 \to C_4$) |
| **Training and Evaluating ML Models** | [BigQuery ML Reference](references/bigquery_ml.md) | `CREATE MODEL`, `ML.PREDICT`, `VECTOR_SEARCH`, `ARIMA_PLUS`, `TRANSFORM` |
| **Evaluating Scorecards and Risk Models** | [Scorecard & Risk Patterns](examples/scorecard_metrics.sql) | Gini coefficient, ROC-AUC, KS statistic, PSI drift, trapezoidal integration |
| **Ingesting Files, Exports & Streams** | [Data Loading & Export](references/data_loading_and_export.md) | `LOAD DATA`, `EXPORT DATA`, continuous queries, streaming exports, BigQuery DTS |
| **Creating Tables, Views, or Routines** | [DDL Reference](references/ddl_reference.md) | `CREATE TABLE`, clones, snapshots, TVFs, vector indexes, stored procedures |
| **Executing Batched Mutations or MERGE** | [DML & Transactions](references/dml_and_transactions.md) | Batched mutations, delete masks, multi-statement ACID |
| **Auditing Metadata and Compute Billing** | [INFORMATION_SCHEMA](references/information_schema_reference.md) | System views, job timelines, table storage footprints, slot reservations |
| **Setting Table and Field Parameters** | [Table Parameters Guide](references/table_and_field_options.md) | Retention, rounding modes, policy tags, billing models |
| **Inspecting Columnar Storage Layouts** | [Storage Architecture](references/storage_and_capacitor.md) | Dremel repetition/definition levels, columnar encodings, Capacitor files |
| **Optimizing Shuffle & Expression Placement** | [Query Optimization](references/query_design_and_optimization.md) | Shuffle boundary type-slimming, reduction ratios, operator placement |
| **Standardizing Resource Identifiers** | [Naming Conventions](references/naming_conventions.md) | Three-tier hierarchy, ISO 11179 grammar, suffix catalog |
| **Structuring Enterprise Lifecycles** | [Data Architecture](references/data_architecture_and_lifecycle.md) | Eight-tier data lifecycle (`01_landing` to `08_metrics`), table lifecycles |
| **Applying FinOps and Security Tags** | [Resource Tagging](references/resource_tagging_and_metadata.md) | FinOps tags, SDK query labels, Dataplex policy tags |
| **Executing End-to-End Workflows** | [Engineering Workflows](references/engineering_workflows.md) | Query authoring, stage performance triage, schema migrations, CI gating |
| **Formatting Code and Enforcing CI Gates**| [Style & Formatting](references/style_and_formatting.md) | `bqfmt` rules, `.bqfmt.toml`, dry-run cost verification |
| **Automating via CLI, Go, or Python** | [Tooling, CLI & SDKs](references/tooling_cli_and_sdks.md) | `bq` CLI flags, Go client, Python client, Storage Write API |

---

## Production Quick Reference

| Operational Domain | Anti-Pattern | Recommended Production Pattern | Reference Link |
| :--- | :--- | :--- | :--- |
| **Storage Retrieval** | Unnecessary `SELECT *` or wildcard scans on external tables | Project explicit column lists; use `SELECT *` only when all columns are needed or from local CTEs/temp tables | [Storage Internals](references/storage_and_capacitor.md) |
| **Partition Filtering** | `WHERE DATE(ts) = '2026-03-01'` | `WHERE ts >= '2026-03-01' AND ts < '2026-03-02'` (sargable) | [Query Design](references/query_design_and_optimization.md) |
| **Pipeline Modularity** | Deeply nested subqueries | Pipe syntax: `FROM table \|> WHERE ... \|> AGGREGATE ...` | [Pipe Syntax](references/pipe_syntax.md) |
| **Expression Chaining** | Deeply nested inside-out calls | Chained function calls: `(x).h().g().f()` | [Language Syntax](references/language_and_syntax.md) |
| **Multi-Level Aggregation** | Multi-stage CTEs for rollups or deduplication | Nested aggregates: `AVG(SUM(v) GROUP BY k)` | [Language Syntax](references/language_and_syntax.md) |
| **Repeated CTE Ingestion** | Complex CTE re-evaluated multiple times | Materialize via `CREATE TEMP TABLE` to evaluate once | [Optimization Rules](references/query_design_and_optimization.md) |
| **Join Execution** | Joining two large tables without pre-filtering | Filter both sides before join; ensure smaller side broadcasts | [Planning & Execution](references/query_planning_and_execution.md) |
| **Deduplication** | Correlated subqueries or large self-joins | Window function with `QUALIFY ROW_NUMBER() OVER (...) = 1` | [Language Syntax](references/language_and_syntax.md) |
| **Cardinality Aggregation** | `COUNT(DISTINCT large_id)` | `APPROX_COUNT_DISTINCT(large_id)` for massive telemetry sets | [Cheat Sheet](resources/cheat_sheet.md) |
| **High-Precision Decimals** | Defaulting to `BIGNUMERIC` everywhere | Use `INT64` (e.g. micros/cents) or standard `NUMERIC` | [Language Syntax](references/language_and_syntax.md) |
| **Float Output Precision** | Unrounded transformed `FLOAT64` noise | Wrap output in `ROUND(expr, N)` calibrated to domain | [Style Guide](references/style_and_formatting.md) |
| **Schema Definitions** | Unpartitioned tables without constraints | Partitioned, clustered tables with non-enforced PKs and partition filters | [DDL Reference](references/ddl_reference.md) |
| **Data Mutations** | High-frequency single-row DML | Batched MERGE with partition boundary pruning | [DML & Transactions](references/dml_and_transactions.md) |
| **System Telemetry** | Blind console inspection | Query `region-*.INFORMATION_SCHEMA.JOBS_BY_PROJECT` filtered on `creation_time` | [System Views](references/information_schema_reference.md) |
| **Code Formatting** | Inconsistent indentation and lower-case SQL | Automated formatting with `bqfmt` (2-space indent, uppercase) | [Style Guide](references/style_and_formatting.md) |
| **CI Cost Verification** | Blind execution of test queries | Automated dry runs checking bytes processed via CLI or SDK | [Tooling & SDKs](references/tooling_cli_and_sdks.md) |

---

## Production Resources and Executable Tooling

- **Cheat Sheets:** Consult [Engineering Cheat Sheet](resources/cheat_sheet.md) for clause mapping, execution limits, and CLI commands.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](resources/anti_patterns_catalog.md) for mechanical failures and refactoring patterns.
- **Schema Templates:** Consult [Schema Templates](resources/schema_templates.md) for canonical `TableFieldSchema[]` definitions.
- **Formatter Configuration:** Deploy [Production bqfmt Configuration](examples/dot_bqfmt.toml) for automated SQL style enforcement.
- **SQL Patterns:** Inspect [Classic vs Pipe Syntax](examples/classic_vs_pipe_syntax.sql), [Scorecard & Risk Patterns](examples/scorecard_metrics.sql), [Optimized Query Patterns](examples/optimized_patterns.sql), [Incremental Merge Pattern](examples/incremental_merge_pattern.sql), [Multi-Level Aggregation](examples/multi_level_aggregation.sql), and [DDL and DML Patterns](examples/ddl_and_dml_patterns.sql).
- **Client Utilities:** Review [Go Schema Client](examples/schema_extraction.go) (with [Go Tests](examples/schema_extraction_test.go)) and [Python Schema Utility](examples/schema_extraction.py) (with [Python Tests](examples/test_schema_extraction.py)).
- **Automation Scripts:** Execute [Dry-Run Estimator](scripts/dry_run.sh), [Schema Exporter](scripts/extract_schema.sh), and [Artifact Verifier](scripts/verify.sh).

---

## Scope Boundaries

This skill covers analytical query engineering, columnar storage architecture, runtime performance diagnostics, schema management, and in-database machine learning in BigQuery. The following areas fall outside the operational scope of this skill:
- Row-level access control policies (`CREATE ROW ACCESS POLICY`).
- Column data masking and authorized view permission grants.
- Remote external functions invoking Cloud Functions or Cloud Run microservice endpoints.
- BigLake engines and federated external tables (`CREATE EXTERNAL TABLE`).
