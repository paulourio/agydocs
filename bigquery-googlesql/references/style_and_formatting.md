# GoogleSQL Style Guidelines and Formatter Specification

This document provides a technical specification of the GoogleSQL code style conventions enforced by the `gsql` formatter (`bqfmt`). It details lexical casing invariants, indentation rules, Common Table Expression alignment, pipe syntax formatting, modeline directives, configuration schema, and parser compatibility boundaries.

```sql
WITH
  high_value_orders AS (
    SELECT customer_id, SUM(order_amount) AS total_spend
      FROM `enterprise.sales.orders`
     WHERE order_status = 'COMPLETED'
       AND transaction_date >= '2026-01-01'
     GROUP BY customer_id
    HAVING total_spend > 1000.00
  )
SELECT c.customer_id, c.customer_name, h.total_spend
  FROM high_value_orders AS h
       INNER JOIN
       `enterprise.sales.customers` AS c
       ON h.customer_id = c.customer_id
 ORDER BY h.total_spend DESC
```

---

## 1. Lexical Casing Invariants

The `bqfmt` tool enforces explicit casing rules across SQL tokens.

| Element Category | Casing Rule | Canonical Example | Prohibited Non-Compliant Form |
| :--- | :--- | :--- | :--- |
| **SQL Keywords** | `UPPER_CASE` | `SELECT`, `FROM`, `WHERE`, `JOIN` | `select`, `From`, `where` |
| **Built-in Types** | `UPPER_CASE` | `INT64`, `NUMERIC`, `STRING`, `BOOL` | `int64`, `numeric`, `String` |
| **Built-in Functions** | `UPPER_CASE` | `SUM()`, `COUNT()`, `COALESCE()` | `sum()`, `count()`, `Coalesce()` |
| **Boolean & Null Literals** | `UPPER_CASE` | `TRUE`, `FALSE`, `NULL` | `true`, `false`, `null` |
| **Column Identifiers** | `LOWER_CASE` | `customer_id`, `event_timestamp` | `CustomerID`, `Customer_Id` |
| **Table Aliases** | `LOWER_CASE` | `AS o`, `AS cust`, `AS raw_events` | `AS O`, `AS Cust` |
| **Table Names** | `AS_IS` | `project-id.dataset.table_name` | Altering existing project or dataset case |
| **Pseudo-Columns** | `UPPER_CASE` | `_PARTITIONDATE`, `_PARTITIONTIME` | `_partitiondate`, `_table_suffix` |
| **String Literals** | Single Quotes | `'COMPLETED'`, `'US'` | `"COMPLETED"`, `"US"` |

---

## 2. Layout, Indentation, and Alignment Rules

Formatting rules preserve visual clarity while avoiding noisy Git diff churn across engineering repositories. Uniform formatting accelerates peer reviews.

### 2.1 Clause Alignment Gutter
The formatter aligns primary SQL clauses along a right-aligned keyword gutter so that query arguments start uniformly at column 8 (1-indexed). The `SELECT` clause sits flush at column 1 (0 leading spaces), while the `FROM` keyword indents by two spaces to place its final character at column 6. The `WHERE`, `LIMIT`, `GROUP BY`, and `ORDER BY` keywords indent by a single leading space, whereas `HAVING` and `QUALIFY` sit flush at column 1. Logical conjunctions (`AND`, `OR`) indent by three and four spaces respectively to place their final character at column 6. This layout aligns condition expressions at column 8.

| Clause Keyword | Leading Spaces | Keyword Character Span (1-Indexed) | Trailing Whitespace | Argument Start Column (1-Indexed) |
| :--- | :--- | :--- | :--- | :--- |
| `SELECT` | 0 | 1–6 | 1 space | Column 8 |
| `FROM` | 2 | 3–6 | 1 space | Column 8 |
| `WHERE` | 1 | 2–6 | 1 space | Column 8 |
| `HAVING` | 0 | 1–6 | 1 space | Column 8 |
| `AND` | 3 | 4–6 | 1 space | Column 8 |
| `OR` | 4 | 5–6 | 1 space | Column 8 |
| `LIMIT` | 1 | 2–6 | 1 space | Column 8 |
| `QUALIFY` | 0 | 1–7 | 1 space | Column 9 |
| `GROUP BY` | 1 | 2–9 | 1 space | Column 11 |
| `ORDER BY` | 1 | 2–9 | 1 space | Column 11 |

```sql
SELECT order_id, customer_id, total_amount
  FROM `retail.orders`
 WHERE total_amount > 50.00
   AND order_status = 'COMPLETED'
```

Under mixed `OR` disjunctions, `bqfmt` aligns condition expressions at column 12:

```sql
SELECT order_id, customer_id, total_amount
  FROM `retail.orders`
 WHERE     total_amount > 50.00
       AND order_status = 'COMPLETED'
    OR is_priority_customer = TRUE
```

For multi-line column projections exceeding four attributes, the first column identifier follows `SELECT `, and each subsequent attribute indents by seven spaces to start at column 8:

```sql
SELECT order_id,
       customer_id,
       order_amount,
       order_status
  FROM `retail.orders`
 WHERE total_amount > 50.00
   AND order_status = 'COMPLETED'
```

### 2.2 Join Clause Structuring
Multi-line join expressions indent under the primary `FROM` relation to preserve parent-child hierarchy. The join operator indents by seven spaces, placing its text in line with the target table name declared in the preceding clause (column 8). The joined relation appears on the subsequent line with identical seven-space indentation, followed by the `ON` predicate starting on the next line with seven-space indentation.

```sql
SELECT o.order_id, c.customer_name
  FROM `retail.orders` AS o
       INNER JOIN
       `retail.customers` AS c
       ON o.customer_id = c.customer_id
```

### 2.3 Conditional Expression Formatting
The `indent_case_when = true` setting indents conditional branches inside `CASE` expressions. The `CASE` keyword occupies its own line or follows an existing projection comma. Each subsequent `WHEN ... THEN` condition indents by two spaces relative to `CASE`. The `ELSE` token indents to align beneath the `THEN` result column, and the concluding `END` token aligns flush with the opening `CASE`.

```sql
SELECT order_id,
       CASE
         WHEN total_amount >= 1000.00 THEN 'TIER_1'
         WHEN total_amount >= 500.00  THEN 'TIER_2'
                                      ELSE 'STANDARD'
       END AS customer_tier
  FROM `retail.orders`
```

### 2.4 Single-Line Projection Limit
The formatter preserves short projections on a single line when the column count does not exceed four items and total width stays below 120 characters. Compact projections save vertical space. Projections exceeding four columns break across lines with vertical column alias alignment.

### 2.5 Agent Code Generation Style Card and Quality Checklist
Verify each requirement in this checklist before emitting GoogleSQL queries, views, or DDL statements:

1. **Intermediate Materialization Standard:**
   - To materialize intermediate result sets across multiple consumer branches, execute `CREATE TEMP TABLE my_table AS SELECT ...`.
2. **Lexical Casing:**
   - Statement and clause keywords (`SELECT`, `FROM`, `WHERE`) must remain uppercase.
   - Built-in data types (`INT64`, `FLOAT64`, `STRING`, `DATE`) must remain uppercase.
   - Built-in scalar functions (`COUNT`, `ROUND`, `APPROX_QUANTILES`) must remain uppercase.
   - Boolean and NULL literals (`TRUE`, `FALSE`, `NULL`) must remain uppercase.
   - String literals must use single quotes (`'string'`). Double quotes remain prohibited.
3. **Clause Alignment Gutter:**
   - Align primary clauses using canonical gutters: position `SELECT` at column 1, `FROM` at column 3, and `WHERE` at column 2.
   - Indent subsequent attributes in multi-line `SELECT` projections by seven spaces to start at column 8.
4. **Multi-Line Join Geometry:**
   - Indent multi-line joins by seven spaces under `FROM`. Place `INNER JOIN` on the first line, the joined relation on the second line, and `ON` on the third line.
5. **CASE Alignment:**
   - Place each `WHEN condition THEN result` expression on a single line. Align `ELSE` directly under the `THEN` result column. Position `END` flush with the governing `CASE` token.
6. **Transformed Float Rounding:**
   - Wrap computed `FLOAT64` projections in `ROUND(expr, N)` (for example, `ROUND(psi_val, 4)` for statistical indices).
7. **Architectural Naming and Class Words:**
   - Format dataset identifiers as `<domain>_<subdomain>_<layer>` (for example, `risk_monitoring_08_met`).
   - Format table identifiers as `<entity>_<context>_<suffix>` (layers 01-04) or `<product>_<context>_<suffix>` (layers 05-08) with approved suffixes (`_met`, `_dim`, `_fact`, `_pred`, `_feat`).
   - Terminate column identifiers with approved ISO 11179 class words (`_id`, `_bk`, `_nm`, `_dt`, `_ts`, `_amt`, `_qty`, `_val`, `_rt`, `_p`, `_ind`, `_cd`).

---

## 3. Formatting Common Table Expressions (CTEs)

Common Table Expressions must remain readable across complex multi-branch analytical pipelines. The `WITH` keyword occupies its own line, each CTE identifier indents by two spaces, and inner queries indent by two additional spaces. The closing parenthesis aligns with the CTE identifier margin, and commas trail each closing parenthesis when declaring multiple CTEs.

```sql
WITH
  monthly_revenue AS (
    SELECT customer_id, SUM(amount) AS revenue
      FROM `finance.invoices`
     WHERE invoice_date >= '2026-01-01'
     GROUP BY customer_id
  ),
  customer_tiers AS (
    SELECT customer_id, tier_name
      FROM `crm.customers`
     WHERE is_active = TRUE
  )
SELECT m.customer_id, c.tier_name, m.revenue
  FROM monthly_revenue AS m
       INNER JOIN
       customer_tiers AS c
       ON m.customer_id = c.customer_id
```

---

## 4. Formatting Pipe Query Syntax (`|>`)

Pipe syntax constructs linear data pipelines without nested wrapper subqueries. Each pipe operator starts on a new line with the symbol `|> ` flush against the left margin. Operator keywords render in uppercase, and multi-column extensions indent subsequent expressions to align with the initial assignment. Within aggregate operators, aggregate expressions indent by five spaces with vertical alias alignment, while suffix grouping clauses indent by three spaces.

```sql
FROM `enterprise.telemetry.events`
|> WHERE event_timestamp >= '2026-03-01'
|> EXTEND JSON_VALUE(payload, '$.user_id') AS parsed_user_id,
          JSON_VALUE(payload, '$.action')  AS action_type
|> WHERE action_type IN ('PURCHASE', 'CHECKOUT')
|> AGGREGATE
     COUNT(*)                       AS total_events,
     COUNT(DISTINCT parsed_user_id) AS unique_users
   GROUP AND ORDER BY action_type ASC
```

---

## 5. Formatting Chained Function Calls

GoogleSQL supports chained function calls using dot notation (`.`), evaluating scalar transformations from left to right. Formatting rules keep chained expressions readable without overflowing column limits.

### 5.1 Inline Chaining for Short Expressions
When a chained expression contains three or fewer function calls and fits within the 120-character line boundary, format the entire chain on a single line. The initial identifier or expression must sit inside parentheses.

```sql
SELECT customer_id, (customer_name).TRIM().UPPER() AS normalized_name
  FROM `retail.customers`
```

### 5.2 Deep Transformations
When combining multiple transformations, chain scalar methods consecutively without nested wrappers:

```sql
SELECT order_id, (raw_payload).JSON_EXTRACT_SCALAR('$.user.email').TRIM().LOWER() AS sanitized_email
  FROM `telemetry.ingest_logs`
```

---

## 6. Query Writing Style: Transformed FLOAT64 Precision Discipline

Calculations over `FLOAT64` data types (such as division, averages, ratios, percentages, discounts, exponential smoothing, or logarithmic scaling) introduce IEEE 754 binary floating-point representation artifacts. Persisting unrounded transformed fields into destination tables creates noisy outputs and conveys false precision.

### 6.1 Mandatory Rounding on Resulting Tables
Whenever a query computes, aggregates, or transforms `FLOAT64` values, and the resulting table or view schema exposes this field, engineers must explicitly wrap the transformed expression in `ROUND()`.

```sql
-- Non-Compliant Form: Exposes IEEE 754 precision artifacts (e.g. 14.200000000000003)
CREATE OR REPLACE TABLE `finance.monthly_account_summary`
AS (
  SELECT account_id,
         AVG(balance)                     AS average_balance,
         SUM(fee_amount) / SUM(tx_amount) AS fee_ratio
    FROM `finance.daily_ledger`
   GROUP BY account_id
);

-- Corrected Form: Enforces explicit, context-driven output precision
CREATE OR REPLACE TABLE `finance.monthly_account_summary`
AS (
  SELECT account_id,
         ROUND(AVG(balance), 2)                     AS average_balance,
         ROUND(SUM(fee_amount) / SUM(tx_amount), 4) AS fee_ratio
    FROM `finance.daily_ledger`
   GROUP BY account_id
);
```

### 6.2 Context-Driven Sensible Precision
Sensible precision depends on the semantic domain of the data. Engineers must balance informativeness against visual and analytical noise. Avoid exaggerating precision beyond what the underlying data warrants:

- **Monetary and Currency Metrics:** Round to 2 decimal places (such as `ROUND(revenue, 2)`).
- **Percentages and Conversion Rates:** Round to 2 decimal places when expressed as percentages (such as `ROUND(rate * 100.0, 2)`), or to 4 decimal places when stored as fractional ratios (such as `0.1425`).
- **Performance Latencies and Sensor Telemetry:** Round to 1 or 2 decimal places (such as `ROUND(latency_ms, 1)`). Millisecond metrics rarely justify microsecond fractions.
- **Normalized Scores, Weights, and Statistical Indices:** Round to 3 or 4 decimal places. Extra digits beyond 4 decimal places usually represent floating-point noise rather than measurable variance.

Excessive precision increases cognitive overhead during data consumption without adding informational value. Calibrate the rounding parameter strictly to user and downstream system requirements.

### 6.3 Intermediate Calculations vs. Output Projections
The rounding rule applies to the final projected fields of tables and views. Intermediate expressions inside Common Table Expressions (CTEs) or subqueries should preserve raw `FLOAT64` precision to avoid accumulating rounding errors during intermediate arithmetic stages. Apply `ROUND()` at the terminal projection boundary that defines the resulting table.

---

## 7. Formatter Settings: `.bqfmt.toml`

The `bqfmt` tool resolves options by walking upward from the source file directory looking for `.bqfmt.toml`. The configuration requires a top-level `default_style` attribute pointing to a declared style block. A complete configuration template is provided in [`dot_bqfmt.toml`](../examples/dot_bqfmt.toml).

```toml
default_style = "default"

[[styles]]
name = "default"

[styles.options]
soft_max_cols = 120
newline_before_clause = true
align_logical_with_clauses = true
align_trailing_comments = true
column_list_trailing_comma = "AUTO"
indentation = 2
indent_case_when = true
indent_with_clause = true
indent_with_entries = true
min_joins_to_separate_in_blocks = 2
max_cols_for_single_line_select = 4
max_params_for_single_line_function = 1
function_catalog = "BIGQUERY"
function_name_style = "AS_IS"
builtin_function_name_style = "UPPER_CASE"
identifier_style = "LOWER_CASE"
keyword_style = "UPPER_CASE"
type_style = "UPPER_CASE"
bool_style = "UPPER_CASE"
null_style = "UPPER_CASE"
hex_style = "LOWER_CASE"
numeric_style = "LOWER_CASE"
pseudo_column_style = "UPPER_CASE"
table_name_style = "AS_IS"
string_style = "PREFER_SINGLE_QUOTE"
bytes_style = "PREFER_SINGLE_QUOTE"
```

### 7.1 Inline Modeline Directives
Files can override directory-level configuration using modeline comments placed at the top of the file.

```sql
-- bqfmt: indentation=4,soft_max_cols=100
SELECT col1, col2
  FROM `dataset.table`
```

To instruct `bqfmt` to bypass a specific file, declare the skip modeline.

```sql
-- bqfmt: skip
SELECT col1, col2
  FROM `dataset.table`
```

---

## 8. Formatter Parser Constraints

Engineers must account for `bqfmt` parsing constraints when applying automated formatting.

- **CTE Grammar Invariant:** In GoogleSQL syntax, Common Table Expression blocks require an opening parenthesis immediately following the `AS` token (`WITH cte AS (...)`).
- **Search and Vector Index DDL:** BigQuery supports `CREATE SEARCH INDEX` and `CREATE VECTOR INDEX` statements. Because `bqfmt` does not parse these specialized DDL commands, teams manage index definitions through the `bq` CLI or Terraform configurations.
- **Grammar Clause Ordering:** In GoogleSQL grammar, the `QUALIFY` clause must strictly precede the `WINDOW` clause. Placing `WINDOW` before `QUALIFY` causes `bqfmt` to abort with a syntax error.
- **Complete Statement Parsing:** The formatter evaluates code using `ParseScript`. Formatting isolated clause fragments produces a syntax error, requiring all test snippets to exist within complete query blocks.
- **Mandatory Default Style:** Omitting `default_style` from `.bqfmt.toml` causes the formatter to abort with a fatal validation error. Every configuration file must define `default_style = "default"`.

---

## 9. CLI Execution

Execute `bqfmt` to inspect or reformat SQL scripts across local development environments.

```bash
# Format a single SQL file and output to stdout
bqfmt query.sql

# Format all SQL files in-place recursively across a directory
bqfmt -w ./queries/

# Verify formatting inside continuous integration pipelines
bqfmt ./queries/
```

---

## 10. Related References and Operational Tooling

- **Language Syntax:** Consult [Language and Syntax Reference](language_and_syntax.md) for clause ordering grammar.
- **Pipe Syntax:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for linear pipeline conventions.
- **Workflows:** Consult [Engineering Workflows](engineering_workflows.md) for CI formatting gates.
- **Cheat Sheet:** Consult [Engineering Cheat Sheet](../resources/cheat_sheet.md) for quick syntax mapping.
