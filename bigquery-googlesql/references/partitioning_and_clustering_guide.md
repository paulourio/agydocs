# Partitioning and Clustering Architecture and Decision Framework

This document defines the quantitative criteria, query pattern evaluations, row distribution models, and sizing thresholds for determining BigQuery table partitioning and clustering strategies.

```
+---------------------------------------------------------------------------------------------------+
|                               Table Layout Decision Hierarchy                                     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
                                     [Is Table Size >= 10 GB?]
                                        /                  \
                                      YES                  NO
                                      /                      \
                        [Evaluate Temporal Dimension]     [Is Size >= 1 GB?]
                         /                        \            /          \
                      YES                          NO        YES           NO
                      /                              \        /             \
         [Partition + Cluster]                  [Cluster]  [Cluster]    [Flat Table]
         - Partition: Day/Month                   (Up to    (Up to 4     (No physical
         - Cluster: Top 1-4 keys                  4 keys)     keys)      reordering)
```

---

## 1. Quantitative Sizing Thresholds and Boundaries

Physical storage on Colossus organizes data into Capacitor columnar chunks. Table layout optimization requires balancing block pruning benefits against metadata management overhead:

| Layout Dimension | Target Logical Metric | Estimated Physical Size | Failure Mechanism if Violated | Operational Remediation |
| :--- | :--- | :--- | :--- | :--- |
| **Minimum Table Size for Partitioning** | $\ge 10\text{ GB}$ Logical | $\sim 1.5\text{ GB} - 3\text{ GB}$ Physical | Tables under $10\text{ GB}$ incur coordinator overhead without scan savings | Rely on clustering or flat tables |
| **Optimal Partition Segment Size** | $1\text{ GB} - 10\text{ GB}$ (Min $100\text{ MB}$) | $\sim 150\text{ MB} - 2.5\text{ GB}$ (Min $\sim 15\text{ MB}$) | Micro-partitions ($< 100\text{ MB}$) degrade slot read throughput | Coarsen granularity (`DAY` to `MONTH`) |
| **Minimum Table Size for Clustering** | $\ge 1\text{ GB}$ Logical | $\sim 150\text{ MB} - 300\text{ MB}$ Physical | Small tables ($< 1\text{ GB}$) fit inside few Capacitor stripes | Avoid clustering overhead on tiny tables |
| **Maximum Partitions per Table** | $\le 4,000$ partitions | N/A | Exceeding limit blocks DDL mutations and table writes | Enforce partition expiration or coarsen unit |
| **Maximum Clustering Columns** | $1 - 4$ columns | N/A | Columns past 4 are rejected by the query compiler | Select strictly top-four filter/join keys |

### 1.1 Logical versus Physical Storage Sizing Mechanics
Analytical sizing thresholds derive from **uncompressed logical bytes** (`total_logical_bytes`), which represent the raw schema footprint exposed in the BigQuery console and billing metadata.

#### The Compression Ratio Multiplier
Capacitor applies a two-tier compression hierarchy (columnar encodings such as Dictionary and RLE, followed by block-level Snappy, LZ4, or Zstandard compression). Analytical tables achieve compression ratios between $3:1$ and $10:1$ (averaging $4:1$ to $7:1$).
- **$10\text{ GB}$ Logical Table:** Compresses to approximately $1.5\text{ GB}$ to $3\text{ GB}$ of physical Capacitor stripes on Colossus.
- **$100\text{ MB}$ Logical Partition:** Compresses to roughly $15\text{ MB}$ to $25\text{ MB}$ of physical storage.

#### The Physics of Micro-Partitioning
A standard Capacitor stripe holds $100{,}000$ to $1{,}000{,}000$ rows, occupying tens of megabytes compressed. When partitions drop below $100\text{ MB}$ logical, each partition contains sub-stripe slivers. The query coordinator spends more slot milliseconds parsing file headers, issuing RPCs, and orchestrating Borg tasks than reading columnar values.

#### Compression Amplification via Clustering
Clustering groups identical and proximate column values into contiguous sequences within each partition. This physical ordering amplifies Run-Length Encoding and Dictionary compression, shrinking physical storage footprints by an additional 20% to 50% compared to unclustered tables.

---

## 2. Partition Granularity Selection Framework

Select partition granularity by calculating daily ingestion volume and expected table lifecycle:

```sql
-- Calculate daily ingestion volume to select partition granularity
SELECT CAST(ROUND(AVG(daily_bytes) / (1024 * 1024 * 1024), 2) AS STRING) AS avg_daily_gib,
       CAST(ROUND(MAX(daily_bytes) / (1024 * 1024 * 1024), 2) AS STRING) AS peak_daily_gib
  FROM (
         SELECT DATE(event_timestamp)     AS ingest_date,
                SUM(BYTE_LENGTH(payload)) AS daily_bytes
           FROM `telemetry.raw_stream`
          WHERE event_timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
          GROUP BY ingest_date
       )
```

### 2.1 Granularity Selection Rules
- **Hourly (`HOUR`):** Apply only when daily ingestion exceeds $1\text{ TB}$ ($\ge 40\text{ GB}$ per hour). Tables partitioned hourly reach the 4,000-partition limit in 166 days. You must configure `time_partitioning_expiration` (such as 30 to 90 days) to prune historical hours automatically.
- **Daily (`DAY`):** Standard default for analytical systems. Apply when daily ingestion spans $100\text{ MB}$ to $1\text{ TB}$. Daily partitions accommodate up to 10.9 years of historical records before hitting the 4,000-partition boundary.
- **Monthly (`MONTH`):** Apply when daily ingestion is below $100\text{ MB}$, or when total table volume spans $10\text{ GB}$ to $500\text{ GB}$ across multiple years. Monthly intervals aggregate small writes, preventing micro-partition fragmentation.
- **Yearly (`YEAR`):** Apply for multi-decade historical archives where queries filter strictly by calendar year.
- **Integer Range (`RANGE`):** Apply for non-temporal numeric identifiers (such as account IDs or shard keys) with static distributions.

---

## 3. Row Distribution, Key Skew, and Partition Health

Uneven row distributions create partition skew, degrading parallel worker performance:

```
[Balanced Daily Distribution]     [Skewed Partition Trap]
Part 2026-03-01: [ 5.2 GB ]        Part 2026-03-01: [ 0.1 GB ]
Part 2026-03-02: [ 5.1 GB ]        Part 2026-03-02: [ 0.1 GB ]
Part 2026-03-03: [ 5.4 GB ]        Part 2026-03-03: [ 184 GB ]  <-- Skew Bottleneck
Part 2026-03-04: [ 5.0 GB ]        Part 2026-03-04: [ 0.1 GB ]
```

### 3.1 Mitigating Partition Skew
- **Bulk Historical Migrations:** Backfilling historical years in a solitary transaction concentrates millions of rows into a single partition date. Stage historical backfills into distinct day batches to maintain uniform Capacitor block allocations.
- **The Null Partition Trap:** Records containing `NULL` or unparseable dates land in the special `__NULL__` partition. If data validation fails upstream, this partition swells disproportionately. Always enforce `NOT NULL` constraints on partition columns during ingest.
- **Out-of-Range Partitions:** Records with timestamps before 1960 or after 2159 land in `__UNPARTITIONED__`. Query filters on valid date ranges do not prune this partition if predicates permit null evaluations.

---

## 4. Clustering Strategy and Column Ordering Protocol

Clustering arranges rows within each partition using multi-dimensional space-filling curves and block-level zone maps.

### 4.1 Cardinality and Order of Precedence
Order cluster columns ($C_1, C_2, C_3, C_4$) strictly by query filter frequency and predicate selectivity:

1. **Primary Key ($C_1$):** Select the highest-frequency equality filter column with high cardinality (such as `customer_id`, `organization_id`, or `device_uuid`). Worker slots evaluate zone maps for $C_1$ across every physical stripe.
2. **Secondary Key ($C_2$):** Select frequent range filters or dimensional join keys (such as `order_status` or `transaction_type`).
3. **Tertiary Keys ($C_3, C_4$):** Select lower-cardinality grouping dimensions or secondary attributes frequently combined in reporting aggregations.

### 4.2 Avoid Low-Cardinality Primary Cluster Keys
Never declare low-cardinality attributes (such as boolean flags or binary status codes) as the primary cluster column $C_1$. A boolean $C_1$ divides physical data into only two zone map spans, destroying block skipping efficiency for downstream $C_2$ filters. Pair high-cardinality keys first.

---

## 5. Decision Matrix: Layout Selection by Workload Profile

| Workload Access Profile | Recommended Table Layout | Architectural Rationale |
| :--- | :--- | :--- |
| **Streaming Telemetry ($\ge 50\text{ GB}$/day)** | Partition by `DAY` + Cluster on `(tenant_id, event_type)` | Partitions isolate time ranges; clusters isolate tenant blocks within days. |
| **Customer Transaction Ledger ($\ge 500\text{ GB}$ total)** | Partition by `MONTH` + Cluster on `(account_id, txn_date)` | Monthly partitions eliminate micro-partitions; account clustering enables point lookups. |
| **Product Dimension Catalog ($5\text{ GB}$ total)** | Cluster on `(category_id, product_id)` (No partitioning) | Table size is under $10\text{ GB}$; clustering provides zone map skipping without partition metadata. |
| **Lookup Reference Table ($50\text{ MB}$ total)** | Flat table (No partitioning, no clustering) | Table fits into a single Capacitor storage stripe; pruning provides zero mechanical benefit. |
| **Global Sharded Multi-Tenant ($\ge 2\text{ TB}$)** | Partition by `INTEGER_RANGE(shard_id)` + Cluster on `customer_id` | Distributes non-temporal shards evenly across slots while clustering customer histories. |

---

## 6. Table Health Auditing via Metadata Queries

Run this diagnostic query against `INFORMATION_SCHEMA.PARTITIONS` to audit partition sizes, verify logical metrics, and identify micro-partition fragmentation:

```sql
SELECT table_name,
       COUNT(*)                                     AS total_partitions,
       ROUND(AVG(total_logical_bytes) / 1048576, 2) AS avg_partition_logical_mb,
       ROUND(MAX(total_logical_bytes) / 1048576, 2) AS max_partition_logical_mb,
       ROUND(MIN(total_logical_bytes) / 1048576, 2) AS min_partition_logical_mb
  FROM `my_project.analytics.INFORMATION_SCHEMA.PARTITIONS`
 WHERE table_name = 'user_telemetry'
   AND partition_id NOT IN ('__NULL__', '__UNPARTITIONED__')
 GROUP BY table_name
```

If average partition logical size falls below $100\text{ MB}$, migrate the schema from daily to monthly partitioning. If maximum partition size exceeds ten times the average, investigate upstream key skew.

---

## 7. Related References and Operational Tooling

- **Storage Architecture:** Consult [Storage and Capacitor Architecture](storage_and_capacitor.md) for zone maps and physical block layout.
- **Table Parameters:** Consult [Table Parameters Guide](table_and_field_options.md) for partition expiration settings.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for partition syntax across CREATE TABLE statements.
- **Query Optimization:** Consult [Query Optimization Guide](query_design_and_optimization.md) for sargable filter formulation.
