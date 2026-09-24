# BigQuery and GoogleSQL Engineering Workflows

This document defines four operational procedures for designing analytical queries, diagnosing slot contention and stage spills, executing schema migrations, and enforcing CI test gates.

```
+-----------------------------------------------------------------------------------+
|                              GoogleSQL Client Tier                                |
|        bq CLI        |       Go SDK (v1.79+)       |      Python SDK / Storage    |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                             Query Execution Engine                                |
|  Parser -> Resolver (ResolvedAST) -> Rewriters -> Physical Planner -> Borg Slots  |
|  - Dynamic DAG repartitioning during execution                                    |
|  - Distributed Shuffle Tier (RAM + persistent memory, spill to Colossus)          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                           Capacitor Storage Engine                                |
|  - Colossus Distributed File System (Tree-structured columnar blocks)            |
|  - Dremel encoding: Repetition levels (r) and Definition levels (d)               |
|  - Dictionary, Run-Length Encoding (RLE), Frame of Reference (FOR), Vector Quant  |
|  - Metadata-driven Partition and Cluster pruning                                  |
+-----------------------------------------------------------------------------------+
```

---

## 1. Designing Scalable Analytical Queries

Follow this systematic framework when drafting GoogleSQL queries for production workloads.

### Step 1: Identify Granularity, Schema, and Naming Standards
Define the target resolution of the output dataset. For example, choose one record per user per calendar day. Review source table schemas using [Schema Templates](../resources/schema_templates.md) or the [Schema Exporter](../scripts/extract_schema.sh) utility. Ensure target dataset identifiers conform to `<domain>_<subdomain>_<layer>` and table identifiers use approved suffixes (`_fact`, `_dim`, `_met`, `_pred`). Column identifiers must conclude with ISO 11179 class words (`_id`, `_nm`, `_dt`, `_ts`, `_val`, `_rt`).

### Step 2: Enforce Sizable Partition Filters
Locate partition columns such as `_PARTITIONDATE` or explicit date attributes. Formulate sargable boundary expressions in the base `WHERE` clause.

```sql
SELECT event_id, event_timestamp
  FROM `telemetry.raw_events`
 WHERE event_timestamp >= TIMESTAMP('2026-03-01 00:00:00 UTC')
   AND event_timestamp < TIMESTAMP('2026-03-08 00:00:00 UTC')
```

### Step 3: Eliminate Unreferenced Attributes
Prune unnecessary fields from the initial projection. When operating on complex nested records, extract specific subfields directly rather than expanding entire struct trees. Wildcard projection (`SELECT *`) is permissible only when all schema columns are verifiably required, or when selecting from localized intermediate structures such as CTEs and temporary tables. Never project `SELECT *` from external tables (BigLake, object tables, Cloud Storage formats) because schema drift is uncontrolled and can unexpectedly inflate scanned data volumes.

### Step 4: Select Join Geometries and Cardinality Ordering
Place the largest primary fact table on the left side of `JOIN`, followed by smaller dimension tables on the right. When the right-side table contains fewer than 50,000 rows, the query engine broadcasts the relation to worker slots. This broadcast eliminates network shuffle overhead.

### Step 5: Control Deduplication with Window Functions
Avoid scalar self-joins or nested `DISTINCT` passes across entire row tuples. Use window functions with the `QUALIFY` clause.

```sql
 SELECT entity_id, event_timestamp
   FROM `telemetry.raw_events`
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY entity_id
              ORDER BY event_timestamp DESC
        ) = 1
```

### Step 6: Manage Multi-Consumer Subqueries
When intermediate filters or aggregates feed multiple downstream consumer branches, evaluate whether the engine recomputes the subquery graph. For heavy pipelines where re-evaluation occurs, materialize the intermediate dataset into a temporary table (`CREATE TEMP TABLE ... AS SELECT ...`).

### Step 7: Format Clauses and Gutter Alignment
Format query clauses according to the right-aligned keyword gutter in [Style and Formatting Guidelines](style_and_formatting.md). Place `SELECT` flush at column 1, `FROM` at column 3, `WHERE` at column 2, and indent multi-line column projections by seven spaces to start at column 8. Indent multi-line joins by seven spaces under the primary relation. Wrap computed `FLOAT64` expressions in `ROUND(expr, N)`.

### Step 8: Execute Dry-Run Validation
Run the [Dry-Run Script](../scripts/dry_run.sh) to verify bytes processed. This step confirms that partition pruning eliminates unneeded historical blocks prior to executing state-changing workloads.

---

## 2. Diagnosing Slot Contention and Stage Execution Spills

When queries run slowly or exceed slot budgets, conduct stage performance triage.

```
[Query Execution Latency / Resource Spike Detected]
                        |
                        v
       Inspect BigQuery Execution Graph Stages
                        |
       +----------------+----------------+
       |                                 |
       v                                 v
[High Wait Time]                [High Compute / Disk Spill]
       |                                 |
- Slot starvation               - Skewed keys in Shuffle Join
- Insufficient reservation      - Extreme group-by cardinality
- Upstream stage delay          - Heavy unindexed regex/string parsing
       |                                 |
       v                                 v
Check Admin Slot Pools          Apply Join Salting or Approximate Functions
```

### Step 1: Inspect Execution Stage Timing Breakdown
Examine the four physical timing components across each query stage in the BigQuery console or via `INFORMATION_SCHEMA.JOBS_BY_*`. High wait time indicates slots waiting for worker assignment due to tenant concurrency limits. High read time indicates slow Colossus block retrieval, missing cluster sorting, or heavy nested record rebuilding. High compute time points to complex scalar expressions, expensive regex parsing, intensive numeric arithmetic, or massive intermediate sets. High write time indicates network saturation while writing intermediate results to the shuffle tier or outputting large final partitions.

### Step 2: Detect Shuffle Tier Spills
If the execution graph reports `Shuffle bytes spilled to disk`, intermediate records exceeded the in-memory shuffle buffer allocated to worker slots. Spilling intermediate rows to Colossus disk introduces mechanical disk latency. Remediate by pushing aggregation logic earlier into upstream stages, pre-filtering input rows, or increasing reservation slot capacity.

### Step 3: Identify Tail Latency Stragglers
Compare average slot time against maximum slot time across all worker units in an individual stage. If maximum slot time is ten times higher than average slot time, solitary slots process skewed partition keys. Mitigate by appending an artificial salt integer (`MOD(FARM_FINGERPRINT(id), 10)`) to distribute compute tasks across ten parallel slots before final aggregation.

---

## 3. Schema Setup and Table Migration

Maintain strict consistency between code artifacts, documentation, and database schemas.

### Step 1: Extract Existing Schemas
Fetch canonical table schemas from production environments using the Go extraction tool in [Go Schema Client](../examples/schema_extraction.go) or the shell wrapper.

```bash
./scripts/extract_schema.sh my-project:analytics.events -o ./schema.json
```

### Step 2: Structure Nested Data over Flat Duplication
Store repeated entities (such as line items in orders or tags on events) as nested arrays of records (`ARRAY<STRUCT<...>>`) rather than flattening them across duplicate parent rows. Nested storage preserves denormalized locality in Capacitor without storing redundant parent column blocks.

### Step 3: Define Partitioning and Clustering Specifications
Partition by timestamp, date, or integer range on the primary temporal filter column. Cluster by up to four high-cardinality attributes ordered by query frequency from general to specific (such as `tenant_id`, `event_type`, `user_id`).

### Step 4: Provision Tables via bq CLI
Execute `bq mk` with explicit partition and cluster parameters.

```bash
bq mk \
  --table \
  --time_partitioning_field=event_timestamp \
  --time_partitioning_type=DAY \
  --clustering_fields=tenant_id,event_name \
  my-project:analytics.events \
  ./schema.json
```

---

## 4. Code Quality and Formatting Verification

Maintain clean code style and deterministic cost controls inside automated CI test pipelines.

### Step 1: Enforce SQL Formatting
Run the `bqfmt` tool on all SQL query scripts to ensure two-space indentation, uppercase keywords, and standard clause gutter alignment.

```bash
bqfmt -w ./examples/optimized_patterns.sql
```

### Step 2: Execute Automated Dry-Run Cost Checks
Incorporate query cost gating into pull request pipelines using [Python Schema Utility](../examples/schema_extraction.py) or [Dry-Run Script](../scripts/dry_run.sh). Reject pull requests where individual batch queries scan unexpected terabyte-scale volumes due to missing partition predicates.

---

## 5. Related References and Operational Tooling

- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for execution planning rules.
- **Stage Diagnostics:** Consult [Query Planning and Execution](query_planning_and_execution.md) for slot contention triage.
- **Style and Formatting:** Consult [Style and Formatting Guidelines](style_and_formatting.md) for bqfmt standards.
- **Tooling & SDKs:** Consult [Tooling, CLI, and SDKs](tooling_cli_and_sdks.md) for client automation libraries.
