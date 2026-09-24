# GoogleSQL Procedural Language, Scripting, and System Routines Specification

This specification defines syntax rules, execution semantics, control flow structures, and dynamic SQL boundaries. It catalogs exception handling protocols, system variables, and administrative system procedures for GoogleSQL procedural scripting in BigQuery.

```sql
-- Canonical GoogleSQL Multi-Statement Script with Transaction and Exception Handling
DECLARE target_partition_dt DATE DEFAULT CURRENT_DATE('UTC') - 1;
DECLARE processed_records INT64 DEFAULT 0;
DECLARE retry_counter INT64 DEFAULT 0;

main_block: BEGIN
  loop_retry: LOOP
    SET retry_counter = retry_counter + 1;
    BEGIN
      BEGIN TRANSACTION;

      INSERT INTO `enterprise.warehouse.orders_partitioned`
        (order_id, customer_id, order_dt, order_amt)
      SELECT order_id, customer_id, order_dt, order_amt
        FROM `enterprise.staging.orders_ingest`
       WHERE order_dt = target_partition_dt;

      SET processed_records = @@row_count;

      DELETE FROM `enterprise.staging.orders_ingest`
       WHERE order_dt = target_partition_dt;

      COMMIT TRANSACTION;
      LEAVE loop_retry;
    EXCEPTION WHEN ERROR THEN
      BEGIN
        ROLLBACK;
      EXCEPTION WHEN ERROR THEN
        -- Absorb transaction abort if the transaction was already rolled back
      END;

      IF retry_counter >= 3 THEN
        RAISE USING MESSAGE = FORMAT('Pipeline failed after 3 attempts: %s', @@error.message);
      END IF;
    END;
  END LOOP loop_retry;
END main_block;
```

---

## 1. Script Architecture and Variable Scoping (`BEGIN...END`)

Multi-statement scripts execute sequential SQL statements within a unified query session. Borg coordinators manage variable state and control flow across execution steps.

### 1.1 Block Scoping and Nesting

The `BEGIN...END` construct groups statements into an isolated lexical scope.

```sql
-- Outer block
DECLARE outer_metric INT64 DEFAULT 100;

BEGIN
  -- Inner nested block
  DECLARE inner_metric INT64 DEFAULT 20;
  SET outer_metric = outer_metric + inner_metric;
END;

-- Accessing inner_metric here triggers a compilation error
SELECT outer_metric;
```

- **Lexical Lifetime:** Variables declared inside a `BEGIN...END` block exist only within that block and child blocks.
- **Statement Terminators:** Every procedural statement inside a block must terminate with a semicolon (`;`). Omitting semicolons between statements triggers parsing errors.
- **Statement Labels:** Blocks accept optional label identifiers. Labels clarify nesting boundaries and enable targeted exits from outer structures.

### 1.2 Variable Declarations (`DECLARE`)

The `DECLARE` statement introduces typed variables into local scope.

```sql
DECLARE variable_name [, ...] data_type [ DEFAULT default_expression ];
```

- **Placement Rule:** All `DECLARE` statements must appear at the immediate start of the script or block, preceding any procedural or operational SQL statements.
- **Default Expressions:** If the `DEFAULT` clause is omitted, the variable initializes to `NULL`. The default expression can reference earlier declared variables or deterministic functions.

### 1.3 Variable Assignment (`SET`)

GoogleSQL supports both scalar assignments and multi-variable tuple destructuring.

```sql
-- Scalar assignment
SET target_partition_dt = DATE '2026-03-01';

-- Multi-variable tuple destructuring assignment
SET (processed_records, retry_counter) = (1500, 0);

-- Query result assignment into variables
SET (processed_records, target_partition_dt) = (
  SELECT AS STRUCT COUNT(*), MAX(order_dt)
    FROM `enterprise.staging.orders_ingest`
);
```

---

## 2. Conditional Control Flow (`IF` and `CASE`)

GoogleSQL procedural scripts evaluate branching conditions via `IF` blocks and procedural `CASE` statements.

### 2.1 Branching with `IF`

```sql
IF condition_1 THEN
  -- Statements executed when condition_1 is TRUE
  CALL `enterprise.procedures.process_tier_one`();
ELSEIF condition_2 THEN
  -- Statements executed when condition_2 is TRUE
  CALL `enterprise.procedures.process_tier_two`();
ELSE
  -- Statements executed when all preceding conditions evaluate to FALSE or NULL
  CALL `enterprise.procedures.process_default`();
END IF;
```

Conditions evaluate using three-valued boolean logic. A condition branch executes only when its predicate evaluates strictly to `TRUE`. Predicates evaluating to `FALSE` or `NULL` proceed to the next branch.

### 2.2 Procedural `CASE` Statements

GoogleSQL distinguishes between scalar `CASE` expressions and procedural `CASE` statements. Scalar expressions evaluate within queries, whereas procedural statements control script flow and conclude with `END CASE`:

#### Searched `CASE` Statement
```sql
CASE
  WHEN batch_size > 100000 THEN
    CALL `enterprise.procedures.large_batch_loader`();
  WHEN batch_size > 10000 THEN
    CALL `enterprise.procedures.medium_batch_loader`();
  ELSE
    CALL `enterprise.procedures.small_batch_loader`();
END CASE;
```

#### Simple `CASE` Statement
```sql
CASE execution_env
  WHEN 'prod' THEN
    SET alert_channel = 'pagerduty';
  WHEN 'staging' THEN
    SET alert_channel = 'slack_testing';
  ELSE
    SET alert_channel = 'console_log';
END CASE;
```

> **Syntax Invariant:** Omitting the `ELSE` branch in a procedural `CASE` statement causes the script to throw a runtime error if no `WHEN` branch matches.

---

## 3. Iteration and Loop Constructs

GoogleSQL provides four looping structures for iterative tasks, retry loops, and row cursor evaluation.

### 3.1 Unconditional Loop (`LOOP`)

The `LOOP` construct executes repeatedly until halted by an explicit exit statement.

```sql
DECLARE iteration_index INT64 DEFAULT 0;

ingest_loop: LOOP
  SET iteration_index = iteration_index + 1;
  IF iteration_index > 10 THEN
    LEAVE ingest_loop;
  END IF;
END LOOP ingest_loop;
```

### 3.2 Pre-Condition Loop (`WHILE`)

The `WHILE` construct evaluates a boolean test before entering each iteration.

```sql
WHILE records_remaining > 0 DO
  CALL `enterprise.procedures.purge_chunk`(5000);
  SET records_remaining = records_remaining - 5000;
END WHILE;
```

### 3.3 Post-Condition Loop (`REPEAT...UNTIL`)

The `REPEAT` construct executes the body at least once, testing the termination predicate at loop completion.

```sql
REPEAT
  CALL `enterprise.procedures.poll_external_ingest`();
 UNTIL @@row_count > 0
END REPEAT;
```

### 3.4 Cursor Iteration Loop (`FOR...IN`)

The `FOR` loop iterates over the rows returned by a query, binding each row to an implicit loop variable.

```sql
FOR partition_rec IN (
  SELECT partition_id, total_logical_bytes
    FROM `enterprise.warehouse.INFORMATION_SCHEMA.PARTITIONS`
   WHERE table_name = 'orders_fact'
     AND total_logical_bytes > 107374182400
)
DO
  CALL `enterprise.procedures.compact_partition`(partition_rec.partition_id);
END FOR;
```

- **Variable Scope:** The loop record variable is scoped strictly to the loop body.
- **Field Access:** Attributes mirror query projection column names, such as referencing `partition_rec.partition_id`.

### 3.5 Loop Interruption: `LEAVE` and `ITERATE`

- **`LEAVE label`:** Immediately terminates the loop identified by the label.
- **`ITERATE label`:** Skips remaining statements in the current iteration and begins the next loop cycle.

---

## 4. Dynamic SQL Execution (`EXECUTE IMMEDIATE`)

The `EXECUTE IMMEDIATE` statement constructs and runs SQL statements dynamically at runtime.

### 4.1 Parameterized Dynamic SQL and Output Variables

```sql
DECLARE sql_stmt STRING;
DECLARE row_total INT64;

SET sql_stmt = 'SELECT COUNT(*) FROM `enterprise.warehouse.orders` WHERE order_status = ? AND order_amt >= ?';

EXECUTE IMMEDIATE sql_stmt
  INTO row_total
  USING 'COMPLETED', 1000.00;
```

- **`USING` Clause:** Supplies positional parameters (`?`) or named parameters (`@name`) safely. Never interpolate raw user strings into SQL commands; use parameters to eliminate injection hazards.
- **`INTO` Clause:** Captures scalar query results into declared script variables. The dynamic query must return at most one row.

### 4.2 The Universal Ban on Dynamic Procedural Constructs

GoogleSQL strictly prohibits procedural statements inside `EXECUTE IMMEDIATE`. Dynamic strings must contain standard SQL statements (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE TABLE`, `DROP TABLE`).

```sql
-- ILLEGAL: Triggers compilation error at runtime
EXECUTE IMMEDIATE 'IF condition THEN SELECT 1; END IF;';

-- ILLEGAL: Triggers compilation error at runtime
EXECUTE IMMEDIATE 'BEGIN DECLARE x INT64; END;';
```

Engineers cannot execute `IF`, `LOOP`, `WHILE`, `DECLARE`, `CALL`, or nested `BEGIN...END` blocks dynamically. Procedural control structures must remain static in the compiled script.

---

## 5. Exception Handling and Error Trapping

The `BEGIN...EXCEPTION WHEN ERROR THEN...END;` structure captures runtime failures and enables automated recovery or clean teardowns.

### 5.1 Exception Handling Structure

```sql
BEGIN
  -- Operational statements that might encounter errors
  UPDATE `enterprise.warehouse.customer_balance`
     SET balance_usd = balance_usd - 500.00
   WHERE customer_id = 9021;
EXCEPTION WHEN ERROR THEN
  -- Fallback logic executed when errors occur
  INSERT INTO `enterprise.audit.error_log`
    (error_time, error_message, statement_text)
  VALUES
    (CURRENT_TIMESTAMP(), @@error.message, @@error.statement_text);
END;
```

### 5.2 Structured Error Context Inspection

Inside the `EXCEPTION` handler block, four system variables provide forensic details about the caught error.

| System Variable | Data Type | Diagnostic Purpose |
| :--- | :--- | :--- |
| **`@@error.message`** | `STRING` | Standard error description generated by the failed statement. |
| **`@@error.statement_text`** | `STRING` | Verbatim SQL statement text that provoked the execution failure. |
| **`@@error.formatted_stack_trace`**| `STRING` | Human-readable multi-line string mapping the nested procedure call chain. |
| **`@@error.stack_trace`** | `ARRAY<STRUCT<...>>` | Structured array containing `line`, `column`, and `location` for each stack frame. |

### 5.3 User Exception Propagation (`RAISE`)

Scripts trigger custom execution exceptions using the `RAISE` statement.

```sql
IF balance_remaining < 0 THEN
  RAISE USING MESSAGE = FORMAT('Negative balance encountered: %f for account: %d', balance_remaining, account_id);
END IF;
```

Invoking `RAISE;` without arguments inside an `EXCEPTION` block re-throws the currently captured error up the procedure call hierarchy.

---

## 6. Comprehensive System Variables Reference

GoogleSQL provides twenty-two built-in system variables (`@@*`) exposing runtime metadata, job state, session properties, and error details.

### 6.1 Complete System Variables Catalog

| Variable Identifier | Data Type | Access Mode | Operational Scope and Description |
| :--- | :--- | :--- | :--- |
| **`@@project_id`** | `STRING` | Read-only | Google Cloud project executing the current query script. |
| **`@@dataset_id`** | `STRING` | Read/Write | Default dataset namespace resolved when table paths omit dataset prefixes. |
| **`@@dataset_project_id`** | `STRING` | Read/Write | Default project namespace resolved when table paths omit project prefixes. |
| **`@@current_job_id`** | `STRING` | Read-only | Unique identifier of the individual job step executing currently. |
| **`@@last_job_id`** | `STRING` | Read-only | Identifier of the most recently completed job step in the multi-statement script. |
| **`@@row_count`** | `INT64` | Read-only | Total rows inserted, updated, or deleted by the immediately preceding DML or MERGE statement. |
| **`@@session_id`** | `STRING` | Read-only | Unique session token identifying the active BigQuery multi-statement session. |
| **`@@time_zone`** | `STRING` | Read/Write | Default civil timezone evaluated by temporal routines (defaults to `'UTC'`). |
| **`@@location`** | `STRING` | Read/Write | Regional compute location assigned to the query job (must appear as statement 1). |
| **`@@reservation`** | `STRING` | Read/Write | Slot reservation resource path assigned to execute subsequent statements. |
| **`@@query_label`** | `STRING` | Read/Write | FinOps query job label attached to all subsequent child jobs in the session. |
| **`@@max_staleness_override`**| `INTERVAL` | Read/Write | Overrides staleness tolerances across materialized views and CDC tables. |
| **`@@script.job_id`** | `STRING` | Read-only | Root job identifier governing the parent multi-statement script execution. |
| **`@@script.bytes_billed`** | `INT64` | Read-only | Cumulative billable bytes accrued by the script across all completed steps. |
| **`@@script.bytes_processed`**| `INT64` | Read-only | Cumulative raw data bytes scanned by the script across all completed steps. |
| **`@@script.slot_ms`** | `INT64` | Read-only | Total slot milliseconds consumed by the script across all completed steps. |
| **`@@script.num_child_jobs`** | `INT64` | Read-only | Total count of distinct child statement jobs finished so far within the script. |
| **`@@script.creation_time`** | `TIMESTAMP` | Read-only | Absolute UTC timestamp recording when the parent script began execution. |
| **`@@error.message`** | `STRING` | Read-only | Error message string trapped inside the active EXCEPTION block. |
| **`@@error.statement_text`** | `STRING` | Read-only | Text of the specific SQL statement triggering the current EXCEPTION handler. |
| **`@@error.formatted_stack_trace`**| `STRING` | Read-only | Multi-line text trace illustrating the active procedure error hierarchy. |
| **`@@error.stack_trace`** | `ARRAY<STRUCT>` | Read-only | Array of frame objects detailing line numbers, column numbers, and routine paths. |

---

## 7. Administrative System Procedures Reference (`BQ.*`)

BigQuery provides six specialized administrative procedures under the system `BQ` namespace.

### 7.1 Complete System Procedures Specification

| Procedure Signature | Target Area | Functional Description |
| :--- | :--- | :--- |
| **`CALL BQ.ABORT_SESSION([session_id]);`** | Session Control | Terminates an active multi-statement session immediately. |
| **`CALL BQ.JOBS.CANCEL(job_id_string);`** | Job Management | Cancels an asynchronous or background running query job. |
| **`CALL BQ.CANCEL_INDEX_ALTERATION(table, index);`** | Index Operations | Halts an ongoing search or vector index alteration or rebuild. |
| **`CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE(tbl [, uris]);`** | Storage Lakehouses| Forces refresh of object table or BigLake metadata cache paths. |
| **`CALL BQ.REFRESH_MATERIALIZED_VIEW(view_name);`** | Materialized Views | Triggers synchronous batch refresh of precomputed aggregates. |
| **`CALL BQ.SHOW_GRAPH_EXPAND_SCHEMA(graph, out_var);`** | Property Graphs | Populates output string variable with schema JSON for GRAPH_EXPAND. |

### 7.2 Administrative Scripting Patterns

```sql
-- Refresh external BigLake metadata for partition directory drops
CALL BQ.REFRESH_EXTERNAL_METADATA_CACHE(
  'enterprise.lakehouse.telemetry_logs',
  ['gs://enterprise-telemetry/logs/2026/03/*']
);

-- Force synchronization of critical executive dashboard view
CALL BQ.REFRESH_MATERIALIZED_VIEW(
  'enterprise.reporting.executive_kpi_mv'
);
```

---

## 8. Assertions and Pipeline Testing (`ASSERT`)

The `ASSERT` statement validates business assumptions directly within procedural pipelines.

```sql
ASSERT condition [ AS description_expression ];
```

- **Execution Gate:** When the condition evaluates to `TRUE`, script execution proceeds.
- **Assertion Failure:** When the condition evaluates to `FALSE` or `NULL`, the script halts with an error displaying the custom message.

```sql
-- Validate partition row completeness before downstream consumption
DECLARE daily_row_count INT64;

SET daily_row_count = (
  SELECT COUNT(*)
    FROM `enterprise.warehouse.orders`
   WHERE order_dt = CURRENT_DATE() - 1
);

ASSERT daily_row_count > 0 AS FORMAT('Orders partition for %t is empty', CURRENT_DATE() - 1);
```

---

## 9. Related References and Operational Tooling

- **DML and Concurrency:** Consult [DML and Transactions Guide](dml_and_transactions.md) for multi-statement transaction rules and OCC isolation.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for stored procedure and function definitions.
- **System Telemetry:** Consult [INFORMATION_SCHEMA Guide](information_schema_reference.md) for job monitoring views.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](../resources/anti_patterns_catalog.md) for transaction pitfalls.
