-- bqfmt: skip
-- ============================================================================
-- GOOGLESQL DATA DEFINITION (DDL) AND DATA MANIPULATION (DML) PATTERNS
-- ============================================================================
-- Canonical statements and production architectural patterns for table creation,
-- vector indexes, routines, partition-pruned DML,
-- comprehensive MERGE statements, and multi-statement ACID transactions.
-- Conforms strictly to ISO 11179 column suffixes and architectural naming conventions.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. DATA DEFINITION LANGUAGE (DDL) PATTERNS
-- ----------------------------------------------------------------------------

-- Pattern 1.1: Dataset / Schema Creation with Governance Options
CREATE SCHEMA IF NOT EXISTS `corp-prod.ecom_sales_04_anl`
DEFAULT COLLATE 'und:ci'
OPTIONS (
  location                          = 'us-east4',
  description                       = 'Primary production eCommerce analytical warehouse',
  default_table_expiration_days     = 1095,
  default_partition_expiration_days = 730,
  kms_key_name                      = 'projects/corp-sec/locations/us-east4/keyRings/hsm/cryptoKeys/dw-key',
  storage_billing_model             = 'PHYSICAL'
);

-- Pattern 1.2: Production Partitioned & Clustered Table with Constraints
CREATE OR REPLACE TABLE `corp-prod.ecom_sales_04_anl.customer_order_fact`
(
  order_id         STRING NOT NULL,
  customer_id      INT64 NOT NULL,
  order_ts         TIMESTAMP NOT NULL,
  order_amt        FLOAT64,
  order_status_cd  STRING DEFAULT 'PENDING',
  shipping_address STRUCT<
                     street_desc STRING,
                     city_nm STRING,
                     postal_cd STRING,
                     country_cd STRING
                   >,
  line_items       ARRAY<STRUCT<
                     sku_cd STRING,
                     item_qty INT64,
                     unit_price_amt FLOAT64
                   >>,
  order_dt         DATE NOT NULL,
  created_ts       TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (order_id) NOT ENFORCED
)
PARTITION BY order_dt
CLUSTER BY customer_id, order_status_cd
OPTIONS (
  description               = 'Consolidated customer orders transactional ledger',
  require_partition_filter  = TRUE,
  partition_expiration_days = 730
);

-- Pattern 1.3: Create Table As Select (CTAS) with Aggregation and Rounding
CREATE OR REPLACE TABLE `corp-prod.ecom_sales_04_anl.monthly_customer_summary_agg`
PARTITION BY summary_month_dt
CLUSTER BY customer_id
AS (
  SELECT DATE_TRUNC(order_dt, MONTH) AS summary_month_dt,
         customer_id,
         COUNT(order_id)             AS order_qty,
         ROUND(SUM(order_amt), 2)    AS spend_tot_amt,
         ROUND(AVG(order_amt), 2)    AS order_avg_amt
    FROM `corp-prod.ecom_sales_04_anl.customer_order_fact`
   WHERE order_dt >= '2025-01-01'
   GROUP BY 1, 2
);

-- Pattern 1.4: Zero-Copy Table Clone & Read-Only Snapshot
-- Writeable zero-copy clone (delta billing only)
CREATE TABLE `corp-prod.ecom_sales_04_anl.customer_order_staging_stg`
CLONE `corp-prod.ecom_sales_04_anl.customer_order_fact`
  FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);

-- Read-only point-in-time snapshot with auto-expiration
CREATE SNAPSHOT TABLE `corp-prod.ecom_sales_04_anl.customer_order_q4_audit_snp`
CLONE `corp-prod.ecom_sales_04_anl.customer_order_fact`
OPTIONS (
  expiration_timestamp = TIMESTAMP '2027-01-01 00:00:00 UTC'
);

-- Pattern 1.5: Materialized View with Incremental Refresh and Staleness
CREATE OR REPLACE MATERIALIZED VIEW `corp-prod.ecom_sales_04_anl.daily_order_metric_mvw`
PARTITION BY order_dt
CLUSTER BY order_status_cd
OPTIONS (
  enable_refresh           = TRUE,
  refresh_interval_minutes = 30,
  max_staleness            = INTERVAL "0 0:30:0" DAY TO SECOND
)
AS (
  SELECT order_dt,
         order_status_cd,
         COUNT(*)                 AS order_qty,
         ROUND(SUM(order_amt), 2) AS daily_revenue_amt
    FROM `corp-prod.ecom_sales_04_anl.customer_order_fact`
   GROUP BY order_dt, order_status_cd
);

-- Pattern 1.6: Search Index for High-Throughput Text Filtering
CREATE SEARCH INDEX IF NOT EXISTS customer_order_search_idx
ON `corp-prod.ecom_sales_04_anl.customer_order_fact` (ALL COLUMNS)
OPTIONS (
  analyzer = 'LOG_ANALYZER'
);

-- Pattern 1.7: Vector Index for Semantic & Embedding Search
CREATE OR REPLACE TABLE `corp-prod.ecom_sales_05_feat.product_embedding_feat`
(
  product_id    STRING NOT NULL,
  product_nm    STRING NOT NULL,
  embedding_vec ARRAY<FLOAT64> NOT NULL,
  PRIMARY KEY (product_id) NOT ENFORCED
);

CREATE VECTOR INDEX IF NOT EXISTS product_embedding_ivf_idx
ON `corp-prod.ecom_sales_05_feat.product_embedding_feat` (embedding_vec)
OPTIONS (
  index_type    = 'IVF',
  distance_type = 'COSINE',
  ivf_options   = '{"num_lists": 1000}'
);

-- Pattern 1.8: SQL and JavaScript User-Defined Functions (UDFs)
-- Deterministic SQL UDF with Float Rounding
CREATE OR REPLACE FUNCTION `corp-prod.ecom_sales_04_anl.fn_calculate_discount`(base_price_amt FLOAT64, discount_pct FLOAT64)
RETURNS FLOAT64
DETERMINISTIC
AS (
  ROUND(base_price_amt * (1.0 - (discount_pct / 100.0)), 2)
);

-- JavaScript UDF for Specialized Transformation
CREATE OR REPLACE FUNCTION `corp-prod.ecom_sales_04_anl.fn_clean_postal_code`(raw_postal STRING)
RETURNS STRING
LANGUAGE js
AS r"""
  if (!raw_postal) return null;
  return raw_postal.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
""";

-- Pattern 1.9: Table-Valued Function (TVF)
CREATE OR REPLACE TABLE FUNCTION `corp-prod.ecom_sales_04_anl.tvf_recent_high_spenders`(lookback_days_qty INT64, threshold_spend_amt FLOAT64)
RETURNS TABLE <customer_id INT64, order_qty INT64, spend_tot_amt FLOAT64>
AS (
  SELECT customer_id,
         COUNT(order_id)          AS order_qty,
         ROUND(SUM(order_amt), 2) AS spend_tot_amt
    FROM `corp-prod.ecom_sales_04_anl.customer_order_fact`
   WHERE order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL lookback_days_qty DAY)
   GROUP BY customer_id
  HAVING spend_tot_amt >= threshold_spend_amt
);

-- Pattern 1.10: Schema Evolution (ALTER TABLE Operations)
ALTER TABLE `corp-prod.ecom_sales_04_anl.customer_order_fact`
  ADD COLUMN IF NOT EXISTS tracking_num STRING,
  ADD COLUMN IF NOT EXISTS priority_cd STRING DEFAULT 'STANDARD';

ALTER TABLE `corp-prod.ecom_sales_04_anl.customer_order_fact`
  ALTER COLUMN priority_cd DROP DEFAULT;

ALTER TABLE `corp-prod.ecom_sales_04_anl.customer_order_fact`
  SET OPTIONS (
    description = 'Updated customer order repository with tracking metadata'
  );


-- ----------------------------------------------------------------------------
-- 2. DATA MANIPULATION LANGUAGE (DML) PATTERNS
-- ----------------------------------------------------------------------------

-- Pattern 2.1: Multi-Row Insert & Bulk SELECT Insert
INSERT INTO `corp-prod.ecom_sales_04_anl.customer_order_fact`
  (order_id, customer_id, order_ts, order_amt, order_status_cd, order_dt)
VALUES
  ('ORD-2026-001', 9001, TIMESTAMP '2026-03-24 10:15:00 UTC', 154.20, 'COMPLETED', DATE '2026-03-24'),
  ('ORD-2026-002', 9002, TIMESTAMP '2026-03-24 10:20:00 UTC',  89.50, 'PENDING',   DATE '2026-03-24');

-- Pattern 2.2: Partition-Pruned Join-Style UPDATE
UPDATE `corp-prod.ecom_sales_04_anl.customer_order_fact` AS target
   SET order_amt       = ROUND(source.revised_amt, 2),
       order_status_cd = 'REVISED'
  FROM (
         SELECT customer_id,
                spend_tot_amt AS revised_amt
           FROM `corp-prod.ecom_sales_04_anl.monthly_customer_summary_agg`
       ) AS source
 WHERE target.order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   AND target.customer_id = source.customer_id
   AND target.order_status_cd = 'PENDING';

-- Pattern 2.3: Partition-Pruned DELETE
DELETE FROM `corp-prod.ecom_sales_04_anl.customer_order_fact`
 WHERE order_dt = DATE '2026-03-20'
   AND order_status_cd = 'CANCELLED';

-- Pattern 2.4: Instantaneous Table Truncation
TRUNCATE TABLE `corp-prod.ecom_sales_04_anl.customer_order_staging_stg`;

-- Pattern 2.5: Comprehensive Batched MERGE Statement
-- Demonstrates WHEN MATCHED, WHEN NOT MATCHED BY TARGET, and WHEN NOT MATCHED BY SOURCE
MERGE INTO `corp-prod.ecom_sales_04_anl.customer_order_fact` AS target
USING (
  SELECT order_id,
         customer_id,
         order_ts,
         ROUND(order_amt, 2) AS order_amt,
         order_status_cd,
         order_dt,
         cdc_action_cd -- 'I' for insert, 'U' for update, 'D' for delete
    FROM `corp-prod.ecom_sales_04_anl.customer_order_staging_stg`
   WHERE order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY)
) AS source
   ON target.order_dt = source.order_dt
  AND target.order_id = source.order_id

 -- 1. Matched row flagged for deletion in CDC source
 WHEN MATCHED AND source.cdc_action_cd = 'D' THEN
      DELETE

 -- 2. Matched row flagged for update in CDC source
 WHEN MATCHED AND source.cdc_action_cd = 'U' THEN
      UPDATE SET
        order_amt       = source.order_amt,
        order_status_cd = source.order_status_cd

 -- 3. Unmatched source row to be inserted into target
 WHEN NOT MATCHED BY TARGET AND source.cdc_action_cd = 'I' THEN
      INSERT (order_id, customer_id, order_ts, order_amt, order_status_cd, order_dt)
      VALUES (source.order_id, source.customer_id, source.order_ts, source.order_amt, source.order_status_cd, source.order_dt)

 -- 4. Target record absent from recent source partition window (retire or purge)
 WHEN NOT MATCHED BY SOURCE AND target.order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 DAY) AND target.order_status_cd = 'PENDING' THEN
      UPDATE SET
        order_status_cd = 'PURGED_FROM_SOURCE';

-- Pattern 2.6: Multi-Statement Transaction with Snapshot Isolation & Rollback
BEGIN
  DECLARE transfer_amt FLOAT64 DEFAULT 500.00;
  DECLARE sender_id INT64 DEFAULT 1001;
  DECLARE recipient_id INT64 DEFAULT 2002;
  DECLARE available_balance_amt FLOAT64;

  BEGIN TRANSACTION;

    -- Query current sender balance within transaction snapshot
    SET available_balance_amt = (
      SELECT balance_amt
        FROM `corp-prod.ecom_sales_04_anl.customer_wallet_fact`
       WHERE customer_id = sender_id
    );

    IF available_balance_amt IS NULL OR available_balance_amt < transfer_amt THEN
      RAISE USING MESSAGE = 'Transaction aborted: Insufficient funds in sender wallet.';
    END IF;

    -- Debit sender account
    UPDATE `corp-prod.ecom_sales_04_anl.customer_wallet_fact`
       SET balance_amt = ROUND(balance_amt - transfer_amt, 2)
     WHERE customer_id = sender_id;

    -- Credit recipient account
    UPDATE `corp-prod.ecom_sales_04_anl.customer_wallet_fact`
       SET balance_amt = ROUND(balance_amt + transfer_amt, 2)
     WHERE customer_id = recipient_id;

    -- Append audit ledger record
    INSERT INTO `corp-prod.ecom_sales_04_anl.wallet_transfer_jnl`
      (sender_id, recipient_id, transfer_amt, transfer_ts)
    VALUES
      (sender_id, recipient_id, ROUND(transfer_amt, 2), CURRENT_TIMESTAMP());

  COMMIT TRANSACTION;

EXCEPTION WHEN ERROR THEN
  BEGIN
    ROLLBACK TRANSACTION;
  EXCEPTION WHEN ERROR THEN
    -- Safely absorb errors if transaction was already aborted by OCC conflict or earlier rollback
  END;
  RAISE USING MESSAGE = CONCAT('Wallet transaction failed with error: ', @@error.message);
END;
