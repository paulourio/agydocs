# Capacitor and Dremel Storage Architecture

This document provides a technical specification of the physical storage architecture powering GoogleSQL and BigQuery. It details the columnar storage model derived from the Dremel paper, the physical file format of Capacitor, block-level encodings, partition and cluster pruning mechanics, and streaming ingestion storage tiers.

---

## 1. The Dremel Columnar Model: Nested and Repeated Schemas

Google's Dremel system stores multi-level nested and repeated record structures (Protocol Buffers) in a columnar representation without flattening or cross-product explosion.

```text
Field Path Resolution:
Doc.Owner.Name       -> Column 0: [values, r, d]
Doc.Links.Forward    -> Column 1: [values, r, d]
```

### 1.1 Schema Trees and Field Paths
A schema is represented as a tree of named nodes:
- Primitive scalar fields represent leaf nodes containing values.
- Intermediate `RECORD` or `STRUCT` fields represent branch nodes.
- Field declarations specify cardinality: `REQUIRED`, `OPTIONAL`, or `REPEATED`.

Every value in a table is addressed by its unique schema path. For example, in a schema with `orders.items.item_id`, the leaf field `item_id` corresponds to a dedicated physical column in storage.

### 1.2 Repetition Levels ($r$) and Definition Levels ($d$)
To reconstruct nested records from independent column files without storing record boundaries, Dremel annotates each atomic value with two integers:

#### 1. Repetition Level ($r$)
The repetition level indicates the depth in the field's schema path at which the value repeats.
- $r = 0$: Indicates the start of a new top-level row.
- $r > 0$: Indicates that the value continues an existing record and repeats at schema tree level $r$.

#### 2. Definition Level ($d$)
The definition level records how many optional or repeated ancestor fields in the path are defined (non-null).
- If a leaf value is defined, $d$ equals the maximum possible definition level for that path.
- If an ancestor is `NULL` or an array is empty, $d$ records the deepest defined ancestor.
- Storing $d$ distinguishes between an empty array, a null array, and an array containing null elements without storing explicit placeholder rows.

### 1.3 Concrete Encoding Example
Consider the following schema:

```protobuf
message Document {
  required int64 doc_id = 1;
  repeated group links = 2 {
    required int64 forward = 3;
  }
  repeated group names = 4 {
    repeated string languages = 5;
    optional string url = 6;
  }
}
```

For a document with two records:
- Record 1: `doc_id = 10`, `links.forward = [20, 30]`, `names = [{languages: ["en", "es"], url: "http://a"}, {languages: ["fr"], url: null}]`
- Record 2: `doc_id = 40`, `links = []`, `names = [{languages: [], url: "http://b"}]`

The physical column stream for `names.languages` contains the following tuples of `(value, r, d)`:

| Record | Value | Repetition Level ($r$) | Definition Level ($d$) | Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **Doc 1** | `"en"` | 0 | 2 | New top-level row ($r=0$). Both `names` and `languages` defined ($d=2$). |
| | `"es"` | 2 | 2 | Repeats at level 2 (`languages` array). |
| | `"fr"` | 1 | 2 | Repeats at level 1 (`names` array element 2). |
| **Doc 2** | `NULL` | 0 | 1 | New top-level row ($r=0$). `names` defined, but `languages` is empty ($d=1$). |

### 1.4 Record Reconstruction Algorithm
During query execution, the reader state machine reconstructs records using a finite state automaton. For each target field, the reader reads `(value, r, d)` tuples from disk. By checking $r$, the engine determines whether to close the current nested struct, close the current array, or begin a new root record. Because columns store $r$ and $d$ explicitly, queries projecting a subset of fields reconstruct only the projected subtrees, skipping unread leaf columns entirely.

---

## 2. The Capacitor File Format

Capacitor is Google's columnar storage format, serving as the physical successor to ColumnIO. Capacitor files reside on Google's distributed file system (Colossus) and organize columnar data into immutable segments.

```
+-----------------------------------------------------------------------+
|                       Capacitor File Structure                        |
+-----------------------------------------------------------------------+
|  File Header: Magic bytes ('CAP1'), format version, table UUID       |
+-----------------------------------------------------------------------+
|  Row Group 0 (Stripe)                                                |
|    - Column 0 Chunk (Metadata, Dictionary Page, Data Pages)           |
|    - Column 1 Chunk (Metadata, Min/Max Stats, Bit-Packed Data Pages)  |
|    - Column N Chunk (RLE Definition Levels, Dictionary Chunks)       |
+-----------------------------------------------------------------------+
|  Row Group 1 (Stripe)                                                |
|    - Column Chunks 0..N                                               |
+-----------------------------------------------------------------------+
|  File Footer                                                          |
|    - Row group directory and byte offsets                             |
|    - Column-level metadata and per-stripe row counts                  |
|    - Zone maps / Block-level min/max statistics for cluster pruning   |
+-----------------------------------------------------------------------+
```

### 2.1 File Layout: Stripes, Chunks, and Pages
- **File Header:** Contains magic identification bytes, format version, and table schema metadata.
- **Row Groups (Stripes):** A Capacitor file is divided horizontally into row groups containing between $100{,}000$ and $1{,}000{,}000$ rows. Each stripe holds independent column chunks, allowing parallel decompression across workers.
- **Column Chunks:** Within each stripe, data for a single column path is stored contiguously. Each chunk consists of a chunk metadata header, an optional dictionary page, and multiple data pages.
- **Data Pages:** The smallest unit of physical I/O and decompression (typically 64 KB to 1 MB). Pages store encoded leaf values along with bit-packed repetition and definition levels.
- **File Footer:** Stored at the end of the file. Contains the byte offset index for all row groups and column chunks, total row counts, and summary statistics. Readers read the footer first to locate byte ranges without scanning file contents.

### 2.2 Two-Tier Compression Hierarchy

Capacitor applies a two-tier compression hierarchy to every data page before committing blocks to Colossus:

#### Tier 1: Type-Specific Columnar Encodings
Capacitor analyzes data distributions during stripe writes and dynamically selects the most compact encoding scheme for each column chunk:
1. **Dictionary Encoding:**
   Replaces repeated strings or numbers with compact integer IDs. If a column chunk has fewer than 256 distinct values, IDs use 8-bit unsigned integers; for fewer than $65{,}536$ distinct values, IDs use 16-bit integers.
2. **Run-Length Encoding (RLE):**
   Stores consecutive identical values as `(value, count)` pairs. Highly effective for clustered or sorted columns where cardinality is low relative to row count.
3. **Bit-Packing:**
   Packs integers into the minimum number of bits required to store the maximum value in the page. For example, if all integers in a page are between 0 and 15, each value is packed into 4 bits.
4. **Frame of Reference (FOR):**
   Stores the minimum value in the page as a base offset, recording each entry as an unsigned difference ($\Delta = x - \text{base}$). This delta transformation reduces 64-bit timestamps or integers into small bit-packed offsets.
5. **Vector Quantization:**
   Used for high-dimensional numeric arrays and float embeddings. Values map to quantized centroids, reducing raw byte storage while enabling fast vector similarity scoring.

#### Tier 2: Block-Level General-Purpose Compression
After applying columnar encodings, Capacitor compresses the resulting data pages using high-throughput block compression algorithms (such as Snappy, LZ4, or Zstandard variants). Data pages (typically 64 KB to 1 MB) decompress independently, enabling parallel SIMD worker decompression without cross-page dependencies.

### 2.3 Compression Amplification via Clustering
Clustering physically reorders rows within each partition according to declared sort keys ($C_1 \to C_4$). This ordering groups identical and proximate values into contiguous sequences:
- **Encoding Synergies:** Consecutive identical values maximize RLE runs and reduce dictionary entry counts.
- **Physical Footprint Reduction:** Clustered tables typically achieve 20% to 50% smaller physical byte footprints on Colossus compared to unclustered representations of identical logical datasets.
- **Zone Map Pruning:** Zone maps in file headers permit workers to skip compressed blocks entirely without expending CPU cycles on block decompression.

### 2.4 Direct Predicate Evaluation on Encoded Data
Capacitor evaluates filter expressions directly against compressed and dictionary-encoded data without decompressing pages into memory:
- **Dictionary Filtering:** For a query with `WHERE status = 'FAILED'`, the engine looks up `'FAILED'` in the column chunk's dictionary page once. If present at index 4, the filter expression rewrites to `status_id = 4`. The scan evaluates 8-bit integer comparisons directly against vector registers. If `'FAILED'` does not exist in the dictionary page, the entire stripe drops without reading data pages.
- **SIMD Bitmask Operations:** RLE and bit-packed streams unpack directly into AVX2 or AVX-512 vector registers, generating selection bitmasks in hardware.

---

## 3. Partitioning Mechanics

Partitioning divides large tables into discrete physical segments based on a time column, ingestion timestamp, or integer range.

```
Table: `analytics.events` (Partitioned by DATE(event_timestamp))
Colossus Directory / Metadata Hierarchy:
├── Partition 2026-03-01/  -> [stripe_001.cap, stripe_002.cap] (Metadata: Min 00:00, Max 23:59)
├── Partition 2026-03-02/  -> [stripe_003.cap, stripe_004.cap]
└── Partition 2026-03-03/  -> [stripe_005.cap, stripe_006.cap]
```

### 3.1 Partition Storage Types
1. **Time-Unit Column Partitioning:**
   Partitions data using a `DATE`, `DATETIME`, or `TIMESTAMP` column. Supported granularities are `HOUR`, `DAY`, `MONTH`, or `YEAR`.
2. **Ingestion-Time Partitioning:**
   Partitions data based on the arrival time of records. GoogleSQL exposes pseudo-columns `_PARTITIONTIME` (timestamp truncated to partition boundary) and `_PARTITIONDATE` (date representation).
3. **Integer Range Partitioning:**
   Partitions tables using an `INT64` column with defined `start`, `end`, and `interval` parameters.

### 3.2 Partition Pruning at Query Compilation
When a query executes, the BigQuery engine analyzes predicates in the `WHERE` clause during logical plan optimization.
- If the filter contains static constraints on the partitioning column (for example, `WHERE event_date BETWEEN '2026-03-01' AND '2026-03-03'`), the query coordinator consults table metadata.
- Unmatched partition directories are pruned before worker slot dispatch.
- **Physical I/O impact:** Workers open and read file footers only for matched partitions. Bytes in unselected partitions contribute zero cost to bytes processed.
- **Dynamic Partition Pruning:** If the partition filter references a subquery (for example, `WHERE event_date = (SELECT MAX(date) FROM DimDates)`), pruning cannot occur at compilation. BigQuery evaluates the subquery in Stage 1, broadcasts the scalar date, and prunes partitions dynamically at runtime.

---

## 4. Clustering Mechanics

Clustering sorts and co-locates data within each partition based on the contents of up to four columns.

### 4.1 Multi-Column Ordering and Space-Filling Curves
When writing rows to Capacitor files, BigQuery sorts records using the declared clustering columns:
- **Lexicographical Sort:** By default, data is ordered primarily by column 1, then column 2, column 3, and column 4.
- **Block-Level Zone Maps:** For each column chunk and stripe, Capacitor writes the minimum and maximum values into the stripe metadata.

```
Stripe 1 Metadata: user_id [1000 .. 2500], country ['CA' .. 'US']
Stripe 2 Metadata: user_id [2501 .. 4200], country ['DE' .. 'FR']
Stripe 3 Metadata: user_id [4201 .. 9999], country ['GB' .. 'JP']
```

### 4.2 Block Pruning via Zone Maps
When a query filters on clustered fields (`WHERE user_id = 3100`):
1. The worker reads the file footer and inspects the zone maps for each stripe.
2. Stripe 1 ($1000 \le user\_id \le 2500$) and Stripe 3 ($4201 \le user\_id \le 9999$) are skipped.
3. The worker issues read requests strictly for the byte offsets of Stripe 2.
4. **Column Priority Rule:** Queries filtering on the first clustering column achieve the highest pruning ratios. Filtering on secondary clustering columns without filtering on the primary column yields degraded pruning efficiency.

### 4.3 Layout Decision Guidance
For architectural rules on table sizing thresholds, partition granularity, row skew mitigation, and cluster column ordering, consult the dedicated [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md).

---

## 5. Ingestion Architecture: Streaming Buffer vs. Base Storage

BigQuery separates low-latency ingestion from persistent columnar storage to balance real-time write availability with analytical scan performance.

```
                           Incoming Writes (Storage Write API)
                                           │
                                           ▼
                                ┌─────────────────────┐
                                │   Streaming Buffer  │ (Row-oriented LSM / Flash)
                                └──────────┬──────────┘
                                           │ Read-merge on query
              Query Engine <───────────────┼────────────────────────┐
                                           │                        │
                                           ▼                        ▼
                                ┌─────────────────────┐  ┌─────────────────────┐
                                │ Background Compact  │  │    Base Storage     │
                                └──────────┬──────────┘  │  (Capacitor Files   │
                                           │             │    on Colossus)     │
                                           └────────────>│                     │
                                                         └─────────────────────┘
```

### 5.1 The Streaming Buffer
When records arrive via the Storage Write API or legacy streaming (`tabledata.insertAll`), BigQuery writes records into an in-memory and NVMe-backed write-ahead log known as the Streaming Buffer.
- **Write Latency:** Sub-second confirmation to clients.
- **Storage Layout:** Row-oriented format optimized for append throughput rather than analytical scans.
- **Metadata Availability:** Exposed in `INFORMATION_SCHEMA.STREAMING_TIMELINE` and `bq show` as `streamingBuffer`.

### 5.2 The Read-Merge Query Process
When a query targets a table with an active streaming buffer:
1. The execution coordinator issues parallel read requests to both Base Storage (Capacitor files on Colossus) and the Streaming Buffer.
2. A union-and-merge operator unifies records from both tiers.
3. Queries read the latest committed records without waiting for disk compaction.
4. **Performance Penalty:** Scans over the streaming buffer do not benefit from full Capacitor columnar encodings, block-level clustering zone maps, or dictionary filtering. Queries scanning large uncompacted streaming buffers consume more slot milliseconds per gigabyte.

### 5.3 Background Extraction and Compaction
Background workers continuously extract records from the streaming buffer, sort them by cluster keys, apply dictionary and run-length encodings, and write optimized Capacitor files to Colossus. Once committed, the buffer log is truncated.

---

## 6. Temporary Tables and Intermediate Storage Architecture

BigQuery executes temporary data materialization using the identical storage architecture deployed for permanent tables.

### 6.1 Explicit Temporary Tables (`CREATE TEMP TABLE`)
When scripts, sessions, or stored procedures declare temporary tables:
- **Physical Persistence:** BigQuery writes temporary tables directly to Colossus in the job's temporary session dataset (`_SESSION` or `_script_...`).
- **Capacitor Columnar Storage:** Temporary tables use full Capacitor format, applying both Tier 1 columnar encodings (dictionary, RLE, bit-packing) and Tier 2 block compression.
- **Partitioning and Clustering Support:** Temporary tables support `PARTITION BY` and `CLUSTER BY` specifications. Multi-step workflows benefit from partition pruning and cluster zone map skipping across intermediate steps:
  ```sql
CREATE TEMP TABLE temp_orders
PARTITION BY order_date
  CLUSTER BY customer_id
AS (
  SELECT order_id, customer_id, order_date, order_amount
    FROM `enterprise.analytics.customer_orders`
   WHERE order_date >= '2026-03-01'
)
  ```
- **Storage Lifecycle:** Temporary tables persist for the duration of the multi-statement script or session and automatically expire without persistent storage billing charges.

### 6.2 Anonymous Cached Query Results
Queries executed without an explicit destination table store results in anonymous temporary tables:
- **Persistence Tier:** Cached result tables reside on Colossus in compressed Capacitor format.
- **Cache Invalidation:** The engine reuses compressed result tables for up to 24 hours when subsequent queries provide identical SQL syntax, identical project credentials, and undisturbed underlying table data.

### 6.3 Shuffle Spills to Disk
When distributed query stages exceed slot memory during large hash joins or aggregations, the execution engine spills shuffle records onto Colossus:
- **Serialized Compression:** Spilled shuffle buffers are serialized and compressed using lightweight block compression codecs (such as Snappy) to minimize network transfer and Colossus disk write overhead.
- **Diagnostic Signal:** Positive values for `shuffle_spilled_bytes` in stage execution profiles indicate memory exhaustion requiring query refactoring or slot quota expansion.

---

## 7. Related References and Operational Tooling

- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for zone maps and pruning boundaries.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for shuffle type-slimming and memory footprint controls.
- **Data Architecture:** Consult [Data Architecture and Lifecycle](data_architecture_and_lifecycle.md) for storage tier lifecycle rules.
- **Query Planning:** Consult [Query Planning and Distributed Execution](query_planning_and_execution.md) for dynamic DAGs and shuffle buffers.

