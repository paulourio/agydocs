# BigQuery Query Planning and Distributed Execution Architecture

This document provides a technical specification of BigQuery distributed query execution. It details the dynamic Directed Acyclic Graph (DAG) planner, Borg slot scheduling, the remote shuffle tier, execution stage metrics, physical join mechanics, and data skew mitigation.

```text
Query Execution DAG Topology:
Stage S00 (Input: Table Scan -> Partial Filter/Hash) -> Write to Shuffle
Stage S01 (Input: Table Scan -> Broadcast Dim Table)  -> Write to Shuffle
Stage S02 (Input: S00 + S01 -> Hash Join -> Partial Agg) -> Write to Shuffle
Stage S03 (Input: S02 -> Final Agg -> Sort -> Limit) -> Emit Result
```

---

## 1. Distributed Engine Architecture: From Trees to Dynamic DAGs

Original distributed query systems (such as early Dremel) routed intermediate tuples through multi-level serving trees consisting of root, intermediate, and leaf servers. That tree architecture encountered severe network bottlenecks at intermediate nodes during large aggregations and high-cardinality joins.

BigQuery resolved tree bottlenecks by disaggregating compute from shuffle storage:
- **Borg Worker Slots:** Compute capacity is provisioned as abstract processing units called slots (virtual workers equipped with CPU cores and local memory).
- **Jupiter Network Fabric:** Google's petabit-scale bisection datacenter network connects all worker slots directly to remote shuffle and storage nodes.
- **External Shuffle Tier:** Intermediate state between execution stages is not passed peer-to-peer or routed through trees. Workers write stage partitions into a dedicated, multi-tenant memory-and-SSD shuffle cluster.
- **Dynamic Query Execution:** The query coordinator constructs an initial execution plan, but downstream stages are sized, partitioned, and scheduled dynamically at runtime based on the actual row counts and byte distributions emitted by earlier stages.

---

## 2. Anatomy of Execution Stages

BigQuery breaks SQL queries into independent execution stages ($S00, S01, S02, \dots$). Each stage represents a pipelined unit of parallel execution run across a subset of assigned worker slots.

### 2.1 Stage Structure
Each stage comprises three operational boundaries:
1. **Input Phase:** Ingests data from storage (Colossus Capacitor files, streaming buffer) or reads partitioned intermediate records from the external shuffle tier.
2. **Operations Pipeline:** Executes relational operators in memory using vectorized CPU loops (filtering, projection, hash table probing, partial aggregation).
3. **Output Phase:** Partitions output rows by hash key and writes serialized buffers to the shuffle tier, or writes final tuples to the destination result buffer.

```
+-------------------------------------------------------------------------+
|                       Execution Stage Lifecycle                         |
+-------------------------------------------------------------------------+
|  Input: Read Capacitor Chunks from Colossus or Partitions from Shuffle  |
|                                   │                                     |
|                                   ▼                                     |
|  Pipeline: Vectorized Filter -> Hash Join Probe -> Partial Aggregation  |
|                                   │                                     |
|                                   ▼                                     |
|  Output: Hash Repartition -> Serialize Proto Bytes -> Write to Shuffle  |
+-------------------------------------------------------------------------+
```

### 2.2 Operator Placement and the Shuffle Boundary
Query expressions execute either before or after intermediate stage repartitioning, dictating the physical wire payload transmitted across the external shuffle tier.

Because aggregation operators alter mathematical precision and overflow boundaries, the query planner cannot push type conversions down across an aggregate boundary. This generates two distinct physical DAG topologies:

#### Plan A: `CAST(SUM(x) AS FLOAT64)` (Post-Shuffle Output Projection)
```text
[Stage 02: Output Phase]    Project: CAST(partial_sum AS FLOAT64)
                                    ▲
[Stage 02: Compute Phase]   Aggregate: SUM(partial_sum) (128-bit NUMERIC)
                                    ▲
[Stage 01: Shuffle Tier]    Read Shuffled Partitions (16-byte NUMERIC Payload)
                                    ▲
[Stage 01: Output Phase]    Hash Repartition by Group Key
                                    ▲
[Stage 01: Compute Phase]   Partial Aggregate: SUM(x) (128-bit NUMERIC)
                                    ▲
[Stage 01: Input Phase]     Scan Capacitor Chunks (NUMERIC)
```
- **Compute Workload:** Stage 01 performs native decimal addition. Stage 02 evaluates `CAST` only once per distinct group in the final output phase.
- **Network Shuffle Payload:** Transmits 16-byte `NUMERIC` values across the Jupiter network fabric.

#### Plan B: `SUM(CAST(x AS FLOAT64))` (Pre-Shuffle Input Projection)
```text
[Stage 02: Output Phase]    Emit Final Aggregates (FLOAT64)
                                    ▲
[Stage 02: Compute Phase]   Aggregate: SUM(partial_sum) (64-bit FLOAT64)
                                    ▲
[Stage 01: Shuffle Tier]    Read Shuffled Partitions (8-byte FLOAT64 Payload)
                                    ▲
[Stage 01: Output Phase]    Hash Repartition by Group Key
                                    ▲
[Stage 01: Compute Phase]   Partial Aggregate: SUM(cast_val) (64-bit FLOAT64)
                                    ▲
[Stage 01: Input Phase]     Project: CAST(x AS FLOAT64) -> Scan Capacitor Chunks
```
- **Compute Workload:** Stage 01 evaluates `CAST` on every raw input row ($N$ operations).
- **Network Shuffle Payload:** Emits 8-byte `FLOAT64` values into the shuffle tier, halving intermediate serialization bytes, wire transit, and Stage 02 deserialization memory footprint.

---

## 3. Query Plan Diagnostics and Performance Metrics

Profiling query performance requires analyzing stage metrics in the execution plan rather than relying solely on wall-clock duration.

### 3.1 Total Slot Milliseconds vs. Elapsed Time
- **Elapsed (Wall-Clock) Time:** The real-world clock time elapsed from query submission to completion. Elapsed time fluctuates based on slot availability, cluster multi-tenancy, and network concurrency.
- **Total Slot Milliseconds:** The cumulative CPU computation time consumed by all worker slots across all stages:
  $$\text{Slot ms} = \sum_{i=1}^{N_{\text{stages}}} \sum_{j=1}^{M_{\text{slots}}} \text{CPU Time}_{i,j}$$
  Total slot time represents the true compute footprint of a query. Optimizations must aim to reduce total slot milliseconds rather than relying on noisy wall-clock measurements.

### 3.2 Stage Execution Time Breakdown
BigQuery profiles worker duration into four distinct categories:
- **Wait Time:** Time spent waiting for worker slots to be scheduled by the cluster manager, or waiting for preceding stage shuffle buffers to become available. Elevated wait time indicates cluster slot starvation or severe stage dependencies.
- **Read Time:** Time spent reading data pages from Colossus storage or reading intermediate records from the shuffle tier across the Jupiter network fabric.
- **Compute Time:** Active CPU execution time spent evaluating expressions, calculating hash codes, and sorting records in memory.
- **Write Time:** Time spent serializing record buffers and transmitting output partitions to the remote shuffle cluster.

### 3.3 Shuffle Spill to Disk
Each worker slot possesses a finite quota of high-speed memory. When the volume of intermediate records assigned to a slot exceeds its RAM buffer:
- The worker spills intermediate shuffle records onto persistent Colossus storage.
- The execution plan reports positive values for **Shuffle Spilled to Disk (Bytes)**.
- Spilling introduces disk serialization and network re-read overhead, causing significant performance degradation.

---

## 4. Physical Join Implementations

The physical optimizer selects join algorithms based on estimated input cardinalities and data distributions.

### 4.1 Broadcast Hash Join
If one table in a join is small (typically under $10\text{ MB} - 100\text{ MB}$), BigQuery selects a broadcast join strategy:
- The coordinator broadcasts the small table in its entirety to every worker slot assigned to scan the large table.
- Each worker loads the small table into an in-memory hash table.
- Workers stream through the large table, probing the hash table locally.
- **Performance Advantage:** The large table requires zero network shuffle. Workers scan base Capacitor files and emit join results directly, minimizing slot CPU consumption.

```
Broadcast Join Topology:
Dimension Table (Small)  ──(Broadcast to All Slots)──> [ Slot 1: Hash Table ]
                                                       [ Slot 2: Hash Table ]
Fact Table (Large) ──────────(Local Stream Scan)──────> [ Slot N: Hash Table ]
```

### 4.2 Hash Shuffle Join
When both joined tables exceed broadcast memory thresholds, BigQuery executes a distributed hash shuffle join:
- Workers scan Table A and hash each row's join keys, routing rows into shuffle buckets.
- Workers scan Table B and hash each row's join keys, routing rows into matching shuffle buckets.
- Downstream worker slots read corresponding buckets for both tables from the shuffle service, construct an in-memory hash table on the smaller partition, and probe it with the larger partition.
- **Performance Trade-Off:** Both relations undergo network transmission and serialization through shuffle, increasing total slot milliseconds.

```
Hash Shuffle Join Topology:
Table A ──(Hash Key)──> [ Shuffle Partition 0 ] ──> [ Slot 0: Join Probe ]
Table B ──(Hash Key)──> [ Shuffle Partition 1 ] ──> [ Slot 1: Join Probe ]
                        [ Shuffle Partition N ] ──> [ Slot N: Join Probe ]
```

---

## 5. Data Skew and Slot Stragglers

Data skew represents the primary cause of tail latency and memory exhaustion in distributed joins and aggregations.

### 5.1 Skew Mechanics
In a hash shuffle join, the worker assignment for row processing is determined by the hash value of the join key:
$$\text{Worker ID} = \text{hash}(\text{join\_key}) \pmod{N_{\text{workers}}}$$

When a dataset exhibits non-uniform key distribution, skew occurs:
- If 40% of rows contain a generic default value (such as `account_id = NULL` or `user_id = 'GUEST'`), all those tuples map to the exact same hash partition.
- While 99 workers process balanced partitions in three seconds, the single worker assigned to the skewed key must process hundreds of millions of tuples alone.
- This overwhelmed worker becomes a **straggler**, pinning the entire execution stage until it finishes.

### 5.2 Diagnostic Indicators of Data Skew
In the BigQuery execution plan, data skew exhibits three verifiable symptoms:
1. **Disparity in Worker Timings:** The maximum worker compute duration is dramatically higher than the average worker compute duration (for example: Average Slot Time: $2.1\text{s}$, Max Slot Time: $184.5\text{s}$).
2. **Isolated Disk Spill:** A single stage reports gigabytes of shuffle spill while upstream and downstream stages run entirely in memory.
3. **Long Tail Completion:** The query progress meter stays at 99% completion for the majority of the elapsed execution time.

### 5.3 Engineering Mitigations for Skew

#### 1. Pre-Filtering or Isolating Default Keys
If non-matching keys (such as `NULL` or `'UNKNOWN'`) are not needed in the final join result, filter them prior to joining:
```sql
SELECT o.order_id, c.customer_name
  FROM `retail.orders` AS o
       INNER JOIN
       `retail.customers` AS c
       ON o.customer_id = c.customer_id
 WHERE o.customer_id IS NOT NULL
```

#### 2. Key Salting (Randomized Key Distribution)
When a heavily skewed dimension key must be preserved across an aggregation or join, authors apply a salt technique:
- The skewed table appends a random integer salt from $0$ to $K-1$: `CONCAT(customer_id, '_', CAST(MOD(FARM_FINGERPRINT(GENERATE_UUID()), K) AS STRING))`.
- The matching dimension table is replicated $K$ times, cross-joining with an array of integers `[0, 1, ..., K-1]`.
- This salting operation scatters the single hot key evenly across $K$ independent workers, eliminating the slot straggler.

---

## 6. Interpreting Execution Details via INFORMATION_SCHEMA.JOBS

Engineers inspect execution details through two modalities: visual graphs in the BigQuery console and programmatic queries over `INFORMATION_SCHEMA.JOBS`. Visual graphs highlight stage hierarchies and operator blocks. The `INFORMATION_SCHEMA.JOBS_BY_*` views expose raw machine telemetry for automated pipeline audits, cost governance, and performance regression tracking.

### 6.1 View Scope and Regional Targeting
Audit views operate across three hierarchical administration scopes:
- **`JOBS_BY_USER`:** Exposes query execution history initiated by the authenticated user.
- **`JOBS_BY_PROJECT`:** Exposes execution records for all jobs submitted to the designated billing project.
- **`JOBS_BY_ORGANIZATION`:** Exposes fleet-wide telemetry across all projects within the Google Cloud organization.

All jobs views require regional qualification (for example: `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`). Queries against these views must include partition filters over `creation_time` to prevent scanning unnecessary metadata blocks.

### 6.2 Structural Breakdown of the `job_stages` Array
The `job_stages` column contains a repeated record capturing runtime telemetry for every execution stage.

| Attribute | Data Type | Physical Meaning and Diagnostic Application |
| :--- | :--- | :--- |
| **`id`** | `INT64` | Numeric identifier for the execution stage within the DAG. |
| **`name`** | `STRING` | Descriptive label displaying stage sequence and primary operation (such as `S00: Input`). |
| **`input_stages`** | `ARRAY<INT64>` | Upstream stage dependencies feeding data into this stage. Identifies the critical path. |
| **`start_ms` / `end_ms`** | `INT64` | Epoch timestamps in milliseconds marking stage lifecycle boundaries. |
| **`slot_ms`** | `INT64` | Cumulative CPU slot time consumed by worker units within this specific stage. |
| **`wait_ms_avg` / `max`** | `INT64` | Milliseconds spent waiting for worker allocation or upstream shuffle data. |
| **`read_ms_avg` / `max`** | `INT64` | Milliseconds spent reading Capacitor chunks or fetching remote shuffle buffers. |
| **`compute_ms_avg` / `max`** | `INT64` | Active CPU evaluation milliseconds for scalar expressions, hashing, and sorting. |
| **`write_ms_avg` / `max`** | `INT64` | Milliseconds spent serializing output tuples and transmitting buffers to shuffle. |
| **`records_read`** | `INT64` | Total row count ingested by the stage. |
| **`records_written`** | `INT64` | Total row count emitted by the stage after filtering and processing. |
| **`shuffle_output_bytes`** | `INT64` | Byte volume transmitted across the network into the remote shuffle cluster. |
| **`shuffle_output_bytes_spilled`** | `INT64` | Byte volume exceeding worker RAM and written to persistent storage. |
| **`parallel_inputs`** | `INT64` | Total number of parallel work units (shards) planned for the stage. |
| **`completed_parallel_inputs`**| `INT64` | Number of completed parallel work units. Equals `parallel_inputs` on success. |
| **`steps`** | `ARRAY<RECORD>`| Sequence of physical relational operators (`kind`) and operations (`substeps`). |

### 6.3 Scheduling Telemetry in the `timeline` Array
The `timeline` column captures periodic execution snapshots, sampling cluster state every few seconds:
- **`elapsed_ms`:** Elapsed execution time from query start.
- **`total_slot_ms`:** Cumulative slot milliseconds expended up to this snapshot.
- **`active_units`:** Worker slots currently computing stage tasks.
- **`completed_units`:** Work units completed since query initiation.
- **`pending_units`:** Work units queued awaiting execution.
- **`estimated_runnable_units`:** Units of work ready for scheduling immediately. When `estimated_runnable_units` exceeds `active_units` over sustained snapshots, the query suffers from slot starvation or reservation cap limits.

### 6.4 Query Governance, Performance Insights, and Acceleration
The `query_info` struct provides automated engine diagnostics:
- **`resource_warning`:** Warning text emitted when internal resource thresholds are breached (such as excessive shuffle memory consumption).
- **`query_hashes.normalized_literals`:** Hexadecimal query fingerprint that ignores literals, formatting, and comments. Enables grouping identical parameterized query patterns across historical runs.
- **`performance_insights`:** Contains engine advisories highlighting partition pruning omissions, high-cardinality join risks, and shuffle quota saturation.
- **`bi_engine_statistics.bi_engine_mode`:** Reports `FULL` when memory acceleration succeeds, `PARTIAL` when complex operators fall back to slot workers, and `DISABLED` when queries exceed allocated reservations.

---

## 7. Quantitative Diagnostic Rubric and Operational Formulas

Isolating query performance regressions requires calculating standard operational ratios from `job_stages` and `timeline` data:

### 7.1 Peak Stage Slot Concurrency
To determine the maximum concurrent slots utilized by an individual stage.
$$\text{Stage Concurrency} = \frac{\text{slot\_ms}}{\text{end\_ms} - \text{start\_ms}}$$
Contrast this value against average job concurrency.
$$\text{Job Average Concurrency} = \frac{\text{total\_slot\_ms}}{\text{end\_time} - \text{start\_time}}$$
If a single stage consumes 2,000 concurrent slots while the job average is 80 slots, sizing reservation commitments to the average will throttle that critical stage.

### 7.2 Shard Skew Factor
To detect worker slot stragglers caused by uneven key distributions.
$$\text{Skew Factor} = \frac{\text{compute\_ms\_max}}{\text{compute\_ms\_avg}}$$
- **Normal Range ($1.0 \le \text{Skew} \le 2.5$):** Balanced workload distribution across parallel workers.
- **Moderate Skew ($2.5 < \text{Skew} \le 5.0$):** Non-uniform distribution causing minor tail latency.
- **Severe Straggler ($\text{Skew} > 5.0$):** Extreme data skew. A small fraction of workers process the majority of rows. Apply key salting or filter default values prior to joining.

### 7.3 Shuffle Spill Fraction
To measure worker memory buffer exhaustion.
$$\text{Spill Fraction} = \frac{\text{shuffle\_output\_bytes\_spilled}}{\text{shuffle\_output\_bytes}}$$
Any value greater than zero indicates that intermediate state overflowed slot RAM into persistent disk storage. When `Spill Fraction` exceeds 0.20 (20%), query duration increases significantly due to disk serialization and network re-reads.

### 7.4 Input-to-Output Cardinality Expansion
To evaluate join health and filter effectiveness.
$$\text{Expansion Ratio} = \frac{\text{records\_written}}{\text{records\_read}}$$
- **Selective Filtering ($\text{Expansion} \le 0.10$):** High selectivity. Upstream filters prune the vast majority of raw rows.
- **Aggregation Phase ($0.10 < \text{Expansion} \le 1.0$):** Grouping operations condense tuples into summary records.
- **Join Explosion ($\text{Expansion} > 1.0$):** Relational joins multiply row volume. An expansion ratio greater than 10.0 signals unintentional Cartesian products or missing join predicates.

---

## 8. Production Diagnostic SQL Query Suite

These production SQL queries inspect execution details, profile stage skew, and track fleet-wide shuffle spills using `INFORMATION_SCHEMA.JOBS_BY_PROJECT`.

### 8.1 Stage-by-Stage Performance and Skew Profiler
Analyze an individual query job by unnesting its `job_stages` array:

```sql
SELECT stage.id,
       stage.name,
       stage.slot_ms,
       stage.end_ms - stage.start_ms                             AS duration_ms,
       SAFE_DIVIDE(stage.slot_ms, stage.end_ms - stage.start_ms) AS stage_concurrent_slots,
       stage.wait_ms_avg,
       stage.wait_ms_max,
       stage.read_ms_avg,
       stage.read_ms_max,
       stage.compute_ms_avg,
       stage.compute_ms_max,
       SAFE_DIVIDE(stage.compute_ms_max, stage.compute_ms_avg) AS compute_skew_ratio,
       stage.write_ms_avg,
       stage.write_ms_max,
       stage.records_read,
       stage.records_written,
       SAFE_DIVIDE(stage.records_written, stage.records_read) AS cardinality_ratio,
       stage.shuffle_output_bytes,
       stage.shuffle_output_bytes_spilled
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` AS j
       CROSS JOIN
       UNNEST(j.job_stages) AS stage
 WHERE j.job_id = 'bquxjob_5c8a1b2e_18e54739210'
   AND j.creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
 ORDER BY stage.id
```

### 8.2 Timeline Slot Starvation and Concurrency Analyzer
Examine temporal scheduling bottlenecks and runnable work queues across the lifetime of a query.

```sql
SELECT snap.elapsed_ms,
       snap.total_slot_ms,
       snap.active_units,
       snap.pending_units,
       snap.completed_units,
       snap.estimated_runnable_units
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` AS j
       CROSS JOIN
       UNNEST(j.timeline) AS snap
 WHERE j.job_id = 'bquxjob_5c8a1b2e_18e54739210'
   AND j.creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
 ORDER BY snap.elapsed_ms
```

### 8.3 Fleet-Wide Top Spill and Skew Job Hunter
Identify high-impact queries in the billing project that suffered from memory spills or extreme slot skew over the past 24 hours.

```sql
SELECT j.job_id,
       j.user_email,
       j.total_slot_ms,
       TIMESTAMP_DIFF(j.end_time, j.start_time, SECOND)                                    AS duration_seconds,
       SAFE_DIVIDE(j.total_slot_ms, TIMESTAMP_DIFF(j.end_time, j.start_time, MILLISECOND)) AS avg_slots_consumed,
       MAX(stage.shuffle_output_bytes_spilled)                                             AS max_stage_spill_bytes,
       SUM(stage.shuffle_output_bytes_spilled)                                             AS total_job_spill_bytes,
       MAX(SAFE_DIVIDE(stage.compute_ms_max, stage.compute_ms_avg))                        AS max_stage_compute_skew
  FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT` AS j
       CROSS JOIN
       UNNEST(j.job_stages) AS stage
 WHERE j.creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
   AND j.job_type = 'QUERY'
   AND j.end_time IS NOT NULL
 GROUP BY j.job_id, j.user_email, j.total_slot_ms, j.start_time, j.end_time
HAVING total_job_spill_bytes > 0
 ORDER BY total_job_spill_bytes DESC
 LIMIT 25
```

---

## 9. Related References and Operational Tooling

- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for 7-step optimization protocols.
- **System Views:** Consult [INFORMATION_SCHEMA System Views](information_schema_reference.md) for job stage schemas.
- **Language Syntax:** Consult [Language and Syntax Reference](language_and_syntax.md) for casting semantics and clause execution phases.
- **Workflows:** Consult [Engineering Workflows](engineering_workflows.md) for slot contention triage procedures.

