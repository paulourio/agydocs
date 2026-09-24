-- ============================================================================
-- GOOGLESQL MULTI-LEVEL AGGREGATION PATTERNS
-- ============================================================================
-- Demonstrates multi-level aggregation using the inner GROUP BY modifier within
-- aggregate function calls. Includes canonical queries from official GoogleSQL
-- documentation as well as production patterns for risk, retail, and telemetry.
-- ============================================================================
-- ----------------------------------------------------------------------------
-- 1. OFFICIAL DOCUMENTATION CANONICAL EXAMPLES
-- ----------------------------------------------------------------------------
-- Example 1.1: Canonical Multi-Level Aggregation (Average Daily Sales)
-- Computes the average of daily sales sums per product in a single SELECT step.
WITH
  Sales AS (
    SELECT 'Apples'                        AS product,
           100                             AS revenue,
           TIMESTAMP '2026-01-01 10:00:00' AS time
     UNION ALL
    SELECT 'Apples', 150, TIMESTAMP '2026-01-01 12:00:00'
     UNION ALL
    SELECT 'Apples', 200, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 50, TIMESTAMP '2026-01-01 10:00:00'
     UNION ALL
    SELECT 'Oranges', 60, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 70, TIMESTAMP '2026-01-02 12:00:00'
  )
SELECT product, ROUND(AVG(SUM(revenue)), 2) AS avg_daily_sales_amt
  FROM Sales
 GROUP BY product
 ORDER BY product;

-- Example 1.2: Classic Subquery Equivalent of Example 1.1
-- Demonstrates the two-stage aggregation pattern replaced by multi-level syntax.
WITH
  Sales AS (
    SELECT 'Apples'                        AS product,
           100                             AS revenue,
           TIMESTAMP '2026-01-01 10:00:00' AS time
     UNION ALL
    SELECT 'Apples', 150, TIMESTAMP '2026-01-01 12:00:00'
     UNION ALL
    SELECT 'Apples', 200, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 50, TIMESTAMP '2026-01-01 10:00:00'
     UNION ALL
    SELECT 'Oranges', 60, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 70, TIMESTAMP '2026-01-02 12:00:00'
  )
SELECT product, ROUND(AVG(daily_sales_amt), 2) AS avg_daily_sales_amt
  FROM (
         SELECT product, SUM(revenue) AS daily_sales_amt
           FROM Sales
          GROUP BY product,
                   DATE(time)
       )
 GROUP BY product
 ORDER BY product;

-- Example 1.3: Avoiding Overcounting in One-to-Many Joins
-- Parent salary duplicated across child records is evaluated exactly once per employee.
WITH
  Employees AS (
    SELECT 101       AS empno,
           'Alice'   AS name,
           120000.00 AS salary
     UNION ALL
    SELECT 102, 'Bob', 95000.00
     UNION ALL
    SELECT 103, 'Carol', 110000.00
  ),
  Dependents AS (
    SELECT 101     AS empno,
           'Child' AS relationship
     UNION ALL
    SELECT 101, 'Child'
     UNION ALL
    SELECT 102, 'Spouse'
     UNION ALL
    SELECT 102, 'Child'
     UNION ALL
    SELECT 103, 'Child'
  )
SELECT ROUND(AVG(ANY_VALUE(e.salary)), 2) AS avg_salary_amt
  FROM Employees AS e
       INNER JOIN
       Dependents AS d
       USING (empno)
 WHERE d.relationship = 'Child';

-- Example 1.4: Classic Subquery Equivalent of Example 1.3
-- Collapses duplicated salary rows in a subquery before the outer average.
WITH
  Employees AS (
    SELECT 101       AS empno,
           'Alice'   AS name,
           120000.00 AS salary
     UNION ALL
    SELECT 102, 'Bob', 95000.00
     UNION ALL
    SELECT 103, 'Carol', 110000.00
  ),
  Dependents AS (
    SELECT 101     AS empno,
           'Child' AS relationship
     UNION ALL
    SELECT 101, 'Child'
     UNION ALL
    SELECT 102, 'Spouse'
     UNION ALL
    SELECT 102, 'Child'
     UNION ALL
    SELECT 103, 'Child'
  )
SELECT ROUND(AVG(salary_per_emp_amt), 2) AS avg_salary_amt
  FROM (
         SELECT ANY_VALUE(e.salary) AS salary_per_emp_amt
           FROM Employees AS e
                INNER JOIN
                Dependents AS d
                USING (empno)
          WHERE d.relationship = 'Child'
          GROUP BY e.empno
       );

-- Example 1.5: Filtering Intermediate Groups with Inner HAVING
-- The inner HAVING clause prunes daily totals below 120 before computing product average.
WITH
  Sales AS (
    SELECT 'Apples'                        AS product,
           100                             AS revenue,
           TIMESTAMP '2026-01-01 10:00:00' AS time
     UNION ALL
    SELECT 'Apples', 150, TIMESTAMP '2026-01-01 12:00:00'
     UNION ALL
    SELECT 'Apples', 200, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 50, TIMESTAMP '2026-01-01 10:00:00'
     UNION ALL
    SELECT 'Oranges', 60, TIMESTAMP '2026-01-02 10:00:00'
     UNION ALL
    SELECT 'Oranges', 70, TIMESTAMP '2026-01-02 12:00:00'
  )
SELECT product, ROUND(AVG(SUM(revenue)), 2) AS avg_qualifying_daily_sales_amt
  FROM Sales
 GROUP BY product
 ORDER BY product;

-- ----------------------------------------------------------------------------
-- 2. PRODUCTION-GRADE ADVANCED ANALYTICAL PATTERNS
-- ----------------------------------------------------------------------------
-- Pattern 2.1: Retail Basket Depth (Average Distinct Categories per Session)
-- Evaluates the diversity of category browsing per session across acquisition channels.
SELECT acquisition_channel_cd,
       COUNT(DISTINCT session_id)                 AS session_tot_qty,
       ROUND(AVG(COUNT(DISTINCT category_id)), 2) AS category_avg_qty,
       ROUND(MAX(COUNT(DISTINCT category_id)), 0) AS category_max_qty
  FROM `enterprise.retail_traffic_04_anl.web_event_fact`
 WHERE event_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
 GROUP BY acquisition_channel_cd;

-- Pattern 2.2: Financial Velocity & Surge Spike Detection
-- Calculates peak hourly transaction volume and compares against the daily mean.
SELECT merchant_id,
       merchant_category_cd,
       ROUND(MAX(SUM(transaction_amt)), 2)                                         AS peak_hourly_vol_amt,
       ROUND(AVG(SUM(transaction_amt)), 2)                                         AS avg_hourly_vol_amt,
       ROUND(SAFE_DIVIDE(MAX(SUM(transaction_amt)), AVG(SUM(transaction_amt))), 2) AS surge_rt
  FROM `enterprise.fin_card_04_anl.card_transaction_fact`
 WHERE transaction_dt = CURRENT_DATE()
 GROUP BY merchant_id, merchant_category_cd
HAVING surge_rt >= 3.0;

-- Pattern 2.3: Telemetry SLA Monitoring (P95 Hourly Ingestion Peak)
-- Computes the 95th percentile of hourly event ingest across distinct microservices.
SELECT service_nm,
       deployment_environment_cd,
       APPROX_QUANTILES(SUM(event_qty))[OFFSET(95)] AS p95_hourly_event_qty
  FROM `enterprise.telem_service_08_met.service_metric_met`
 WHERE metric_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
 GROUP BY service_nm, deployment_environment_cd;

-- Pattern 2.4: Multi-Level Aggregation in Pipe Query Syntax (|>)
-- Composes multi-level reduction linearly within the |> AGGREGATE operator.
FROM `enterprise.retail_sales_04_anl.order_fact`
|> WHERE order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
   AND   order_status_cd = 'COMPLETED'
|> AGGREGATE
     ROUND(AVG(SUM(order_amt)), 2) AS avg_daily_revenue_amt,
     ROUND(MAX(SUM(order_amt)), 2) AS max_daily_revenue_amt,
     COUNT(DISTINCT customer_id)   AS customer_tot_qty
   GROUP BY region_cd
|> WHERE avg_daily_revenue_amt >= 5000.00
|> ORDER BY avg_daily_revenue_amt DESC;
