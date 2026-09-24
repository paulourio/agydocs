-- ============================================================================
-- HIGH-PERFORMANCE GOOGLESQL PATTERNS
-- ============================================================================
-- Demonstrates partition pruning, cluster key ordering, broadcast join
-- structuring, in-memory deduplication with QUALIFY, and explicit CTE
-- materialization control.
-- Conforms strictly to ISO 11179 column suffixes and 8-column gutter alignment.
-- ============================================================================
-- Pattern 1: In-Memory Deduplication via QUALIFY (Replaces Self-Join)
-- Scans base table once; eliminates 2x Colossus read and shuffle hash join.
 SELECT transaction_id, account_id, transaction_amt, transaction_ts
   FROM `enterprise.fin_ledger_04_anl.transaction_fact`
  WHERE transaction_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
QUALIFY ROW_NUMBER() OVER (
          PARTITION BY account_id
              ORDER BY transaction_ts DESC
        ) = 1;

-- Pattern 2: Broadcast Hash Join Structuring
-- Filtering dimension table under 50 MB enables BigQuery to broadcast the hash
-- table to all fact slots, requiring zero network shuffle on the 500M row fact table.
WITH
  active_promotions AS (
    SELECT promotion_id, promotion_nm, discount_rt
      FROM `enterprise.retail_promo_04_anl.promotion_dim`
     WHERE is_active_ind = TRUE
       AND region_cd = 'US-WEST'
  )
SELECT o.order_id, o.customer_id, ROUND(o.order_amt * (1.0 - p.discount_rt), 2) AS discounted_amt
  FROM `enterprise.retail_sales_04_anl.order_fact` AS o
       INNER JOIN
       active_promotions AS p
       ON o.promotion_id = p.promotion_id
 WHERE o.order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
   AND o.tenant_id = 1042;

-- Pattern 3: Multi-Stage Materialization with Temporary Tables
-- BigQuery evaluates CTEs dynamically as inline query views.
-- To guarantee that an expensive intermediate reduction evaluates only once,
-- materialize the intermediate dataset into a temporary table.
CREATE TEMP TABLE daily_account_metric_agg
AS (
  SELECT account_id,
         COUNT(*)             AS transaction_qty,
         SUM(transaction_amt) AS volume_tot_amt
    FROM `enterprise.fin_ledger_04_anl.transaction_fact`
   WHERE transaction_dt = CURRENT_DATE()
   GROUP BY account_id
);

SELECT m.account_id, m.transaction_qty, m.volume_tot_amt, l.credit_limit_amt
  FROM daily_account_metric_agg AS m
       INNER JOIN
       `enterprise.fin_card_04_anl.credit_limit_dim` AS l
       ON m.account_id = l.account_id
 WHERE m.volume_tot_amt > l.credit_limit_amt
 UNION ALL
SELECT m.account_id, m.transaction_qty, m.volume_tot_amt, 0.0 AS credit_limit_amt
  FROM daily_account_metric_agg AS m
 WHERE m.transaction_qty > 1000;

-- Pattern 4: Approximate Aggregations for Scale
-- HyperLogLog++ and streaming quantile algorithms execute in a fraction of slot ms.
SELECT tenant_id,
       APPROX_COUNT_DISTINCT(user_id)                        AS approx_active_users_qty,
       APPROX_QUANTILES(request_latency_ms, 100)[OFFSET(50)] AS p50_latency_ms_val,
       APPROX_QUANTILES(request_latency_ms, 100)[OFFSET(99)] AS p99_latency_ms_val
  FROM `enterprise.telem_traffic_01_lnd.api_request_jnl`
 WHERE request_dt = CURRENT_DATE()
 GROUP BY tenant_id;

-- Pattern 5: Chained Function Calls with Sensible FLOAT64 Precision Rounding
-- Evaluates scalar transformations from left to right using dot notation (.)
-- and enforces contextual decimal precision on resulting table fields.
SELECT customer_id,
       (customer_nm).TRIM().UPPER()                            AS normalized_nm,
       (order_amt * (1.0 - discount_rt)).ROUND(2)              AS net_revenue_amt,
       (((order_amt - cost_amt) / order_amt) * 100.0).ROUND(2) AS profit_margin_pct
  FROM `enterprise.retail_sales_04_anl.order_fact`
 WHERE order_dt = CURRENT_DATE();
