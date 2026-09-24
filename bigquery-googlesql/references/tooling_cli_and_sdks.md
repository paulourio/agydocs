# BigQuery Tooling Specification: CLI, Go SDK, and Python SDK

This document provides a technical specification for managing schemas, estimating query costs, and executing production workloads using the BigQuery CLI (`bq`), the Go SDK (`cloud.google.com/go/bigquery`), and the Python SDK (`google-cloud-bigquery`).

```bash
# Canonical Schema Export and Dry-Run Inspection via bq CLI
bq show --schema --format=prettyjson my-project:analytics.events > schema.json

bq query \
  --use_legacy_sql=false \
  --dry_run \
  --format=prettyjson \
  'SELECT event_id, COUNT(*) FROM `my-project.analytics.events` GROUP BY event_id'
```

---

## 1. BigQuery CLI (`bq`) Operational Architecture

The `bq` CLI Python source code resides in `platform/bq/frontend/`. Core operations execute as command subclasses (`command_query.py`, `command_show.py`, `command_load.py`).

### 1.1 Operational Flags

| Flag | Scope | Default | Technical Mechanism |
| :--- | :--- | :--- | :--- |
| `--dry_run` | `query` | `False` | Submits a `jobs.insert` request with `configuration.dryRun=true`. Returns query validity and projected scan bytes without slot execution. |
| `--use_legacy_sql=false` | `query` | `False` | Forces the GoogleSQL dialect. Required for structs, arrays, query parameters, and DDL. |
| `--format=prettyjson` | Global | `pretty` | Serializes command stdout as indented JSON. Required when piping schema representations into files. |
| `--max_rows` (-n) | `query` | `100` | Restricts terminal row emissions from the result table. |
| `--parameter` | `query` | `None` | Binds typed values (`name:type:value` or filepath) to prevent injection and enable plan caching. |
| `--label` | `query` | `None` | Attaches key-value pairs to `job.configuration.labels` for cost tracking in `INFORMATION_SCHEMA`. |
| `--priority` | `query` | `INTERACTIVE` | Sets slot scheduling priority (`INTERACTIVE` or `BATCH`). |
| `--destination_table` | `query` | `""` | Routes results into `dataset.table`, bypassing the 10 GB uncompressed anonymous query response ceiling. |
| `--clustering_fields` | `query`, `load` | `None` | Defines up to four comma-separated clustering columns for block-level zone map sorting. |
| `--time_partitioning_field` | `query`, `load` | `None` | Specifies a `TIMESTAMP`, `DATE`, or `DATETIME` column for physical partition segment pruning. |
| `--require_partition_filter` | `query`, `load` | `False` | Mandates that all queries referencing the table include a partition column predicate in the `WHERE` clause. |

### 1.2 Schema Extraction Flow and Canonical JSON Format
The schema extraction workflow fetches the table resource dictionary via the `tables.get` REST endpoint:
```bash
bq show --schema --format=prettyjson project:dataset.table
```
In `frontend/utils.py`, the CLI isolates `object_info['schema']['fields']` and serializes an array of field objects:

```json
[
  {
    "name": "event_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Unique event identifier"
  },
  {
    "name": "event_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  },
  {
    "name": "payload",
    "type": "RECORD",
    "mode": "NULLABLE",
    "fields": [
      {
        "name": "action",
        "type": "STRING",
        "mode": "REQUIRED"
      },
      {
        "name": "latency_ms",
        "type": "INT64",
        "mode": "NULLABLE"
      }
    ]
  }
]
```

---

## 2. Go BigQuery Client (`cloud.google.com/go/bigquery@v1.79.0`)

The Go client library provides idiomatic abstractions for distributed query execution and schema management.

### 2.1 Execution Lifecycle and Invariants
- **Client RPC Context vs. Server Job Timeout:** A client `context.WithTimeout` bounds the local HTTP/gRPC round-trip. In contrast, setting `Query.JobTimeout` serializes a deadline into `JobConfiguration.JobTimeoutMs`. BigQuery terminates backend execution when this server threshold is reached.
- **Dry-Run Query Invariant:** When `Query.DryRun = true`, calling `Query.Read(ctx)` fails immediately. Authors must call `Query.Run(ctx)` to submit the dry-run job. Crucially, authors must call `job.LastStatus()` to retrieve query statistics; calling `job.Status(ctx)` triggers an HTTP GET against job history, returning `404 Not Found` because dry-run jobs are never recorded.

```go
// Production Go Query Configuration
query := client.Query(`
    SELECT event_id, user_id, action
      FROM ` + "`" + projectID + ".analytics.events`" + `
     WHERE event_timestamp >= @min_time
       AND tenant_id = @tenant_id
`)
query.Priority = bigquery.BatchPriority
query.JobTimeout = 15 * time.Minute
query.Labels = map[string]string{
    "service": "auditor",
    "env":     "production",
}
query.Parameters = []bigquery.QueryParameter{
    {Name: "min_time", Value: time.Now().Add(-24 * time.Hour)},
    {Name: "tenant_id", Value: int64(1001)},
}

// Perform Dry Run Validation
query.DryRun = true
dryJob, err := query.Run(ctx)
if err != nil {
    return fmt.Errorf("dry run failed: %w", err)
}

stats := dryJob.LastStatus().Statistics.Details.(*bigquery.QueryStatistics)
fmt.Printf("Projected Scan: %d bytes\n", stats.TotalBytesProcessed)
```

### 2.2 Schema Handling and Table Management
The Go SDK converts between local structs and the CLI's standard JSON schema representation:
- `schema.ToJSONFields()`: Marshals `bigquery.Schema` into an indented JSON byte slice conforming to `TableFieldSchema[]`.
- `bigquery.SchemaFromJSON(jsonBytes)`: Parses a JSON schema byte slice back into `bigquery.Schema`.

```go
// Table creation with partitioning, clustering, and partition requirement
tableRef := client.Dataset("analytics").Table("events")
metadata := &bigquery.TableMetadata{
    Schema: targetSchema,
    TimePartitioning: &bigquery.TimePartitioning{
        Type:       bigquery.DayPartitioningType,
        Field:      "event_timestamp",
        Expiration: 90 * 24 * time.Hour,
    },
    RequirePartitionFilter: true,
    Clustering: &bigquery.Clustering{
        Fields: []string{"tenant_id", "action"},
    },
}
if err := tableRef.Create(ctx, metadata); err != nil {
    return err
}
```

---

## 3. Python BigQuery Client and Storage Write API

### 3.1 Python SDK Query and Schema Operations
```python
from google.cloud import bigquery

client = bigquery.Client(project="my-project")

# Cost estimation via dry run
job_config = bigquery.QueryJobConfig(
    dry_run=True,
    use_query_cache=False,
    priority=bigquery.QueryPriority.BATCH,
    labels={"pipeline": "daily_reconciliation"},
    query_parameters=[
        bigquery.ScalarQueryParameter("start_date", "DATE", "2026-03-01"),
    ],
)

job = client.query(
    "SELECT event_id, user_id, event_timestamp FROM `my-project.analytics.events` WHERE event_date = @start_date",
    job_config=job_config,
)

print(f"Projected Scan: {job.total_bytes_processed / (1024**3):.2f} GiB")

# Schema extraction to JSON
table = client.get_table("my-project.analytics.events")
client.schema_to_json(table.schema, "schema_exported.json")
```

### 3.2 Storage Write API Architecture
The Storage Write API (`google-cloud-bigquery-storage`) replaces the legacy `tabledata.insertAll` REST interface.
- **Transport Protocol:** Bidirectional streaming over gRPC using HTTP/2 instead of stateless HTTP/1.1 JSON serialization.
- **Data Payload:** Binary Protocol Buffers instead of JSON strings, minimizing CPU serialization overhead.
- **Stream Types:**
  - `_default`: Ingests records directly into the table with at-least-once semantics.
  - `COMMITTED`: Data becomes queryable immediately; enforces exactly-once semantics by tracking incremental append offsets.
  - `PENDING`: Buffers records until an explicit `batch_commit_write_streams` RPC commits multiple streams in an atomic transaction.

---

## 4. Metadata Discovery via `INFORMATION_SCHEMA`

BigQuery exposes relational metadata views for programmatic inspection without issuing administrative API requests:

```sql
-- Inspect Table Storage and Partition Pruning Metrics
SELECT table_name,
       total_rows,
       total_logical_bytes,
       active_logical_bytes,
       long_term_logical_bytes
  FROM `analytics.INFORMATION_SCHEMA.TABLE_STORAGE`
 WHERE total_rows > 0;

-- Track Daily Job Slot Milliseconds and Spill Metrics
SELECT project_id,
       job_id,
       total_slot_ms,
       total_bytes_billed,
       query_info.runtime_mappings
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
 WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
   AND job_type = 'QUERY'
 ORDER BY total_slot_ms DESC
 LIMIT 20;
```

---

## 5. Related References and Operational Tooling

- **Data Ingestion and Export:** Consult [Data Loading and Export](data_loading_and_export.md) for CLI load and extract flags.
- **System Views:** Consult [INFORMATION_SCHEMA System Views](information_schema_reference.md) for metadata catalog views.
- **Workflows:** Consult [Engineering Workflows](engineering_workflows.md) for automated dry-run procedures.
- **Client Utilities:** Review [Go Client](../examples/schema_extraction.go) and [Python Utility](../examples/schema_extraction.py) examples.
