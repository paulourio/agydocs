# BigQuery Data Ingestion, Loading, Export, and Scheduled Transfers

This specification defines production patterns for loading data into BigQuery tables, exporting query results, and automating recurring execution through BigQuery Data Transfer Service.

---

## 1. Declarative Ingestion: `LOAD DATA`

The `LOAD DATA` statement loads files from Google Cloud Storage directly into native BigQuery tables. It executes as an atomic operation, rolling back completely if any file corrupts or violates schema constraints. Failed jobs roll back cleanly.

### 1.1 Appending and Overwriting Data

Engineers choose between appending new records with `INTO` or replacing table contents with `OVERWRITE`. Appending preserves existing historical records, whereas overwriting truncates existing rows before loading. The SQL examples below illustrate both operations:

```sql
-- bqfmt: skip
-- Appending Parquet files with explicit schema mapping
LOAD DATA INTO `enterprise.warehouse.web_events`
FROM FILES (
  format = 'PARQUET',
  uris   = ['gs://corp-telemetry-prod/events/2026/03/*.parquet']
);

-- Overwriting existing tables with delimited CSV files and table options
LOAD DATA OVERWRITE `enterprise.staging.vendor_catalog`
OPTIONS (
  description = 'Vendor staging catalog loaded from external partner drop'
)
FROM FILES (
  format            = 'CSV',
  uris              = ['gs://corp-vendor-sync/catalog_current.csv'],
  skip_leading_rows = 1,
  field_delimiter   = '|',
  null_marker       = '\\N'
);
```

### 1.2 Hive Partitioned Ingestion

When reading external directories arranged by directory key paths (`/year=2026/month=03/`), declare partition columns directly within the statement. The `WITH PARTITION COLUMNS` clause must follow the `FROM FILES` block:

```sql
-- bqfmt: skip
LOAD DATA INTO `enterprise.telemetry.device_logs`
FROM FILES (
  format                    = 'PARQUET',
  uris                      = ['gs://corp-device-telemetry/logs/*'],
  hive_partition_uri_prefix = 'gs://corp-device-telemetry/logs'
)
WITH PARTITION COLUMNS (
  log_year  INT64,
  log_month INT64
);
```

---

## 2. Data Export: `EXPORT DATA`

The `EXPORT DATA` statement streams query results directly into external storage locations or managed database engines.

### 2.1 Export Targets and External Connections

BigQuery supports exporting query results to multiple external storage and database destinations:
- **Cloud Storage:** Native exports in `PARQUET`, `CSV`, `JSON` (`NEWLINE_DELIMITED_JSON`), and `AVRO` formats.
- **Amazon S3 and Azure Blob Storage:** Exports targeting `s3://` or `azure://` bucket paths using BigQuery Omni connections declared with `WITH CONNECTION \`project.region.connection_id\``.
- **Operational Databases:** Direct ingestion into Cloud Bigtable (`format = 'CLOUD_BIGTABLE'`), Cloud Spanner (`format = 'CLOUD_SPANNER'`), and AlloyDB (`format = 'ALLOYDB'`).
- **Streaming Sinks:** Cloud Pub/Sub topics (`format = 'CLOUD_PUBSUB'`) within continuous streaming queries.

> **Universal Metatable Restriction:** The exported query statement cannot reference metatables. Queries referencing `INFORMATION_SCHEMA` views, system tables, or wildcard tables (`table_*`) fail immediately.

### 2.2 Parquet Export with Compression

Parquet format preserves columnar compression and native data types across downstream consumers. Writing compressed files optimizes network transfer speeds and saves external Cloud Storage expenses:

```sql
EXPORT DATA
OPTIONS (
  uri         = 'gs://corp-data-exchange/exports/finance/orders_*.parquet',
  format      = 'PARQUET',
  compression = 'SNAPPY',
  overwrite   = TRUE
)
AS (
  SELECT order_id, customer_id, order_dt, order_amount
    FROM `enterprise.sales.orders_fact`
   WHERE order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
   ORDER BY order_dt DESC
);
```

### 2.3 Pipe Syntax Integration

In GoogleSQL Pipe Syntax, developers place the `EXPORT DATA` statement block at the start of the query, passing a linear pipeline as the query body:

```sql
EXPORT DATA
OPTIONS (
  uri       = 'gs://corp-data-exchange/exports/daily_summary_*.csv',
  format    = 'CSV',
  header    = TRUE,
  overwrite = TRUE
)
AS (
  FROM `enterprise.sales.orders_fact`
  |> WHERE order_dt = CURRENT_DATE()
  |> AGGREGATE
       COUNT(*)          AS order_count,
       SUM(order_amount) AS total_revenue
     GROUP BY store_id
  |> ORDER BY total_revenue DESC
);
```

---

## 3. BigQuery Continuous Queries (Real-Time Streaming SQL)

BigQuery Continuous Queries execute streaming SQL transformations over unbounded data streams. Unlike batch queries that execute once over static Colossus files, continuous queries run indefinitely. They process incoming rows as records arrive.

### 3.1 Continuous Query Declaration
A continuous query uses `CREATE CONTINUOUS QUERY` combined with `EXPORT DATA` to stream transformed records directly to Cloud Pub/Sub topics or Bigtable:

```sql
CREATE CONTINUOUS QUERY `enterprise.telemetry_08_met.fraud_alert_stream`
EXPORT DATA
OPTIONS (
  format = 'CLOUD_PUBSUB',
  uri    = '//pubsub.googleapis.com/projects/corp-prod/topics/fraud-alerts'
)
AS (
  SELECT order_id,
         customer_id,
         order_amt,
         event_ts
    FROM `enterprise.retail_01_raw.live_orders_stream`
   WHERE order_amt > 10000.00
);
```

### 3.2 Operational Lifecycle Management
Continuous queries require dedicated slot reservations assigned to continuous query workloads:
- **Inspect Status:** Check active execution state via `INFORMATION_SCHEMA.JOBS` filtering by `statement_type = 'CREATE_CONTINUOUS_QUERY'` or `continuous = TRUE`.
- **Suspend Stream:** Pause active processing using `ALTER CONTINUOUS QUERY name SUSPEND`.
- **Resume Processing:** Resume stream processing using `ALTER CONTINUOUS QUERY name RESUME`.

---

## 4. BigQuery CLI Automation (`bq load` and `bq extract`)

Batch scripts invoke the `bq` CLI utility to load or extract large data volumes inside deployment pipelines.

### 4.1 CLI Data Loading (`bq load`)

The `bq load` command provisions destination tables automatically when supplied with schema definitions. Automated deployment pipelines invoke this command to load large batches of Parquet files:

```bash
bq load \
  --source_format=PARQUET \
  --time_partitioning_field=event_ts \
  --time_partitioning_type=DAY \
  --clustering_fields=tenant_id,event_name \
  --schema_update_option=ALLOW_FIELD_ADDITION \
  enterprise:telemetry_01_raw.events_fact \
  'gs://corp-telemetry-prod/events/2026/03/15/*.parquet'
```

### 4.2 CLI Data Extraction (`bq extract`)

Export entire existing tables without formulating SQL projection queries. The CLI utility exports compressed Capacitor blocks directly into destination storage buckets:

```bash
bq extract \
  --destination_format=PARQUET \
  --compression=SNAPPY \
  enterprise:analytics_04_anl.monthly_churn_summary_agg \
  'gs://corp-exports/churn/monthly_summary_*.parquet'
```

---

## 5. Automated Scheduling: BigQuery Scheduled Queries

BigQuery Data Transfer Service executes SQL statements on recurring chronological schedules, persisting results into destination tables.

### 5.1 Provisioning Scheduled Queries via CLI


The transfer configuration setup in `bq mk` automates recurring query jobs. The service triggers scheduled executions without requiring external orchestration workers:

```bash
bq mk \
  --transfer_config \
  --data_source=scheduled_query \
  --display_name="Daily Sales Aggregation Rollup" \
  --target_dataset=analytics \
  --schedule="every 24 hours" \
  --params='{
    "query": "SELECT store_id, DATE(order_ts) AS report_dt, SUM(amount) AS daily_sales FROM `enterprise.sales.orders` WHERE DATE(order_ts) = @run_date GROUP BY store_id, report_dt",
    "destination_table_name_template": "daily_store_sales_agg",
    "write_disposition": "WRITE_APPEND",
    "partitioning_field": "report_dt"
  }'
```

### 5.2 Dynamic Parameter Substitution

BigQuery scheduled query configurations provide built-in execution parameters for date substitution:
- **`@run_date`:** Injects the target calendar date formatted as standard string tokens.
- **`@run_time`:** Injects the target execution timestamp with microsecond resolution for filtering.

```sql
SELECT transaction_id, account_id, transaction_amt, @run_date AS snapshot_dt
  FROM `enterprise.payments.cleared_transactions`
 WHERE clearing_dt = DATE_SUB(@run_date, INTERVAL 1 DAY);
```

---

## 6. Related References and Operational Tooling

- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table creation and schema definitions.
- **Pipe Syntax:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for linear pipelines.
- **Tooling & SDKs:** Consult [Tooling, CLI, and SDKs](tooling_cli_and_sdks.md) for programmatic client automation.
- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for transfer job labels.
