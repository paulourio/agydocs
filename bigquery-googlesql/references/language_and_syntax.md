# GoogleSQL Classic Query Syntax and Language Specification

This document provides a technical specification of the GoogleSQL declarative query syntax and relational language grammar. It details clause ordering, execution phases, relational table operators, window analytics, set operations, data definition statements, and procedural scripting blocks.

```sql
-- Canonical GoogleSQL Classic Query Structure
SELECT customer_id, SUM(order_amount) AS total_revenue
  FROM `project.dataset.orders`
 WHERE order_status = 'COMPLETED'
 GROUP BY customer_id
HAVING total_revenue > 1000.00
 ORDER BY total_revenue DESC
 LIMIT 50;
```

---

## 1. Top-Level Clause Ordering and Execution Semantics

GoogleSQL enforces a declarative syntax grammar. In standard SQL, textual clause ordering diverges from the underlying logical evaluation sequence.

```
Textual Sequence:
WITH -> SELECT -> FROM -> WHERE -> GROUP BY -> HAVING -> QUALIFY -> WINDOW -> ORDER BY -> LIMIT

Logical Evaluation Pipeline:
WITH -> FROM -> WHERE -> GROUP BY -> HAVING -> WINDOW -> QUALIFY -> SELECT -> DISTINCT -> ORDER BY -> LIMIT
```

### 1.1 The Twelve Logical Execution Phases
Query execution proceeds through twelve distinct logical stages:
- **Phase 1 (`WITH` Common Table Expressions):** Evaluates declared CTE subqueries. In recursive queries, the engine executes anchor query branches before executing recursive member iterations.
- **Phase 2 (`FROM` Relational Ingestion):** Resolves base tables, joins, table-valued functions, unnesting arrays, sample clauses, pivots, and row pattern recognition.
- **Phase 3 (`WHERE` Row Filtering):** Applies boolean predicates to prune rows before grouping or analytical evaluation.
- **Phase 4 (`GROUP BY` Partitioning):** Groups rows across declared dimension keys, rollup hierarchies, or grouping sets, computing scalar aggregate expressions.
- **Phase 5 (`HAVING` Group Filtering):** Evaluates boolean predicates against grouped dimension columns and aggregated metric results.
- **Phase 6 (`WINDOW` Analytical Evaluation):** Calculates window functions across defined analytical partition boundaries and ordering frames.
- **Phase 7 (`QUALIFY` Window Filtering):** Evaluates boolean conditions directly against the output of window functions, discarding rows where the predicate evaluates to `FALSE` or `NULL`.
- **Phase 8 (`SELECT` Column Projection):** Projects scalar expressions, computes aliased column transformations, constructs nested structs, and evaluates `EXCEPT` or `REPLACE` modifiers.
- **Phase 9 (`DISTINCT` Deduplication):** Prunes duplicate output rows across projected attributes.
- **Phase 10 (Set Operations):** Combines adjacent relational streams via `UNION`, `INTERSECT`, or `EXCEPT`.
- **Phase 11 (`ORDER BY` Total Ordering):** Sorts rows across specified ordering keys, respecting collation rules and null handling.
- **Phase 12 (`LIMIT` and `OFFSET` Truncation):** Skips offset rows and restricts final row count emission.

---

## 2. Advanced Query Modifiers and Table Operators

GoogleSQL provides rich modifiers that alter tuple construction, array handling, and relational reshaping.

### 2.1 Projection Modifiers
- **`SELECT * EXCEPT (col1, col2)`:** Projects all columns while omitting explicitly excluded identifiers.
- **`SELECT * REPLACE (expression AS col1)`:** Projects all columns, substituting the value of `col1` with the evaluated expression.
- **`SELECT AS STRUCT`:** Packages the entire projected row into an anonymous or typed `STRUCT` container where column aliases define field names.
- **`SELECT AS VALUE expression`:** Emits a value table containing a single anonymous column per row, unwrapping the struct or primitive expression directly.

```sql
SELECT * EXCEPT(internal_id),
       *
       REPLACE(
         quantity * unit_price AS total_price
       )
  FROM `retail.inventory`;

SELECT AS STRUCT
       order_id, customer_id, order_total
  FROM `retail.orders`;
```

### 2.2 Relational Join Topologies
- **Standard Joins:** Supports `[INNER] JOIN`, `LEFT [OUTER] JOIN`, `RIGHT [OUTER] JOIN`, `FULL [OUTER] JOIN`, and `CROSS JOIN`.
- **Correlated Subquery Joins:** GoogleSQL does not support the `LATERAL` keyword. To execute correlated subqueries that reference outer columns for each row, combine `CROSS JOIN` or `LEFT JOIN` with `UNNEST(ARRAY(SELECT AS STRUCT ...))`:

```sql
SELECT a.account_id, recent_tx.transaction_id, recent_tx.amount
  FROM `finance.accounts` AS a
       CROSS JOIN
       UNNEST(ARRAY(
         SELECT AS STRUCT tx.transaction_id, tx.amount
           FROM `finance.transactions` AS tx
          WHERE tx.account_id = a.account_id
          ORDER BY tx.transaction_timestamp DESC
          LIMIT 3
       )) AS recent_tx;
```

### 2.3 Array Unnesting, Offsets, and Subscripting
The `UNNEST` operator flattens an `ARRAY` expression into an independent relation containing one row per element.
- **`WITH OFFSET [AS alias]`:** Emits a zero-indexed `INT64` ordinal indicating array position.
- **Null and Empty Array Unnesting:** Unnesting empty (`[]`) or `NULL` arrays produces zero rows. When using comma cross-join syntax (`FROM orders, UNNEST(items)`), the inner join silently drops the entire parent row if the array is empty or `NULL`. To preserve parent rows, engineers must specify `LEFT JOIN UNNEST(items)`.
- **Array Element Restrictions:** Arrays cannot contain `NULL` elements directly. Defining an array literal containing `NULL` (such as `[1, 2, NULL]`) triggers a compilation error.
- **Safe Subscripting:** Accessing elements with `array_expr[OFFSET(0)]` (zero-based) or `array_expr[ORDINAL(1)]` (one-based) throws a runtime boundary error if the index is out of bounds. To return `NULL` safely instead of halting query execution, engineers must invoke `array_expr[SAFE_OFFSET(0)]` or `array_expr[SAFE_ORDINAL(1)]`.

```sql
-- Unnest with LEFT JOIN to preserve parent rows with empty arrays
SELECT c.customer_id,
       t.transaction_id,
       t.amount
  FROM `retail.customers` AS c
       LEFT JOIN
       UNNEST(c.transactions) AS t;

-- Safe array subscripting protecting against out-of-bounds crashes
SELECT order_id,
       items[SAFE_OFFSET(0)].sku         AS primary_sku,
       items[SAFE_ORDINAL(1)].unit_price AS primary_price
  FROM `retail.orders`;
```

### 2.4 Reshaping Operators: `PIVOT` and `UNPIVOT`
- **`PIVOT`:** Rotates unique values from a column into distinct columns while computing aggregate functions across the remaining attributes.
- **`UNPIVOT`:** Rotates columns into key-value row representations, supporting `INCLUDE NULLS` or `EXCLUDE NULLS`.

```sql
-- PIVOT: Reshapes quarterly sales into distinct columns
SELECT product_category,
       total_sales_q1,
       total_sales_q2,
       total_sales_q3,
       total_sales_q4
  FROM (
         SELECT product_category, sales_amount, sales_quarter
           FROM `retail.quarterly_sales`
       )
       PIVOT (
         SUM(sales_amount) AS total_sales
         FOR sales_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')
       );

-- UNPIVOT: Normalizes column metrics into row tuples
SELECT product_id, quarter_code, revenue
  FROM `retail.matrix_sales`
       UNPIVOT (
         revenue
         FOR quarter_code IN (
           q1_rev AS 'Q1',
           q2_rev AS 'Q2'
         )
       );
```

### 2.5 `TABLESAMPLE` Statistical Sampling
The `TABLESAMPLE` operator reduces scan volume by reading a probabilistic sample of physical data blocks:
- **`SYSTEM (percentage PERCENT)`:** Selects physical data blocks randomly from Capacitor storage, delivering high scan throughput over petabyte tables without decoding unselected blocks.

```sql
SELECT event_id, user_id, event_payload
  FROM `telemetry.raw_events`
       TABLESAMPLE SYSTEM (1.0 PERCENT);
```

### 2.6 `MATCH_RECOGNIZE` Row Pattern Recognition
Performs regular-expression pattern matching across partitioned, ordered streams within the `FROM` clause of classic GoogleSQL queries:

- **`PARTITION BY` and `ORDER BY`:** Partitions input rows into independent sequence windows and sorts them chronologically.
- **`MEASURES`:** Defines output expressions computed over matching pattern variables (e.g. `FIRST()`, `LAST()`, `MAX()`).
- **`AFTER MATCH SKIP PAST LAST ROW`:** Governs where pattern recognition resumes after detecting a match.
- **`DEFINE`:** Specifies Boolean predicates defining each event variable. The `DEFINE` clause uses the dedicated navigation functions `PREV(col [, offset])` and `NEXT(col [, offset])` rather than analytic window functions (`LAG`/`LEAD`).

```sql
-- bqfmt: skip
SELECT ticker,
       first_price,
       peak_price,
       trough_price
  FROM `finance.stock_ticks`
       MATCH_RECOGNIZE (
         PARTITION BY ticker
         ORDER BY tick_time
         MEASURES
           FIRST(price) AS first_price,
           MAX(price)   AS peak_price,
           LAST(price)  AS trough_price
         AFTER MATCH SKIP PAST LAST ROW
         PATTERN (up+ down+)
         DEFINE
           up   AS price > PREV(price),
           down AS price < PREV(price)
       );
```

---

## 3. Chained Function Calls (Dot-Notation Syntax)

GoogleSQL supports chained function calls using the dot (`.`) character. This syntax evaluates nested scalar transformations from left to right instead of nesting function arguments inside-out.

```sql
-- Nested Function Calls (Inside-Out)
SELECT UPPER(TRIM(REGEXP_REPLACE(user_email, r'@.*', ''))) AS username
  FROM `enterprise.identity.users`;

-- Chained Function Evaluation (Left-to-Right)
SELECT (user_email).REGEXP_REPLACE(r'@.*', '').TRIM().UPPER() AS username
  FROM `enterprise.identity.users`;
```

### 3.1 Evaluation Mechanics and Argument Passing
In a chained call, each function treats the output of the preceding expression as its first positional argument. Subsequent function parameters declared within the invocation parentheses map to the second, third, and remaining positions of the target signature.

```sql
-- Equivalent: SUBSTR(CONCAT(prefix, base_token), 1, 8)
SELECT (prefix).CONCAT(base_token).SUBSTR(1, 8) AS short_token
  FROM `enterprise.security.keys`;
```

### 3.2 Syntactic Invariants and Requirements
Chained function calls must satisfy explicit parser rules:

- **Initial Expression Parenthesization:** If the chain originates from a column identifier, system variable, or literal value, the opening expression must be enclosed in parentheses. For example, `(customer_name).TRIM()` is valid, whereas `customer_name.TRIM()` triggers a syntax error because the parser treats the dot as a struct field navigation token. Subsequent functions in the chain do not require input parentheses.
- **Positional Expression Constraint:** The target function must take at least one argument, and its first parameter must accept a value expression. Functions requiring table descriptors, machine learning models, or connection paths cannot appear in scalar chains.
- **Standard Call Syntax Only:** The function must adhere to standard comma-separated parameter syntax. Language constructs using specialized keywords (such as `CAST(x AS TYPE)`, `EXTRACT(part FROM x)`, or `CASE ... END`) cannot participate in chained calls.
- **Multi-Part Function Names:** Functions scoped under namespace prefixes (such as the `SAFE.` error-suppression prefix or user-defined routines) require the function name itself to sit inside parentheses:
  ```sql
SELECT (account_balance).(SAFE.SQRT)()              AS root_balance,
       (event_payload).(analytics.extract_geo_ip)() AS geo_location
  FROM `enterprise.finance.accounts`;
  ```

### 3.3 Aggregate Functions in Chains
Chained function syntax operates across aggregate functions in grouping and window contexts. Aggregate modifiers (such as `DISTINCT` or `ORDER BY`) appear inside the call parentheses:

```sql
SELECT department_id,
       (employee_id).COUNT(DISTINCT) AS distinct_staff,
       (salary).AVG().ROUND(2)       AS average_salary
  FROM `enterprise.corp.employees`
 GROUP BY department_id;
```

### 3.4 Distinction from Pipe Syntax (`|>`)
Engineers must separate chained function calls from BigQuery Pipe Syntax (`|>`):
- **Pipe Syntax (`|>`)** operates across the relational dataflow level. Each pipe operator consumes a tabular relation and emits an altered relation.
- **Chained Function Calls (`.`)** operate across scalar expressions within individual column projections, filters, or window definitions.

Both mechanisms complement each other within unified query pipelines:

```sql
FROM `enterprise.retail.orders`
|> WHERE order_status = 'COMPLETED'
|> EXTEND (order_notes).TRIM().UPPER()                    AS clean_notes,
          (order_amount * (1.0 - discount_rate)).ROUND(2) AS final_amount
|> AGGREGATE (final_amount).SUM().ROUND(2) AS total_revenue
   GROUP BY clean_notes;
```

---

## 4. Aggregations, Window Functions, and `QUALIFY`

GoogleSQL provides analytical operations for multi-dimensional aggregation and window ranking.

### 4.1 Multi-Dimensional Grouping
- **`GROUP BY ALL`:** Infers all non-aggregated expressions in the `SELECT` list automatically.
- **`ROLLUP`:** Generates hierarchical aggregation subtotals from right to left across declared keys.
- **`CUBE`:** Produces all $2^n$ combinations of grouping columns.
- **`GROUPING SETS`:** Computes explicit aggregation subsets within a single query pass.
- **`GROUPING(column)`:** Returns `0` if the column is an active grouping element, and `1` if it has been aggregated into a subtotal.

```sql
SELECT region,
       sales_channel,
       GROUPING(region) AS is_region_subtotal,
       SUM(revenue)     AS total_revenue
  FROM `retail.sales`
 GROUP BY ROLLUP (region, sales_channel);
```

### 4.2 Window Functions, Frames, and the `QUALIFY` Clause
Window functions compute calculations across partitions without collapsing individual rows into groups.
- The `WINDOW` clause defines named, reusable window specifications.
- The `QUALIFY` clause filters rows directly using window function results, eliminating nested wrapper subqueries.

#### 4.2.1 Window Analytic Frames and Ordering Ties (`RANGE` vs. `ROWS`)
When an analytic window function includes an `ORDER BY` clause without an explicit frame specification, GoogleSQL applies the default frame `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

This default behaves differently than many developers anticipate when ordering keys contain duplicate values (ties):
- **`RANGE` Frame (Default):** Values identical to the current row in the ordering key are considered peers. The aggregation lumps all tied rows into the intermediate calculation simultaneously, emitting identical running totals for all duplicate keys.
- **`ROWS` Frame (Explicit):** Evaluates physical rows sequentially. To accumulate metrics strictly row-by-row regardless of duplicate ordering values, engineers must specify `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`.

```sql
SELECT customer_id,
       order_date,
       order_amount,
       SUM(order_amount) OVER (
         PARTITION BY customer_id
             ORDER BY order_date
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS cumulative_amount
  FROM `retail.orders`;

SELECT customer_id,
        order_id,
        order_amount,
        ROW_NUMBER() OVER w AS purchase_rank
   FROM `retail.orders`
QUALIFY purchase_rank <= 3
 WINDOW w AS (
          PARTITION BY customer_id
              ORDER BY order_amount DESC
        );
```

### 4.3 Multi-Level Aggregation (Nested Aggregations with GROUP BY Modifier)

GoogleSQL supports multi-level aggregation, allowing an aggregate function to take another aggregate function as an argument. This syntax enables nested summarization in a solitary query block without intermediate subqueries or Common Table Expressions.

```sql
-- bqfmt: skip
SELECT product,
       ROUND(AVG(SUM(revenue) GROUP BY DATE(time)), 2) AS avg_daily_sales
  FROM `enterprise.retail.sales`
 GROUP BY product;
```

#### 4.3.1 Syntax Grammar
The grammar defines an outer aggregate wrapper enclosing an inner aggregate function with an internal `GROUP BY` modifier:

```text
outer_aggregate_function(
  [ DISTINCT ]
  inner_aggregate_function(expression)
  [ GROUP BY inner_grouping_expression [, ...] [ HAVING having_expression ] ]
)
```

The inner function computes an intermediate aggregate for each subgroup defined by the `GROUP BY` modifier. The optional inner `HAVING` clause filters intermediate groups before values enter the enclosing aggregate function.

#### 4.3.2 Execution Workings and Internal Reduction
The engine resolves multi-level aggregation through a coordinated two-phase evaluation within a single execution stage:
- **Phase 1 (Inner Grouping):** Worker slots partition incoming rows by the composite set of outer `GROUP BY` columns and inner `GROUP BY` modifier expressions. The engine evaluates the inner aggregate function across each partition. If an inner `HAVING` clause is present, the worker drops intermediate rows where the predicate evaluates to `FALSE` or `NULL`.
- **Phase 2 (Outer Aggregation):** The intermediate values flow directly into the outer aggregate function. The outer function summarizes these values across the primary query grouping keys.

This execution topology eliminates intermediate shuffle barriers and temporary table materialization. The physical planner executes both hierarchical levels in a unified pipeline, conserving slot memory and network bandwidth.

#### 4.3.3 Operational Use Cases (When to Use)
Multi-level aggregation addresses three primary architectural requirements:

- **Multi-Tier Hierarchical Metrics:** Compute statistical distributions over subgroup metrics within a single pass. Common patterns include averaging daily sales totals, finding peak hourly surges per merchant, or calculating quantiles of subgroup session lengths.
- **Eliminating Overcounting Across One-to-Many Joins:** When joining parent entities with child tables (such as customers to orders, or employees to dependents), child row cardinality duplicates parent attributes. Wrapping parent metrics in `ANY_VALUE(...) GROUP BY entity_id` guarantees that each parent value enters the outer aggregate calculation exactly once.
- **Query Simplification:** Inlining multi-stage reductions eliminates verbose CTE boilerplate and subquery indirection, improving query maintainability.

```sql
-- bqfmt: skip
-- Join deduplication: Evaluates salary once per employee regardless of dependent count
SELECT ROUND(AVG(ANY_VALUE(e.salary) GROUP BY e.empno), 2) AS avg_employee_salary
  FROM `enterprise.hr.employees` AS e
       INNER JOIN
       `enterprise.hr.dependents` AS d
       USING (empno)
 WHERE d.relationship = 'Child';
```

#### 4.3.4 When Not to Use (Architectural Alternatives)
Engineers must apply alternative language constructs under the following conditions:
- **Dimensional Subtotals and Grand Totals:** When reporting requires output rows at multiple aggregation granularities, use `ROLLUP`, `CUBE`, or `GROUPING SETS`. Multi-level aggregation collapses intermediate levels into a solitary output scalar rather than emitting multi-granularity rows.
- **Preserving Row-Level Lineage:** When queries require unaggregated row details alongside group totals, use analytic window functions (`OVER (PARTITION BY ...)`).
- **Nesting Depth Beyond Two Levels:** The query engine caps multi-level aggregation at two nested functions. When metrics mandate three or more reduction tiers, declare explicit Common Table Expressions.

#### 4.3.5 Syntactic Invariants and Engine Constraints
Multi-level aggregation queries must obey five explicit compiler invariants:
- **Nesting Boundary:** Queries cannot nest more than two aggregate functions. Constructs such as `SUM(AVG(MIN(x) GROUP BY y) GROUP BY z)` trigger a compilation error.
- **Prohibited Internal Clauses:** Inner aggregate invocations cannot contain `ORDER BY`, `LIMIT`, `IGNORE NULLS`, or `RESPECT NULLS`.
- **HAVING Restrictions:** The inner modifier supports standard boolean `HAVING` conditions, but rejects `HAVING MIN` and `HAVING MAX` clauses.
- **Incompatible Features:** Multi-level aggregates cannot execute inside `PIVOT` operators, `GROUPING()` functions, differential privacy routines, or queries specifying `AGGREGATION_THRESHOLD`. Collation on grouping keys is prohibited.
- **Non-Empty Argument Invariant:** The inner function must accept an explicit column or expression argument. Wildcard arguments (such as `COUNT(* GROUP BY col)`) are invalid.

Executable implementations of official and production patterns reside in [`multi_level_aggregation.sql`](../examples/multi_level_aggregation.sql).

---

## 5. Recursive Common Table Expressions

A recursive CTE computes transitive closures and hierarchical relationships using fixed-point iteration.

```sql
WITH RECURSIVE
  OrgHierarchy AS (
    -- Anchor member
    SELECT employee_id, manager_id, 1 AS organizational_depth
      FROM `corp.employees`
     WHERE manager_id IS NULL

    UNION ALL

    -- Recursive member
    SELECT e.employee_id, e.manager_id, h.organizational_depth + 1
      FROM `corp.employees` AS e
           INNER JOIN
           OrgHierarchy AS h
           ON e.manager_id = h.employee_id
     WHERE h.organizational_depth < 20
  )
SELECT employee_id, manager_id, organizational_depth
  FROM OrgHierarchy
 ORDER BY organizational_depth, employee_id;
```

*Structural Invariants:*
- Anchor and recursive branches must be combined via `UNION ALL` (`UNION DISTINCT` is prohibited in recursive CTEs).
- The recursive member must reference the recursive target CTE exactly once in its `FROM` clause.
- Recursive members cannot include aggregate functions or window functions.

---

## 6. Data Definition Language (DDL) and Table Schemas

GoogleSQL DDL statements declare persistent database objects, storage layout topologies, and analytical routines. For the exhaustive specification covering datasets, persistent tables, views, search and vector indexes, SQL and JavaScript UDFs, TVFs, and schema evolution, consult the [Data Definition Language (DDL) Reference](ddl_reference.md).

### 6.1 `CREATE TABLE` with Partitioning and Clustering
```sql
CREATE OR REPLACE TABLE `analytics.user_events`
(
  event_id         STRING
                   NOT NULL,
  event_timestamp  TIMESTAMP
                   NOT NULL,
  user_id          INT64,
  tenant_id        INT64
                   NOT NULL,
  event_attributes JSON,
  load_date        DATE
                   NOT NULL
)
PARTITION BY load_date
  CLUSTER BY tenant_id, user_id
OPTIONS (
  description               = 'Partitioned user telemetry events',
  require_partition_filter  = TRUE,
  partition_expiration_days = 365
);
```

### 6.2 Materialized Views
Materialized views compute query results periodically in the background and expose query rewrite acceleration:

```sql
CREATE MATERIALIZED VIEW `analytics.daily_revenue_mv`
PARTITION BY report_date
  CLUSTER BY tenant_id
AS (
  SELECT DATE(event_timestamp) AS report_date,
         tenant_id,
         COUNT(*)         AS total_events,
         SUM(order_value) AS aggregate_revenue
    FROM `analytics.user_events`
   GROUP BY report_date, tenant_id
);
```

---

## 7. Procedural Language and Multi-Statement Scripting

GoogleSQL procedural scripting enables control flow, dynamic query execution, and transactional semantics.

```sql
DECLARE target_date DATE DEFAULT CURRENT_DATE('UTC') - 1;
DECLARE affected_rows INT64;

BEGIN
  CREATE TEMP TABLE DailyStaging
  AS (
    SELECT order_id, customer_id, order_amount
      FROM `retail.raw_orders`
     WHERE order_date = target_date
  );

  MERGE INTO `retail.daily_orders` AS target
  USING DailyStaging AS source
     ON target.order_id = source.order_id
   WHEN MATCHED THEN
        UPDATE SET
          order_amount = source.order_amount,
          updated_at   = CURRENT_TIMESTAMP()
   WHEN NOT MATCHED THEN
        INSERT
          (order_id, customer_id, order_amount, updated_at)
        VALUES
          (source.order_id, source.customer_id, source.order_amount, CURRENT_TIMESTAMP());

  SET affected_rows = @@row_count;
EXCEPTION WHEN ERROR THEN
  RAISE USING MESSAGE = CONCAT('Pipeline failed during date processing: ', @@error.message);
END;
```

### 7.1 Control Flow Statements
- **Variable Declarations:** `DECLARE variable_name TYPE [DEFAULT expression]`.
- **Assignment:** `SET variable_name = expression`.
- **Branching:** `IF ... THEN ... ELSEIF ... ELSE ... END IF`.
- **Iteration:** `LOOP`, `WHILE condition DO`, `REPEAT ... UNTIL`, `FOR var IN (query) DO`.
- **Dynamic SQL:** `EXECUTE IMMEDIATE dynamic_sql_string [INTO var1, var2] [USING param1, param2]`.
- **Exception Handling:** `BEGIN ... EXCEPTION WHEN ERROR THEN ... END`.

---

## 8. Native JSON Operations and Semi-Structured Data

GoogleSQL provides native binary `JSON` support. This format stores nested data structures efficiently and permits schema-agnostic querying without JSON string re-parsing.

### 8.1 Path Navigation and Subscripting
Engineers extract JSON elements using dot notation or bracket subscripting. Path expressions return values of type `JSON`:

```sql
SELECT payload_json.user.id               AS user_json,
       payload_json['user']['address'][0] AS primary_address_json
  FROM `enterprise.telemetry_01_raw.events_fact`;
```

### 8.2 Type Casting and Scalar Extraction
Because path navigation yields `JSON` tokens, engineers cast values to SQL primitive types using explicit scalar constructors:
- `STRING(json_expr)`: Extracts a scalar string without enclosing JSON quotes.
- `INT64(json_expr)`: Parses numeric JSON integers into 64-bit signed integers.
- `FLOAT64(json_expr)`: Parses floating-point numbers into 64-bit floats.
- `BOOL(json_expr)`: Converts JSON booleans into SQL booleans.

```sql
SELECT STRING(payload_json.user.email) AS user_email,
       INT64(payload_json.user.age)    AS user_age,
       BOOL(payload_json.is_active)    AS active_ind
  FROM `enterprise.telemetry_01_raw.events_fact`;
```

### 8.3 Safe Parsing and Lax Conversion Functions
- **`PARSE_JSON(string_expr)`:** Parses a JSON-formatted string into native `JSON`. If the string is malformed, evaluation fails.
- **`SAFE.PARSE_JSON(string_expr)`:** Returns `NULL` if the input string contains invalid JSON syntax.
- **`JSON_VALUE(json_expr [, json_path])`:** Extracts a scalar value as SQL `STRING`.
- **`JSON_QUERY(json_expr [, json_path])`:** Extracts a sub-object or array as native `JSON`.
- **`JSON_QUERY_ARRAY(json_expr [, json_path])`:** Extracts a JSON array as `ARRAY<JSON>`.
- **`JSON_VALUE_ARRAY(json_expr [, json_path])`:** Extracts a JSON array of scalar strings as `ARRAY<STRING>`.
- **`LAX_INT64(json_expr)`:** Extracts an integer or parses a numeric string as `INT64`, returning `NULL` on type mismatch.
- **`LAX_STRING(json_expr)`:** Converts scalar JSON strings, numbers, or booleans into SQL `STRING`.
- **`LAX_BOOL(json_expr)`:** Parses boolean literals or string boolean tokens into SQL `BOOL`.
- **`LAX_FLOAT64(json_expr)`:** Parses floating-point numbers or numeric strings into SQL `FLOAT64`.

### 8.4 Array Unnesting with JSON
Engineers combine `JSON_QUERY_ARRAY()` with `UNNEST()` to iterate over dynamic JSON collections:

```sql
SELECT event_id,
       STRING(item.sku) AS sku_cd,
       INT64(item.qty)  AS item_qty
  FROM `enterprise.telemetry_01_raw.events_fact`,
       UNNEST(JSON_QUERY_ARRAY(payload_json.items)) AS item;
```

---

## 9. Type Casting Semantics, Rounding, and Precision Controls

GoogleSQL enforces strict type safety and deterministic casting semantics across integer, floating-point, and high-precision decimal domains.

### 9.1 `CAST(... AS INT64)` Rounding vs. Truncation
In GoogleSQL, casting fractional values or fixed-point decimals to integers does not truncate toward zero. The specification mandates **round-half-away-from-zero**:
- The expression `CAST(1.4 AS INT64)` yields `1`.
- The expression `CAST(1.5 AS INT64)` yields `2`.
- The expression `CAST(-1.5 AS INT64)` yields `-2`.

If business logic requires truncation toward zero, engineers must explicitly invoke `TRUNC()`:
```sql
-- Rounding (Default GoogleSQL CAST semantics: half-away-from-zero)
SELECT CAST(1.5 AS INT64) AS rounded_val; -- Returns 2

-- Truncation (Explicit integer truncation toward zero)
SELECT CAST(TRUNC(1.5) AS INT64) AS truncated_val; -- Returns 1
```

### 9.2 Safe Casting with `SAFE_CAST`
Standard `CAST(expr AS target_type)` triggers a runtime query failure if the input string or value cannot be converted or causes numerical overflow. In contrast, `SAFE_CAST` returns `NULL` when conversion fails:
```sql
SELECT SAFE_CAST('2026-03-01' AS DATE)   AS valid_dt,
       SAFE_CAST('invalid_date' AS DATE) AS null_dt;
```

### 9.3 Numeric Precision and Mantissa Capacity
Engineers select numeric representations based on dynamic range and precision requirements:

| Type | Storage Size | Precision Boundaries | Mathematical Semantics |
| :--- | :--- | :--- | :--- |
| **`INT64`** | 8 bytes | $[-2^{63}, 2^{63}-1]$ | Exact integer arithmetic |
| **`FLOAT64`** | 8 bytes | 53-bit mantissa ($\approx 15\text{--}17$ digits) | IEEE-754 double-precision floating point |
| **`NUMERIC`** | 16 bytes | 38 digits (29 integer, 9 fractional) | Exact decimal fixed-point (Scale $10^9$) |
| **`BIGNUMERIC`** | 32 bytes | 77 digits (39 integer, 38 fractional) | Exact decimal fixed-point (Scale $10^{38}$) |

When converting `NUMERIC` to `FLOAT64`, the engine preserves least-significant-bit rounding invariants to ensure IEEE-754 round-to-nearest-even tie-breaking never mistakes inexact quotients for exact halfway points.

### 9.4 Division Operators and Zero Divisor Protection
GoogleSQL differentiates between floating-point division and integer division:
- **Floating-Point Division (`/`):** The `/` operator always evaluates floating-point division returning `FLOAT64` (for example, `5 / 2` yields `2.5`).
- **Integer Division (`DIV`):** For integer division that truncates towards zero and returns an `INT64`, engineers must invoke `DIV(dividend, divisor)`. The expression `DIV(5, 2)` returns `2`.
- **Zero-Divisor Safety (`SAFE_DIVIDE`):** Dividing by zero via `/` or `DIV()` halts query execution with a runtime `division by zero` error. Use `SAFE_DIVIDE(x, y)` to return `NULL` cleanly when the divisor evaluates to zero or overflow occurs.

```sql
SELECT 5 / 2              AS float_div,
       DIV(5, 2)          AS int_div,
       SAFE_DIVIDE(10, 0) AS safe_div;
```

### 9.5 String Concatenation and Null Propagation in `CONCAT`
In GoogleSQL, `CONCAT(str1, str2, ...)` returns `NULL` if any argument evaluates to `NULL`. Concatenating nullable attributes (such as middle initials or secondary address lines) nullifies the entire resulting string. To preserve non-null fragments, wrap nullable columns in `IFNULL(col, '')` or use `FORMAT('%s%s', str1, IFNULL(str2, ''))`.

### 9.6 Temporal Functions, Timezones, and Boundary Crossings
Production queries in BigQuery execute in UTC by standard engineering policy (`CURRENT_DATE('UTC')`, `CURRENT_TIMESTAMP()`) unless explicitly documented in the query header that logic deliberately operates within a designated local civil timezone (such as `CURRENT_DATE('America/New_York')`).

- **Timezone Drift:** Omitting timezone parameters from `CURRENT_DATE()` defaults to UTC. Depending on the time of day, querying `CURRENT_DATE()` can evaluate to the subsequent calendar date relative to local civil business time.
- **Boundary Crossings in `DATE_DIFF`:** The `DATE_DIFF(later_date, earlier_date, date_part)` function counts the number of date part boundaries crossed between two dates, rather than elapsed time spans. For instance, `DATE_DIFF('2026-04-01', '2026-03-31', MONTH)` evaluates to `1` because a calendar month boundary was crossed, despite only twenty-four hours elapsing.
- **Daylight Saving Time Transitions:** Adding intervals via `TIMESTAMP_ADD(ts, INTERVAL 1 DAY)` increments absolute time by exactly 86,400 seconds. On days with Daylight Saving Time shifts (23 or 25 hours), timestamp arithmetic alters the wall-clock hour. In contrast, `DATETIME_ADD` increments civil calendar days while preserving wall-clock hours.

---

## 10. Data Manipulation Language (DML) and Transactions

GoogleSQL provides statements to modify rows and execute multi-statement ACID transactions. For the exhaustive specification covering `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE TABLE`, `MERGE` clause matrices, partition boundary pruning, snapshot read isolation, and Capacitor write mechanics, consult the [Data Manipulation Language (DML) and Transactions Reference](dml_and_transactions.md).

---

## 11. Related References and Operational Tooling

- **Pipe Syntax:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for linear relational pipeline operations.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for complete CREATE and ALTER statement matrices.
- **DML and Transactions:** Consult [DML and Transactions Guide](dml_and_transactions.md) for data mutation semantics.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for execution cost models.
- **Machine Learning:** Consult [BigQuery Machine Learning](bigquery_ml.md) for in-database model declarations.

Executable implementations of production DDL and DML patterns reside in [`ddl_and_dml_patterns.sql`](../examples/ddl_and_dml_patterns.sql).



