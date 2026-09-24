-- ============================================================================
-- CLASSIC GOOGLESQL IMPLEMENTATION
-- ============================================================================
-- Business Goal:
-- Filter completed orders within the last 90 days, join customer details,
-- compute regional customer rankings, aggregate monthly totals,
-- and retain high-volume regions.
-- Conforms strictly to ISO 11179 column suffixes and 8-column gutter alignment.
-- ============================================================================
WITH
  filtered_orders AS (
    SELECT o.order_id,
           o.customer_id,
           o.order_amt,
           o.order_dt,
           FORMAT_DATE('%Y-%m', o.order_dt) AS order_month_cd
      FROM `enterprise.retail_sales_04_anl.order_fact` AS o
     WHERE o.order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
       AND o.order_status_cd = 'COMPLETED'
  ),
  joined_customers AS (
    SELECT f.order_id,
           f.customer_id,
           c.customer_nm,
           c.region_cd,
           f.order_amt,
           f.order_month_cd
      FROM filtered_orders AS f
           INNER JOIN
           `enterprise.retail_sales_04_anl.customer_dim` AS c
           ON f.customer_id = c.customer_id
  ),
  ranked_orders AS (
    SELECT j.*,
           ROW_NUMBER() OVER (
             PARTITION BY j.region_cd, j.order_month_cd
                 ORDER BY j.order_amt DESC
           ) AS regional_rank_qty
      FROM joined_customers AS j
  ),
  top_orders AS (
    SELECT r.customer_id,
           r.customer_nm,
           r.region_cd,
           r.order_month_cd,
           r.order_amt
      FROM ranked_orders AS r
     WHERE r.regional_rank_qty <= 10
  )
SELECT t.region_cd,
       t.order_month_cd,
       COUNT(DISTINCT t.customer_id) AS customer_qty,
       SUM(t.order_amt)              AS revenue_tot_amt
  FROM top_orders AS t
 GROUP BY t.region_cd, t.order_month_cd
HAVING revenue_tot_amt > 25000.00
 ORDER BY t.order_month_cd DESC, revenue_tot_amt DESC;

-- ============================================================================
-- GOOGLESQL PIPE SYNTAX EQUIVALENT (|>)
-- ============================================================================
-- Identical execution semantics expressed as a linear relational pipeline.
-- Eliminates four separate CTE definitions and inverts nested expressions.
-- ============================================================================
FROM `enterprise.retail_sales_04_anl.order_fact` AS o
|> WHERE o.order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
   AND   o.order_status_cd = 'COMPLETED'
|> INNER JOIN
   `enterprise.retail_sales_04_anl.customer_dim` AS c
   ON o.customer_id = c.customer_id
|> EXTEND FORMAT_DATE('%Y-%m', o.order_dt) AS order_month_cd,
          ROW_NUMBER() OVER (
            PARTITION BY c.region_cd, FORMAT_DATE('%Y-%m', o.order_dt)
                ORDER BY o.order_amt DESC
          ) AS regional_rank_qty
|> WHERE regional_rank_qty <= 10
|> AGGREGATE
     COUNT(DISTINCT o.customer_id) AS customer_qty,
     SUM(o.order_amt)              AS revenue_tot_amt
   GROUP BY c.region_cd, order_month_cd
|> WHERE revenue_tot_amt > 25000.00
|> ORDER BY order_month_cd DESC, revenue_tot_amt DESC;
