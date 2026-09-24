-- ============================================================================
-- INCREMENTAL PARTITION-PRUNED MERGE DESIGN PATTERN
-- ============================================================================
-- Business Goal:
-- Incrementally process monthly debtor financial profiles, compute change
-- detection hashes (data_hd), guard against empty ingestion passes, and merge
-- into the partitioned warehouse table while pruning unreferenced partition blocks.
-- ============================================================================
DECLARE g_months ARRAY<DATE> DEFAULT [DATE '2026-03-01', DATE '2026-03-02'];

-- Step 1: Stage incoming delta with computed hash digest (data_hd)
-- Excludes business keys (person_bk, month_dt) and audit fields from hash.
CREATE TEMP TABLE staged_customer_debt_delta_stg
AS (
  SELECT a.person_bk,
         a.month_dt,
         a.debt_amt,
         a.delinquent_ind,
         a.active_ind,
         -- Struct serialization pattern for change detection:
         FARM_FINGERPRINT(
           TO_JSON_STRING(
             (SELECT AS STRUCT
                     a.* EXCEPT(person_bk, month_dt))
           )
         ) AS data_hd
    FROM `enterprise.lend_debt_02_str.customer_debt_rec` AS a
   WHERE a.month_dt IN UNNEST(g_months)
);

-- Step 2: Guard against empty delta batches to prevent unnecessary slot consumption
IF
  (
    SELECT COUNT(*)
      FROM staged_customer_debt_delta_stg
  ) = 0
THEN
  RETURN;
END IF;

-- Step 3: Execute partition-pruned merge mutation
-- Prunes target partitions via IN UNNEST(g_months) before evaluating row matches.
-- Skips unchanged rows via t.data_hd != d.data_hd to avoid delete mask overhead.
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
