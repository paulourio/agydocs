# GoogleSQL Data Manipulation Language (DML) and Transactions Reference

This reference details the GoogleSQL Data Manipulation Language (DML) and multi-statement transaction engine in BigQuery. It defines syntax rules, matching semantics, partition pruning constraints, snapshot read guarantees, and Capacitor write mechanics.

```sql
-- Canonical GoogleSQL Batched MERGE Mutation
MERGE INTO `enterprise.warehouse.customer_orders` AS target
USING `enterprise.staging.orders_delta` AS source
   ON     target.order_date = source.order_date
      AND target.order_id = source.order_id
 WHEN MATCHED AND source.action_type = 'CANCEL' THEN
      UPDATE SET
        order_status = 'CANCELLED',
        updated_at   = CURRENT_TIMESTAMP()
 WHEN MATCHED AND source.action_type = 'UPDATE' THEN
      UPDATE SET
        order_amount = ROUND(source.order_amount, 2),
        order_status = source.order_status,
        updated_at   = CURRENT_TIMESTAMP()
 WHEN NOT MATCHED BY TARGET AND source.action_type = 'INSERT' THEN
      INSERT
        (
          order_id,
          customer_id,
          order_amount,
          order_status,
          order_date,
          updated_at
        )
      VALUES
        (
          source.order_id,
          source.customer_id,
          ROUND(source.order_amount, 2),
          source.order_status,
          source.order_date,
          CURRENT_TIMESTAMP()
        )
 WHEN NOT MATCHED BY SOURCE AND
        target.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
      THEN
      DELETE;
```

---

## 1. Core Statements: Grammar and Execution Semantics

GoogleSQL provides four core DML statements: `INSERT`, `UPDATE`, `DELETE`, and `TRUNCATE TABLE`.

### 1.1 `INSERT` Statement

The `INSERT` statement appends rows to target tables using literal value tuples or query results:

```sql
-- Multi-row literal insertion
INSERT INTO `enterprise.warehouse.order_events`
  (event_id, order_id, event_type, event_time)
VALUES
  ('evt_101', 'ord_501', 'CREATED', CURRENT_TIMESTAMP()),
     ('evt_102', 'ord_502', 'PAID', CURRENT_TIMESTAMP());

-- Query-driven bulk insertion
INSERT INTO `enterprise.warehouse.order_summary`
  (report_date, total_orders, gross_revenue)
SELECT order_date,
       COUNT(order_id)             AS total_orders,
       ROUND(SUM(order_amount), 2) AS gross_revenue
  FROM `enterprise.warehouse.customer_orders`
 WHERE order_date = CURRENT_DATE() - 1
 GROUP BY order_date;
```

- Target column lists can omit fields that define default values or allow `NULL` states.
- The query planner executes bulk query writes as distributed append tasks across worker slots, bypassing row-by-row write paths.

### 1.2 `UPDATE` Statement

The `UPDATE` statement alters column values in existing rows that satisfy a filter condition:

```sql
-- Simple filtered update
UPDATE `enterprise.warehouse.customer_orders`
   SET order_status = 'PROCESSED',
       updated_at   = CURRENT_TIMESTAMP()
 WHERE order_date = CURRENT_DATE() AND order_status = 'PENDING';

-- Join-style update using a secondary FROM relation
UPDATE `enterprise.warehouse.customer_orders` AS target
   SET order_amount = ROUND(source.revised_amount, 2),
       updated_at   = CURRENT_TIMESTAMP()
  FROM `enterprise.staging.price_corrections` AS source
 WHERE target.order_id = source.order_id AND target.order_date = source.order_date;
```

- Each assigned target column can appear only once in the `SET` clause.
- When an `UPDATE` references a secondary relation in the `FROM` clause, each target row must join to at most one source row. If a target row matches multiple source records, the query engine halts the query with a runtime conflict error.

### 1.3 `DELETE` Statement

The `DELETE` statement purges rows satisfying a filter predicate from target tables:

```sql
DELETE FROM `enterprise.warehouse.customer_orders`
 WHERE order_date = '2024-01-01' AND order_status = 'CANCELLED';
```

- In GoogleSQL, the `WHERE` clause is mandatory in a `DELETE` statement. Unqualified deletes without a `WHERE` clause trigger compile-time syntax errors. To delete all rows using `DELETE`, provide an unconditional predicate such as `WHERE true`.
- To clear an entire table, prefer `TRUNCATE TABLE` over an unqualified `DELETE` statement.
- **Zero-Cost Metadata Partition Deletion:** When a `DELETE` statement targets a partitioned table and the `WHERE` condition aligns strictly with partition boundaries (for example, `WHERE order_date = '2024-01-01'`) without evaluating non-partition column expressions, BigQuery executes the deletion as an instantaneous catalog metadata update. No Capacitor storage blocks are decompressed or rewritten, slot utilization remains negligible, and zero scan bytes are billed.

### 1.4 `TRUNCATE TABLE` Statement

The `TRUNCATE TABLE` statement empties a table completely without scanning underlying Capacitor files:

```sql
TRUNCATE TABLE `enterprise.staging.daily_scratch_buffer`;
```

- The engine updates table metadata in the Colossus catalog to reference an empty file set.
- This step consumes negligible slot resources, bypasses row masks, and completes instantaneously regardless of table size.

---

## 2. The `MERGE` Statement Specification

The `MERGE` statement combines conditional inserts, updates, and deletes into a solitary atomic statement.

### 2.1 Complete Syntax Grammar

GoogleSQL supports five distinct match clauses in `MERGE` statements:

```text
MERGE INTO target_table [[AS] target_alias]
USING source_table [[AS] source_alias]
   ON join_condition
[ WHEN MATCHED [AND match_condition] THEN UPDATE SET col = expr, ... ]
[ WHEN MATCHED [AND match_condition] THEN DELETE ]
[ WHEN NOT MATCHED [BY TARGET] [AND match_condition] THEN INSERT [(cols)] VALUES (vals) ]
[ WHEN NOT MATCHED BY SOURCE [AND match_condition] THEN UPDATE SET col = expr, ... ]
[ WHEN NOT MATCHED BY SOURCE [AND match_condition] THEN DELETE ]
```

### 2.2 Evaluation Sequence and Cardinality Invariants

The query engine evaluates match clauses in textual order:

1. **Target Uniqueness Rule:** A target row can match at most one source row based on the `ON` condition. If the join produces duplicate source matches for a solitary target row, the engine terminates execution and raises an error: `A target row matched more than one source row`.
2. **Clause Fall-Through:** For each row pair, the engine evaluates `WHEN MATCHED` clauses from top to bottom. The engine executes the first clause whose predicate evaluates to `TRUE` and skips remaining clauses.
3. **`WHEN NOT MATCHED BY TARGET`:** Applies when a source row finds no counterpart in the target table. This clause supports only `INSERT` actions.
4. **`WHEN NOT MATCHED BY SOURCE`:** Applies to target rows that find no counterpart in the source relation. This clause supports `UPDATE` and `DELETE` actions, enabling change-data-capture pipelines to retire or purge stale target records.

---

## 3. Partition Pruning and Scan Discipline in DML

DML statements on partitioned tables require strict filtering discipline to avoid full-table scans.

### 3.1 The Performance Cost of Unpruned DML

Partitioned tables store data in segmented physical blocks. If an `UPDATE`, `DELETE`, or `MERGE` statement omits partition filters on the target table, BigQuery scans every partition in the table. This scan saturates worker slots, incurs high query charges, and acquires write locks across every partition.

```sql
-- UNOPTIMIZED: Scans all 1,000 table partitions to modify one order
UPDATE `enterprise.warehouse.customer_orders`
   SET order_status = 'DELIVERED'
 WHERE order_id = 'ORD-98421';

-- OPTIMIZED: Prunes scan down to a single partition
UPDATE `enterprise.warehouse.customer_orders`
   SET order_status = 'DELIVERED'
 WHERE order_date = '2026-03-24' AND order_id = 'ORD-98421';
```

### 3.2 Partition Pruning in `MERGE` Queries

To prune target partitions during a basic `MERGE` lacking a `WHEN NOT MATCHED BY SOURCE` clause, place partition boundary predicates directly into the `ON` join clause:

```sql
MERGE INTO `enterprise.warehouse.customer_orders` AS target
USING `enterprise.staging.recent_updates` AS source
   ON     target.order_date = source.order_date
      AND target.order_id = source.order_id
      AND target.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
 WHEN MATCHED THEN
      UPDATE SET
        target.order_status = source.order_status;
```

- When the partition column appears on both sides of the equijoin (`target.order_date = source.order_date`), the query planner performs dynamic partition pruning based on the distinct dates present in the source dataset.
- Adding a static boundary condition (`target.order_date >= DATE_SUB(...)`) ensures that the planner limits the physical scan window before evaluating source rows.
- If the table sets `require_partition_filter = TRUE`, any DML query lacking an explicit target partition filter fails during query compilation.

### 3.3 The Catastrophic `WHEN NOT MATCHED BY SOURCE` Partition Purge Hazard

A destructive failure occurs when combining partition boundary predicates in the `ON` clause with a `WHEN NOT MATCHED BY SOURCE THEN DELETE` or `UPDATE` clause.

Under GoogleSQL join mechanics, any target row where the `ON` predicate evaluates to `FALSE` is classified as `NOT MATCHED BY SOURCE`. If an engineer places a partition boundary like `target.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)` in the `ON` clause, every historical partition older than 3 days evaluates to `FALSE`. Consequently, the query engine marks every historical row across the entire table as unmatched by the source relation and purges all historical data.

To safely prune partitions when using `WHEN NOT MATCHED BY SOURCE`:
1. **Confine `ON` predicates to key equality:** Match on business keys and partition keys (`target.order_date = source.order_date AND target.order_id = source.order_id`).
2. **Attach boundary conditions to the match clause:** Place the partition lookback filter directly on the `WHEN NOT MATCHED BY SOURCE` clause:
```sql
WHEN NOT MATCHED BY SOURCE
     AND target.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
THEN DELETE;
```
3. **Pre-filter target scope:** Alternatively, supply target partitions via an explicit parameterized array (`target.order_date IN UNNEST(g_target_dates)`).

---

---

## 4. Incremental Partition-Pruned MERGE Design Standard

When designing BigQuery tables updated by recurrent partition processing, pipelines must enforce three control fields, partition-bounded join conditions, and payload hashes. This design standard prevents full-table scans, avoids redundant writes, and tracks row lifecycles accurately.

### 4.1 Mandatory Control Attributes: load_ts, update_ts, and data_hd
Every mutated target table must separate attributes into three architectural tiers.

- **Primary Business Keys (PK):** Identify entity and temporal granularity (such as `{person_bk, month_dt}`).
- **Payload Attributes:** Business values and measurement metrics (such as `{debt_amt, delinquent_ind, active_ind}`).
- **Audit Control Fields:** Operational metadata columns tracking when rows are created, altered, and diffed.
  - `load_ts TIMESTAMP`: Timestamp recording when the row was first inserted into the target table. Set to `CURRENT_TIMESTAMP()` during initial insert. Remains immutable throughout the row lifecycle.
  - `update_ts TIMESTAMP`: Timestamp recording the most recent row mutation. Initialized to `CURRENT_TIMESTAMP()` upon insert, and refreshed to `CURRENT_TIMESTAMP()` whenever attribute values change.
  - `data_hd INT64`: Sixty-four-bit integer hash digest (`FARM_FINGERPRINT`) computed over all payload attributes, explicitly omitting primary keys and audit fields.

### 4.2 Hash Digest Calculation Mechanics
The staging delta query computes `data_hd` before evaluating the merge. Choose the calculation pattern based on schema complexity.

- **Scalar String Joining Pattern (Compact Schemas):**
  For tables with a limited number of scalar columns, coalesce nulls, convert values to strings, and delimit with pipes:
```sql
SELECT person_bk,
       month_dt,
       debt_amt,
       delinquent_ind,
       active_ind,
       FARM_FINGERPRINT(
         CONCAT(
           CAST(IFNULL(debt_amt, 0.0) AS STRING),
           '|',
           CAST(IFNULL(delinquent_ind, FALSE) AS STRING),
           '|',
           CAST(IFNULL(active_ind, FALSE) AS STRING)
         )
       ) AS data_hd
  FROM `enterprise.lend_debt_02_str.customer_debt_rec`;
```

- **Struct Serialization Pattern (Wide or Nested Schemas):**
  When schemas contain dozens of attributes or nested structs, manual string joins become error-prone. Use `SELECT AS STRUCT` with `EXCEPT` to omit keys, serializing the struct into a canonical JSON string:
```sql
SELECT a.person_bk,
       a.month_dt,
       a.debt_amt,
       a.delinquent_ind,
       a.active_ind,
       FARM_FINGERPRINT(
         TO_JSON_STRING(
           (SELECT AS STRUCT
                   a.* EXCEPT(person_bk, month_dt))
         )
       ) AS data_hd
  FROM `enterprise.lend_debt_02_str.customer_debt_rec` AS a;
```

### 4.3 Mandatory Target Partition Pruning via Parameterized Arrays
Merging without explicit target partition predicates scans the entire target table across historical years. In recurrent pipelines, declare target partition arrays to restrict scan bounds:

```sql
DECLARE g_months ARRAY<DATE> DEFAULT [DATE '2026-03-01', DATE '2026-03-02'];
```

Place the partition predicate first in the `ON` join condition:

```sql
-- bqfmt: skip
   ON     t.month_dt IN UNNEST(g_months)
      AND t.person_bk = d.person_bk
      AND t.month_dt = d.month_dt
```

BigQuery prunes unreferenced physical Capacitor blocks before evaluating row matches. In single-partition processing, substitute an array with a scalar variable (such as `t.month_dt = g_ref_dt`).

### 4.4 Empty Delta Guard and Early Exit
If an upstream ingestion pass produces zero delta records, running a merge acquires partition locks and consumes slot milliseconds needlessly. Add an explicit record guard prior to mutation:

```sql
IF
  (
    SELECT COUNT(*)
      FROM staged_customer_debt_delta_stg
  ) = 0
THEN
  RETURN;
END IF;
```

### 4.5 Change Tracking via Hash Comparison
Standard merge statements update every matched row regardless of whether payload attributes changed. Rewriting identical rows causes performance regressions by generating delete masks, writing delta blocks, and increasing compaction overhead.

Constrain the update clause with a hash inequality predicate:

```sql
-- bqfmt: skip
 WHEN MATCHED AND t.data_hd != d.data_hd THEN
      UPDATE SET
        debt_amt       = d.debt_amt,
        delinquent_ind = d.delinquent_ind,
        active_ind     = d.active_ind,
        update_ts      = CURRENT_TIMESTAMP(),
        data_hd        = d.data_hd
```

Rows with identical payloads skip the update operation entirely at the speed of a single 64-bit integer ALU comparison.

### 4.6 Complete Production Merge Script
This canonical script combines partition declarations, the empty delta guard, hash-driven change tracking, and audit column maintenance into a production procedural block:

```sql
DECLARE g_months ARRAY<DATE> DEFAULT [DATE '2026-03-01', DATE '2026-03-02'];

-- Step 1: Guard against empty staging data
IF
  (
    SELECT COUNT(*)
      FROM staged_customer_debt_delta_stg
  ) = 0
THEN
  RETURN;
END IF;

-- Step 2: Execute partition-pruned merge
MERGE INTO `enterprise.lend_debt_04_anl.customer_debt_fact` AS t
USING staged_customer_debt_delta_stg AS d
   ON     t.month_dt IN UNNEST(g_months)
      AND t.person_bk = d.person_bk
      AND t.month_dt = d.month_dt
 WHEN MATCHED AND t.data_hd != d.data_hd THEN
      UPDATE SET
        debt_amt       = d.debt_amt,
        delinquent_ind = d.delinquent_ind,
        active_ind     = d.active_ind,
        update_ts      = CURRENT_TIMESTAMP(),
        data_hd        = d.data_hd
 WHEN NOT MATCHED THEN
      INSERT
        (
          person_bk,
          month_dt,
          debt_amt,
          delinquent_ind,
          active_ind,
          load_ts,
          update_ts,
          data_hd
        )
      VALUES
        (
          d.person_bk,
          d.month_dt,
          d.debt_amt,
          d.delinquent_ind,
          d.active_ind,
          CURRENT_TIMESTAMP(),
          CURRENT_TIMESTAMP(),
          d.data_hd
        );
```

---

## 5. Multi-Statement Transactions and Snapshot Semantics

BigQuery supports ACID transactions spanning multiple statements and tables within a single script.

### 5.1 Transaction Grammar and Boundaries

Transactions begin with `BEGIN TRANSACTION` and terminate with `COMMIT TRANSACTION` or `ROLLBACK TRANSACTION`:

```sql
BEGIN
  DECLARE transfer_amount FLOAT64 DEFAULT 250.00;
  DECLARE source_acc STRING DEFAULT 'ACC-101';
  DECLARE dest_acc STRING DEFAULT 'ACC-202';

  BEGIN TRANSACTION;

  -- Step 1: Deduct balance from source account
  UPDATE `enterprise.banking.accounts`
     SET balance = balance - transfer_amount
   WHERE account_id = source_acc AND balance >= transfer_amount;

  -- Verify that deduction affected exactly one row
  IF @@row_count != 1 THEN
    RAISE USING MESSAGE = 'Transfer failed: Insufficient funds or account missing.';
  END IF;

  -- Step 2: Credit balance to destination account
  UPDATE `enterprise.banking.accounts`
     SET balance = balance + transfer_amount
   WHERE account_id = dest_acc;

  -- Step 3: Record transaction ledger audit record
  INSERT INTO `enterprise.banking.ledger`
    (source_id, dest_id, amount, transfer_time)
  VALUES
    (source_acc, dest_acc, ROUND(transfer_amount, 2), CURRENT_TIMESTAMP());

  COMMIT TRANSACTION;
EXCEPTION WHEN ERROR THEN
  -- Safely absorb OCC collision aborts where the transaction was terminated upstream
  BEGIN
    ROLLBACK TRANSACTION;
  EXCEPTION WHEN ERROR THEN
    -- Absorb error if transaction was already aborted or rolled back
  END;

  RAISE USING MESSAGE = CONCAT('Transaction aborted due to error: ', @@error.message);
END;
```

### 5.2 Snapshot Read Semantics

BigQuery executes multi-statement transactions under snapshot read guarantees:

- **Consistent Historical View:** Statements within a transaction observe a consistent snapshot of database tables taken at transaction start time.
- **Read-Your-Own-Writes:** A query inside a transaction observes all changes made by earlier statements in the same transaction block.
- **External Visibility:** External queries cannot observe intermediate transaction writes. The engine exposes committed rows to other jobs only after the `COMMIT TRANSACTION` statement finishes.

### 5.3 Optimistic Concurrency Control and Conflict Aborts

BigQuery implements optimistic concurrency control instead of row-level lock managers:

- **Conflict Detection:** The transaction coordinator tracks partition writes. When two concurrent transactions attempt to modify overlapping partitions or tables, the first transaction to run `COMMIT TRANSACTION` succeeds.
- **Abort on Collision:** The second transaction aborts with a concurrency collision error (`Transaction aborted due to concurrent update`).
- **Retry Strategy:** Client applications encountering concurrency aborts must retry the entire transaction block with exponential backoff.

### 5.4 Allowed and Prohibited Statements in Transactions

The transaction coordinator restricts the types of statements permitted within transaction blocks:

- **Permitted Statements:** `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE TEMP TABLE`, procedural control flow (`IF`, `WHILE`), and variable assignments.
- **Prohibited Statements:** Persistent DDL (`CREATE TABLE`, `ALTER TABLE`, `DROP TABLE`), dataset changes (`CREATE SCHEMA`), and export queries (`EXPORT DATA`).

---

## 6. Capacitor Storage Write Mechanics

Understanding how Capacitor handles row writes explains DML slot costs and execution latency.

### 6.1 Storage Immutability and Row Deletion Bitmaps

Capacitor stores column data in immutable file blocks on Colossus storage:

- **Base Files:** Ingested table data resides in read-only Capacitor blocks.
- **Deletion Masks:** Rather than rewriting multi-gigabyte Capacitor files for every deleted or updated row, modern BigQuery writes lightweight row delete masks. A delete mask stores a compressed bitmap of row offsets pruned by DML statements.
- **Delta Files:** Updates and inserts append new rows into small delta files alongside the delete masks.
- **Scan-Time Reconciliation:** When queries scan mutated tables, worker slots read base Capacitor files, skip masked row offsets, and merge new rows from delta files.

### 6.2 Background Compaction and Slot Latency

To prevent query read degradation from accumulated delta files, BigQuery runs background compaction:

- **Asynchronous Compaction:** Background system workers merge base Capacitor blocks, delete masks, and delta files into fresh Capacitor files.
- **Compaction Latency:** Compaction occurs asynchronously. Queries executed immediately after heavy writes incur higher slot usage because worker slots must resolve row masks dynamically during table scans.

### 6.3 Write Overhead and Micro-Batching Cadence

Executing high-frequency single-row DML statements is an anti-pattern in BigQuery:

- **Write Overhead:** Firing 10,000 independent single-row `UPDATE` statements creates thousands of delete masks and delta fragments. This pattern consumes heavy slot hours and risks exhausting partition write quotas.
- **Micro-Batching Cadence:** Stage incoming rows in an append buffer. Run batched `MERGE` queries periodically (every 15 to 60 minutes). This cadence consolidates thousands of row updates into a single distributed pass, maintaining high read throughput.

---

## 7. Related References and Operational Tooling

- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table creation and schema definitions.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for sargable joins.
- **Storage Architecture:** Consult [Storage and Capacitor Architecture](storage_and_capacitor.md) for delete mask mechanics.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](../resources/anti_patterns_catalog.md) for high-frequency DML failure modes.
- **Executable DML Patterns:** Inspect [Incremental Merge Pattern](../examples/incremental_merge_pattern.sql) and [DDL and DML Patterns](../examples/ddl_and_dml_patterns.sql) for production partition-pruned merges and multi-statement transactions.
