# BigQuery INFORMATION_SCHEMA System Views Reference

This reference details the GoogleSQL system views in BigQuery. It defines view groupings, scoping rules, schema column structures, analytical use cases, and diagnostic queries across catalog metadata, storage footprints, query runtime telemetry, and compute slot pools.

```sql
-- Canonical Regional Query: Audit Top 10 Slot-Consuming Queries in Preceding 24 Hours
SELECT job_id,
       user_email,
       total_slot_ms,
       ROUND(total_bytes_billed / POW(1024, 4), 2) AS billed_terabytes,
       query
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
 WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
   AND job_type = 'QUERY'
   AND end_time IS NOT NULL
 ORDER BY total_slot_ms DESC
 LIMIT 10
```

---

## 1. Scoping Hierarchy and Namespace Rules

BigQuery organizes system views into three distinct architectural scopes: dataset scope, regional project scope, and regional enterprise scope.

```
+-------------------------------------------------------------------------------+
| Regional Enterprise Scope: `region-us.INFORMATION_SCHEMA.*_BY_ORGANIZATION`   |
|   +---------------------------------------------------------------------------+
|   | Regional Project Scope: `region-us.INFORMATION_SCHEMA.*_BY_PROJECT`       |
|   |   +-----------------------------------------------------------------------+
|   |   | Dataset Scope: `project.dataset.INFORMATION_SCHEMA.*`                 |
|   |   +-----------------------------------------------------------------------+
+---+---------------------------------------------------------------------------+
```

### 1.1 Scope Boundaries

Engineers query system views by prefixing view identifiers with appropriate dataset or regional qualifiers:

```text
Dataset-Scoped Syntax:
  `[project_id.]dataset_name.INFORMATION_SCHEMA.VIEW_NAME`
  Includes: TABLES, COLUMNS, COLUMN_FIELD_PATHS, VIEWS, MATERIALIZED_VIEWS, PARTITIONS

Regional Project Syntax:
  `[project_id.]region-REGION_NAME.INFORMATION_SCHEMA.VIEW_NAME`
  Includes: TABLE_STORAGE, JOBS_BY_PROJECT, JOBS_TIMELINE_BY_PROJECT, RESERVATIONS

Regional Enterprise Syntax:
  `region-REGION_NAME.INFORMATION_SCHEMA.VIEW_NAME`
  Includes: JOBS_BY_ORGANIZATION, TABLE_STORAGE_BY_ORGANIZATION
```

The dataset tier exposes metadata for tables, views, and routines residing within a solitary dataset. The regional project tier aggregates metrics across all datasets and jobs executing within a single Google Cloud region. The regional enterprise tier pools job history and storage footprints across every project linked to the parent enterprise node.

---

## 2. Catalog and Schema Views

Catalog views expose database object structures, column types, relational keys, and active parameters.

### 2.1 Catalog Views Summary

| View Name | Scope | Key Columns | Primary Purpose and When to Use |
| :--- | :--- | :--- | :--- |
| **`SCHEMATA`** | Regional | `schema_name`, `location`, `default_collation_name` | Audit dataset geographic placement and default collation rules across a region. |
| **`TABLES`** | Dataset | `table_name`, `table_type`, `creation_time` | Inventory tables, distinguish views from base tables, and detect stale tables. |
| **`TABLE_OPTIONS`** | Dataset | `table_name`, `option_name`, `option_value` | Verify active table parameters (`require_partition_filter`, expiration). |
| **`COLUMNS`** | Dataset | `column_name`, `ordinal_position`, `data_type`, `is_nullable` | Audit column types, null constraints, and verify schema migrations. |
| **`COLUMN_FIELD_PATHS`** | Dataset | `field_path`, `data_type`, `description` | Inspect nested `RECORD` and `STRUCT` subfields without custom parsing code. |
| **`COLUMN_OPTIONS`** | Dataset | `table_name`, `column_name`, `option_name`, `option_value` | Check column descriptions, policy tags, and decimal rounding modes. |
| **`VIEWS`** | Dataset | `table_name`, `view_definition` | Audit SQL query definitions, tracking view dependencies and lineage. |
| **`MATERIALIZED_VIEWS`** | Dataset | `table_name`, `last_refresh_time`, `refresh_watermark` | Check refresh status, staleness gaps, and rewrite eligibility. |
| **`ROUTINES`** | Dataset | `routine_name`, `routine_type`, `language`, `routine_definition` | Catalog SQL UDFs, JavaScript routines, TVFs, and stored procedures. |
| **`PARAMETERS`** | Dataset | `specific_name`, `ordinal_position`, `parameter_name`, `data_type` | Inspect routine argument signatures and return types. |
| **`SEARCH_INDEXES`** | Dataset | `index_name`, `table_name`, `index_status`, `analyzer` | Track text search index readiness and background build progress. |
| **`VECTOR_INDEXES`** | Dataset | `index_name`, `table_name`, `index_status`, `distance_type` | Verify vector embedding index build state before running vector search. |
| **`TABLE_CONSTRAINTS`** | Dataset | `constraint_name`, `constraint_type`, `enforced` | Inspect declared `PRIMARY KEY` and `FOREIGN KEY` metadata hints. |

### 2.2 Operational Use Cases for Catalog Views

Engineers query catalog views to automate schema audits, validate pipeline rollouts, and generate data dictionaries. The `COLUMNS` and `COLUMN_FIELD_PATHS` views allow continuous integration pipelines to compare staging table schemas against production baselines, detecting breaking type changes before code merges. The `MATERIALIZED_VIEWS` view reports refresh timestamps, allowing alerting tools to detect stalled background maintenance tasks.

---

## 3. Storage and Capacity Views

Storage views report raw byte counts, compression outcomes, and partition boundary layouts.

### 3.1 Storage Views Summary

| View Name | Scope | Metric Columns | Primary Purpose and When to Use |
| :--- | :--- | :--- | :--- |
| **`TABLE_STORAGE`** | Regional | `total_logical_bytes`, `active_logical_bytes`, `long_term_logical_bytes`, `total_physical_bytes`, `active_physical_bytes`, `time_travel_physical_bytes`, `fail_safe_physical_bytes` | Evaluate storage billing costs. Compare logical versus physical billing models to capture cost savings. |
| **`PARTITIONS`** | Dataset | `partition_id`, `total_rows`, `total_logical_bytes`, `storage_tier`, `last_modified_time` | Detect partition skew, find empty partitions, and audit historical retention bounds. |
| **`TABLE_STORAGE_USAGE_TIMELINE`** | Regional | `table_schema`, `table_name`, `usage_date`, `billable_logical_bytes`, `billable_physical_bytes` | Track historical data growth and model capacity forecasts over time. |

### 3.2 Operational Guidance for Storage Analysis

Querying `TABLE_STORAGE` enables financial optimization by revealing compressed byte counts on Colossus storage blocks. When physical compression ratios exceed two to one, switching datasets from logical billing to physical storage billing lowers monthly cloud invoices. Querying `PARTITIONS` exposes data skew across date boundaries, allowing engineers to spot overloaded partitions that create bottleneck workers during parallel table scans.

---

## 4. Query Execution and Job Telemetry Views

Job views expose physical runtime metrics, slot usage, billing volumes, and stage diagnostics.

### 4.1 Telemetry Views Summary

| View Name | Scope | Performance Columns | Primary Purpose and When to Use |
| :--- | :--- | :--- | :--- |
| **`JOBS_BY_PROJECT`** | Regional | `job_id`, `user_email`, `total_slot_ms`, `total_bytes_billed`, `query`, `error_result`, `cache_hit` | Profile expensive queries, audit billing bytes, and debug failed batch jobs. |
| **`JOBS_TIMELINE_BY_PROJECT`** | Regional | `period_start`, `job_id`, `active_slots`, `slot_ms`, `pending_units` | Detect slot starvation spikes and evaluate reservation sizing. |
| **`STREAMING_TIMELINE_BY_PROJECT`** | Regional | `table_schema`, `table_name`, `row_count`, `byte_count` | Monitor ingestion throughput and detect streaming pipeline lag. |

### 4.2 Operational Guidance for Query Profiling

The `JOBS_BY_PROJECT` view tracks every SQL job executed within a project over the preceding 180 days. Platform teams inspect this view to surface queries that scan terabytes without partition filters or burn excessive slot hours. The `JOBS_TIMELINE_BY_PROJECT` view slices slot consumption into one-second intervals. Analysts use these timeline slices to detect concurrent query spikes that exhaust slot capacity, causing downstream jobs to queue in pending states.

---

## 5. Workload Management and Slot Reservation Views

Slot pool views expose capacity commitments, tier allocations, and project assignments.

### 5.1 Reservation Views Summary

| View Name | Scope | Key Columns | Primary Purpose and When to Use |
| :--- | :--- | :--- | :--- |
| **`RESERVATIONS`** | Regional | `reservation_name`, `edition`, `slot_capacity`, `autoscale_max_slots` | Monitor baseline slots, maximum autoscale limits, and edition features. |
| **`CAPACITY_COMMITMENTS`** | Regional | `commitment_name`, `plan`, `slot_count`, `state` | Track annual and monthly slot commitments to control budget burn. |
| **`ASSIGNMENTS`** | Regional | `reservation_name`, `assignee_id`, `job_type` | Verify project routing into assigned workload pools. |
| **`BI_CAPACITIES`** | Regional | `size`, `preferred_tables` | Audit BigQuery BI Engine memory sizing and acceleration rates. |

### 5.2 Operational Guidance for Capacity Management

Platform administrators inspect reservation views to verify that high-priority production pipelines route to dedicated slot pools while ad-hoc exploratory queries execute in separate pools. Tracking baseline and autoscale slot counts ensures that dynamic workloads scale up to meet demand spikes without exceeding established budget ceilings.

---

## 6. Diagnostic Recipes and Operational Queries

Engineers execute these production recipes to audit costs, partition layouts, and query bottlenecks.

### 6.1 Identify Top Queries by Billable Bytes and Slot Duration

```sql
SELECT job_id,
       user_email,
       total_slot_ms,
       ROUND(total_slot_ms / (1000 * 60 * 60), 2)  AS slot_hours,
       ROUND(total_bytes_billed / POW(1024, 4), 2) AS billed_tb,
       cache_hit,
       SUBSTR(query, 1, 100) AS query_preview
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
 WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
   AND job_type = 'QUERY'
   AND end_time IS NOT NULL
 ORDER BY total_bytes_billed DESC
 LIMIT 20
```

### 6.2 Audit Storage Billing Savings: Physical vs. Logical Model

```sql
SELECT table_schema,
       table_name,
       ROUND(total_logical_bytes / POW(1024, 3), 2)                    AS logical_gb,
       ROUND(total_physical_bytes / POW(1024, 3), 2)                   AS physical_gb,
       ROUND(total_logical_bytes / NULLIF(total_physical_bytes, 0), 2) AS compression_ratio,
       -- Evaluate projected cost under typical regional pricing ($0.020/GB logical vs $0.040/GB physical)
       ROUND((total_logical_bytes / POW(1024, 3)) * 0.020, 2)  AS cost_logical_usd,
       ROUND((total_physical_bytes / POW(1024, 3)) * 0.040, 2) AS cost_physical_usd
  FROM `region-us.INFORMATION_SCHEMA.TABLE_STORAGE`
 WHERE total_logical_bytes > POW(1024, 3) -- Filter tables larger than 1 GB
 ORDER BY logical_gb DESC
 LIMIT 25
```

### 6.3 Detect Partition Skew and Micro-Partition Fragmentation

```sql
SELECT table_name,
       COUNT(partition_id)                                    AS total_partitions,
       ROUND(AVG(total_rows), 0)                              AS avg_rows_per_partition,
       ROUND(STDDEV(total_rows), 0)                           AS stddev_rows_per_partition,
       ROUND(MAX(total_rows) / NULLIF(MIN(total_rows), 0), 2) AS row_skew_factor,
       ROUND(SUM(total_logical_bytes) / POW(1024, 3), 2)      AS total_gb
  FROM `enterprise.warehouse.INFORMATION_SCHEMA.PARTITIONS`
 WHERE partition_id NOT IN ('__NULL__', '__UNPARTITIONED__')
 GROUP BY table_name
HAVING total_partitions > 30
 ORDER BY row_skew_factor DESC
 LIMIT 20
```

### 6.4 Find Undocumented Columns Across Gold Marts

```sql
SELECT c.table_name, c.column_name, c.data_type
  FROM `enterprise.gold_marts.INFORMATION_SCHEMA.COLUMNS` AS c
       LEFT JOIN
       `enterprise.gold_marts.INFORMATION_SCHEMA.COLUMN_OPTIONS` AS opt
       ON  c.table_name    = opt.table_name
       AND c.column_name   = opt.column_name
       AND opt.option_name = 'description'
 WHERE opt.option_value IS NULL
 ORDER BY c.table_name, c.ordinal_position
```

---

## 7. Performance Discipline When Querying System Views

Querying system views requires strict scan discipline:

- **Filter on `creation_time`:** Queries targeting job views must supply explicit range predicates over `creation_time` (`WHERE creation_time >= ...`). Omitting this filter scans all historical records in the project, burning scan budget.
- **Regional Qualifier Consistency:** Regional views mandate matching the compute job location to the regional metadata store. Running a query in `us-central1` against `region-us.INFORMATION_SCHEMA.*` triggers cross-region execution errors.
- **Access Roles:** Inspecting project-level jobs requires BigQuery Resource Admin or Viewer roles. Inspecting enterprise-level views mandates enterprise administrative roles.

---

## 8. Related References and Operational Tooling

- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for job labeling and FinOps audits.
- **Stage Diagnostics:** Consult [Query Planning and Execution](query_planning_and_execution.md) for slot metrics and execution graph triage.
- **Table Parameters:** Consult [Table and Field Options](table_and_field_options.md) for metadata parameter options.
- **Tooling & SDKs:** Consult [Tooling, CLI, and SDKs](tooling_cli_and_sdks.md) for automated CLI execution.
