# BigQuery and GoogleSQL Anti-Patterns Catalog

This catalog documents common query anti-patterns observed in BigQuery and GoogleSQL codebases. It provides the architectural failure mechanism, slot resource impact, and corrected implementations for each pattern.

```sql
-- Anti-Pattern: Self-Join for Deduplication (High Slot MS, Heavy Shuffle)
SELECT o.*
  FROM `retail.orders` AS o
       INNER JOIN
       (
         SELECT customer_id, MAX(order_timestamp) AS max_ts
           FROM `retail.orders`
          GROUP BY customer_id
       ) AS latest
       ON  o.customer_id     = latest.customer_id
       AND o.order_timestamp = latest.max_ts
```

---

## 1. Unnecessary Full Column Projection (`SELECT *`)

### Mechanical Failure and Risk Boundaries
Capacitor stores table columns in isolated physical chunks on Colossus. Declaring `SELECT *` forces worker slots to request, transfer, and decode every column in the schema, bypassing columnar projection pruning.

- **Persistent Tables:** Scanning unneeded columns inflates memory bandwidth and increases scan costs.
- **External Tables (Strictly Prohibited):** Using `SELECT *` on external tables (BigLake, object tables, Cloud Storage formats, Google Drive, Sheets) introduces severe operational failure risks. External schemas evolve without database control; upstream producers can append wide columns or alter layouts, unexpectedly multiplying scan volume by orders of magnitude or breaking downstream contracts.

### Conditioned Exceptions (When `SELECT *` Is Permissible)
Wildcard projection is valid when conditioned on certainty of correctness:
1. **Verifiably Complete Consumption:** When downstream computations or destination pipelines genuinely require all schema columns.
2. **Localized Intermediate Representations (CTEs and Temp Tables):** Projecting `SELECT *` from localized structures (such as `CREATE TEMP TABLE` or CTEs) is completely permissible because the author explicitly defines, bounds, and isolates the projected schema.

```sql
-- Anti-Pattern 1: Unnecessary column scan on wide persistent table (85 columns read)
SELECT *
  FROM `telemetry.raw_events`
 WHERE event_date = CURRENT_DATE();

-- Anti-Pattern 2: Wildcard scan on external table with uncontrolled schema drift
SELECT *
  FROM `external_lake.partner_events_csv`;

-- Compliant Form 1: Explicit column projection on persistent storage
SELECT event_id, user_id, event_timestamp
  FROM `telemetry.raw_events`
 WHERE event_date = CURRENT_DATE();

-- Compliant Form 2: Localized projection from an author-controlled CTE
WITH filtered_events AS (
  SELECT event_id, user_id, event_timestamp
    FROM `telemetry.raw_events`
   WHERE event_date = CURRENT_DATE()
)
SELECT *
  FROM filtered_events;
```

---

## 2. Function-Wrapped Partition Filtering

### Mechanical Failure
Wrapping a partition column inside a scalar function prevents the logical optimizer from resolving static pruning constraints when compiling queries. The query coordinator fails to prune unselected partition directories, initiating a full table scan. Pruning fails completely.

```sql
-- Non-Compliant Form (Evaluates function on every row; scans entire table)
SELECT COUNT(*)
  FROM `analytics.user_actions`
 WHERE EXTRACT(YEAR FROM event_timestamp) = 2026
   AND EXTRACT(MONTH FROM event_timestamp) = 3;

-- Corrected Form (Static bounds enable compilation-time partition pruning)
SELECT COUNT(*)
  FROM `analytics.user_actions`
 WHERE event_timestamp >= '2026-03-01 00:00:00 UTC'
   AND event_timestamp < '2026-04-01 00:00:00 UTC';
```

---

## 3. Self-Joins for Record Deduplication

### Mechanical Failure
Joining a table with an aggregated subquery of itself requires two full scans of the base relation. Both scans redistribute rows across the network shuffle tier, multiplying total slot compute time. Avoid self-joins.

```sql
-- Non-Compliant Form (Two table scans plus distributed hash join)
SELECT o.order_id, o.customer_id, o.order_amount
  FROM `retail.orders` AS o
       INNER JOIN
       (
         SELECT customer_id, MAX(order_timestamp) AS latest_time
           FROM `retail.orders`
          GROUP BY customer_id
       ) AS m
       ON  o.customer_id     = m.customer_id
       AND o.order_timestamp = m.latest_time;

-- Corrected Form (Single table scan with in-memory window filter)
 SELECT order_id, customer_id, order_amount
   FROM `retail.orders`
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY customer_id
              ORDER BY order_timestamp DESC
        ) = 1;
```

---

## 4. Unpinned Multiple CTE Re-Evaluation

### Mechanical Failure
By default, Common Table Expressions act as inline syntactic macros. When a query references a complex CTE in multiple join branches, BigQuery may re-evaluate the CTE pipeline repeatedly, multiplying compute slots and shuffle memory pressure. Pin shared CTEs.

```sql
-- Non-Compliant Form (May evaluate DailyTotals twice across separate joins)
WITH
  DailyTotals AS (
    SELECT customer_id, SUM(amount) AS total_spent
      FROM `finance.transactions`
     WHERE transaction_date = CURRENT_DATE()
     GROUP BY customer_id
  )
SELECT a.customer_id, a.total_spent, b.credit_limit
  FROM DailyTotals AS a
       LEFT JOIN
       `finance.limits` AS b
       ON a.customer_id = b.customer_id
 UNION ALL
SELECT c.customer_id, c.total_spent, 0
  FROM DailyTotals AS c
 WHERE c.total_spent > 5000.00;

-- Corrected Form (Materializes intermediate state into a temporary table)
CREATE TEMP TABLE DailyTotals
AS (
  SELECT customer_id, SUM(amount) AS total_spent
    FROM `finance.transactions`
   WHERE transaction_date = CURRENT_DATE()
   GROUP BY customer_id
);

SELECT a.customer_id, a.total_spent, b.credit_limit
  FROM DailyTotals AS a
       LEFT JOIN
       `finance.limits` AS b
       ON a.customer_id = b.customer_id
 UNION ALL
SELECT c.customer_id, c.total_spent, 0
  FROM DailyTotals AS c
 WHERE c.total_spent > 5000.00;
```

---

## 5. Unfiltered Cross Joins and Cartesian Expansion

### Mechanical Failure
Omitting join conditions generates the Cartesian product ($M \times N$) of input relations. This intermediate volume exhausts worker RAM buffers, forcing gigabytes of shuffle spill to persistent storage. Spills kill throughput.

```sql
-- Non-Compliant Form (Emits billions of synthetic tuples into shuffle)
SELECT o.order_id, p.promotion_code
  FROM `retail.orders` AS o
       CROSS JOIN
       `retail.promotions` AS p
 WHERE o.order_amount >= p.min_order_value;

-- Corrected Form (Translates condition into an explicit theta join)
SELECT o.order_id, p.promotion_code
  FROM `retail.orders` AS o
       INNER JOIN
       `retail.promotions` AS p
       ON o.order_amount >= p.min_order_value;
```

---

## 6. Shuffling Raw `NUMERIC` Instead of Converting Late

### Mechanical Failure
As documented in the GoogleSQL engine analysis, `NUMERIC` occupies 16 bytes and executes through scalar ALU carry chains. Shuffling raw `NUMERIC` columns doubles network bandwidth compared to 8-byte `FLOAT64` values. Cast early.

```sql
-- Non-Compliant Form (Shuffles 16-byte NUMERIC values across 100M keys)
SELECT account_id,
       CAST(SUM(transaction_numeric) AS FLOAT64) AS total_float
  FROM `finance.ledger`
 GROUP BY account_id;

-- Corrected Form (Converts to FLOAT64 before shuffle when approximate precision suffices)
SELECT account_id,
       SUM(
         CAST(transaction_numeric AS FLOAT64)
       ) AS total_float
  FROM `finance.ledger`
 GROUP BY account_id;
```
*(Note: Maintain raw `NUMERIC` arithmetic throughout when financial currency precision mandates zero decimal rounding drift).*

---

## 7. Projecting Unrounded `FLOAT64` Calculations in Output Tables

### Mechanical Failure
Arithmetic over `FLOAT64` expressions produces IEEE 754 representation artifacts with noisy trailing decimal fractions. Exposing raw, unrounded transformed floats in resulting tables or views clutters downstream consumption and implies false precision. Restrict output precision by wrapping transformed expressions in `ROUND()` calibrated to domain context.

```sql
-- Non-Compliant Form (Emits unrounded IEEE 754 floating-point noise)
CREATE OR REPLACE TABLE `analytics.daily_order_metrics`
AS (
  SELECT customer_id,
         AVG(order_amount)                                     AS avg_order_amount,
         SUM(order_amount * discount_rate) / SUM(order_amount) AS effective_discount_rate
    FROM `retail.orders`
   GROUP BY customer_id
);

-- Corrected Form (Rounds output fields to sensible domain precision)
CREATE OR REPLACE TABLE `analytics.daily_order_metrics`
AS (
  SELECT customer_id,
         ROUND(AVG(order_amount), 2)                                     AS avg_order_amount,
         ROUND(SUM(order_amount * discount_rate) / SUM(order_amount), 4) AS effective_discount_rate
    FROM `retail.orders`
   GROUP BY customer_id
);
```
