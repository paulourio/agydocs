-- ============================================================================
-- GOOGLESQL STATISTICAL SCORECARD & RISK MODEL EVALUATION PATTERNS
-- ============================================================================
-- Demonstrates high-performance, single-pass distributed implementations for:
-- 1. Gini Coefficient & Area Under ROC Curve (AUC) via Trapezoidal Integration
-- 2. Kolmogorov-Smirnov (KS) Two-Sample Separation Statistic
-- 3. Multi-Feature Population Stability Index (PSI) with Quantile Binning
-- ============================================================================
-- ----------------------------------------------------------------------------
-- PATTERN 1: GINI COEFFICIENT & ROC-AUC (TRAPEZOIDAL INTEGRATION)
-- ----------------------------------------------------------------------------
-- Pre-aggregating discrete score levels collapses millions of rows into hundreds,
-- computing exact AUC and Gini (2 * AUC - 1) in slot memory without shuffle spills.
-- Handles tied scores exactly via the trapezoidal midpoint (prev_cum + 0.5 * step).
WITH
  source_data AS (
    SELECT credit_scorecard_val, default_ind
      FROM `corp-prod.risk_scoring_07_inf.credit_scorecard_pred`
     WHERE partition_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
       AND credit_scorecard_val IS NOT NULL
       AND default_ind IN (0, 1)
  ),
  -- Step 1: Pre-aggregate bads and goods by distinct score level
  score_level_agg AS (
    SELECT credit_scorecard_val,
           COUNTIF(default_ind = 1) AS bad_qty,
           COUNTIF(default_ind = 0) AS good_qty
      FROM source_data
     GROUP BY credit_scorecard_val
  ),
  -- Step 2: Compute cumulative bad distribution across score ranks
  -- DIRECTION: ASC when lower score indicates higher risk (e.g. bureau 300-850)
  --            DESC when higher score indicates higher risk (e.g. probability of default)
  cumulative_curve AS (
    SELECT credit_scorecard_val,
           bad_qty,
           good_qty,
           COALESCE(
             SUM(bad_qty) OVER (
               ORDER BY credit_scorecard_val ASC
                ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
             ),
             0
           ) AS prev_cum_bad_qty,
           SUM(bad_qty) OVER (
             ORDER BY credit_scorecard_val ASC
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS cum_bad_qty
      FROM score_level_agg
  ),
  -- Step 3: Integrate trapezoidal area under ROC curve with exact tie adjustment
  auc_calc AS (
    SELECT SUM(good_qty)                                      AS tot_good_qty,
           MAX(cum_bad_qty)                                   AS tot_bad_qty,
           SUM(good_qty * (prev_cum_bad_qty + 0.5 * bad_qty)) AS auc_numerator_val
      FROM cumulative_curve
  )
SELECT tot_good_qty,
       tot_bad_qty,
       ROUND(auc_numerator_val / NULLIF(tot_good_qty * tot_bad_qty, 0), 4)               AS auc_val,
       ROUND(2.0 * (auc_numerator_val / NULLIF(tot_good_qty * tot_bad_qty, 0)) - 1.0, 4) AS gini_val
  FROM auc_calc;

-- ----------------------------------------------------------------------------
-- PATTERN 2: KOLMOGOROV-SMIRNOV (KS) SEPARATION STATISTIC
-- ----------------------------------------------------------------------------
-- Measures maximum vertical divergence between cumulative bad and good distributions:
-- KS = MAX(|CDF_bad - CDF_good|) * 100.
WITH
  source_data AS (
    SELECT credit_scorecard_val, default_ind
      FROM `corp-prod.risk_scoring_07_inf.credit_scorecard_pred`
     WHERE partition_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
       AND credit_scorecard_val IS NOT NULL
       AND default_ind IN (0, 1)
  ),
  score_level_agg AS (
    SELECT credit_scorecard_val,
           COUNTIF(default_ind = 1) AS bad_qty,
           COUNTIF(default_ind = 0) AS good_qty
      FROM source_data
     GROUP BY credit_scorecard_val
  ),
  totals AS (
    SELECT SUM(bad_qty)  AS tot_bad_qty,
           SUM(good_qty) AS tot_good_qty
      FROM score_level_agg
  ),
  cumulative_cdf AS (
    SELECT s.credit_scorecard_val,
           SUM(s.bad_qty) OVER (ORDER BY s.credit_scorecard_val ASC) / t.tot_bad_qty   AS cum_bad_p,
           SUM(s.good_qty) OVER (ORDER BY s.credit_scorecard_val ASC) / t.tot_good_qty AS cum_good_p
      FROM score_level_agg AS s
           CROSS JOIN
           totals AS t
  )
SELECT ROUND(MAX(ABS(cum_bad_p - cum_good_p)) * 100.0, 2) AS max_ks_pct
  FROM cumulative_cdf;

-- ----------------------------------------------------------------------------
-- PATTERN 3: POPULATION STABILITY INDEX (PSI) WITH QUANTILE BINNING
-- ----------------------------------------------------------------------------
-- Measures distributional drift between a baseline (expected) population and a
-- monitoring (actual) population using decile bins derived from the baseline
-- score distribution. PSI = SUM((actual_p - expected_p) * LN(actual_p / expected_p)).
-- Interpretation: PSI < 0.10 stable, 0.10-0.25 moderate shift, > 0.25 significant drift.
-- Uses APPROX_QUANTILES to derive decile boundaries from the baseline period,
-- then bins both populations against those boundaries in a single pass.
WITH
  baseline_scores AS (
    SELECT credit_scorecard_val
      FROM `corp-prod.risk_scoring_07_inf.credit_scorecard_pred`
     WHERE partition_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
       AND partition_dt < DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
       AND credit_scorecard_val IS NOT NULL
  ),
  monitoring_scores AS (
    SELECT credit_scorecard_val
      FROM `corp-prod.risk_scoring_07_inf.credit_scorecard_pred`
     WHERE partition_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
       AND credit_scorecard_val IS NOT NULL
  ),
  -- Step 1: Derive decile boundaries from baseline distribution
  decile_boundaries AS (
    SELECT boundaries
      FROM (
             SELECT APPROX_QUANTILES(credit_scorecard_val, 10) AS boundaries
               FROM baseline_scores
           )
  ),
  -- Step 2: Assign each baseline score to its decile bin
  baseline_binned AS (
    SELECT CASE
             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(1)]
             THEN
               1

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(2)]
             THEN
               2

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(3)]
             THEN
               3

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(4)]
             THEN
               4

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(5)]
             THEN
               5

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(6)]
             THEN
               6

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(7)]
             THEN
               7

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(8)]
             THEN
               8

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(9)]
             THEN
               9

             ELSE
               10

           END AS bin_id
      FROM baseline_scores AS s
           CROSS JOIN
           decile_boundaries AS b
  ),
  -- Step 3: Assign each monitoring score to the same decile bins
  monitoring_binned AS (
    SELECT CASE
             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(1)]
             THEN
               1

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(2)]
             THEN
               2

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(3)]
             THEN
               3

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(4)]
             THEN
               4

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(5)]
             THEN
               5

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(6)]
             THEN
               6

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(7)]
             THEN
               7

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(8)]
             THEN
               8

             WHEN
               s.credit_scorecard_val <= b.boundaries[OFFSET(9)]
             THEN
               9

             ELSE
               10

           END AS bin_id
      FROM monitoring_scores AS s
           CROSS JOIN
           decile_boundaries AS b
  ),
  -- Step 4: Compute bin proportions for both populations
  baseline_dist AS (
    SELECT bin_id, COUNT(*) AS bin_qty
      FROM baseline_binned
     GROUP BY bin_id
  ),
  monitoring_dist AS (
    SELECT bin_id, COUNT(*) AS bin_qty
      FROM monitoring_binned
     GROUP BY bin_id
  ),
  -- Step 5: Join distributions and compute per-bin PSI contribution
  -- Floor proportions at 0.0001 to prevent LN(0) singularity
  psi_bins AS (
    SELECT e.bin_id,
           GREATEST(
             e.bin_qty / SUM(e.bin_qty) OVER (),
             0.0001
           ) AS expected_p,
           GREATEST(
             a.bin_qty / SUM(a.bin_qty) OVER (),
             0.0001
           ) AS actual_p
      FROM baseline_dist AS e
           INNER JOIN
           monitoring_dist AS a
           ON e.bin_id = a.bin_id
  )
SELECT ROUND(SUM((actual_p - expected_p) * LN(actual_p / expected_p)), 4) AS psi_val
  FROM psi_bins;
