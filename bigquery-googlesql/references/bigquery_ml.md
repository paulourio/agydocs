# BigQuery Machine Learning (BQML) Engineering Specification

This document provides a technical specification of BigQuery Machine Learning (BQML). It details declarative model training, feature preprocessing, time-series forecasting, performance metrics, and batch inference execution across distributed Borg slots.

---

## 1. Architectural Foundations

BigQuery ML executes machine learning algorithms directly inside the analytical data warehouse. By training models directly on Colossus storage blocks using Borg worker slots, BQML avoids moving raw records over external networks. Model state persists as a first-class relational dataset object:

```
+-----------------------------------------------------------------------------------+
|                           BigQuery ML Training Engine                             |
|  1. Feature Ingestion (Capacitor Columnar Pruning from Colossus)                   |
|  2. TRANSFORM Pipeline (StandardScaler, OneHotEncoder, Bucketize)                  |
|  3. Distributed Numerical Solvers (Coordinate Descent, L-BFGS, XGBoost, ARIMA)   |
|  4. Model Artifact Persistence (Persisted under project.dataset.model_name)       |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          Batch Inference (ML.PREDICT)                             |
|  - In-memory scoring across Borg worker slots                                     |
|  - Automatic schema alignment between input features and model signatures        |
+-----------------------------------------------------------------------------------+
```

---

## 2. Supervised Learning Models

Engineers define supervised regression and classification models using the `CREATE MODEL` statement. The query body provides feature columns and target labels.

### 2.1 Logistic and Linear Regression

Linear and logistic algorithms optimize weights through gradient-based numeric solvers:

```sql
CREATE OR REPLACE MODEL `enterprise.ml.churn_classifier`
TRANSFORM (
  customer_id,
  ML.STANDARD_SCALER(account_age_days) OVER () AS scaled_age,
  ML.STANDARD_SCALER(total_spend_amt) OVER ()  AS scaled_spend,
  ML.ONE_HOT_ENCODER(billing_tier_cd) OVER ()  AS encoded_tier,
  is_churned_ind
)
OPTIONS (
  model_type         = 'LOGISTIC_REG',
  input_label_cols   = ['is_churned_ind'],
  auto_class_weights = TRUE,
  data_split_method  = 'AUTO_SPLIT',
  l1_reg             = 0.01,
  l2_reg             = 0.05,
  max_iterations     = 30
)
AS (
  SELECT customer_id,
         account_age_days,
         total_spend_amt,
         billing_tier_cd,
         is_churned_ind
    FROM `enterprise.analytics.customer_profile_dim`
   WHERE snapshot_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
)
```

### 2.2 Gradient Boosted Trees and Random Forests

Tree-based ensembles handle non-linear decision boundaries and complex feature interactions:

```sql
CREATE OR REPLACE MODEL `enterprise.ml.fraud_boosted_tree`
OPTIONS (
  model_type        = 'BOOSTED_TREE_CLASSIFIER',
  input_label_cols  = ['is_fraudulent_ind'],
  num_parallel_tree = 4,
  max_tree_depth    = 6,
  learn_rate        = 0.1,
  subsample         = 0.85,
  data_split_method = 'CUSTOM',
  data_split_col    = 'split_assignment_cd'
)
AS (
  SELECT transaction_id,
         transaction_amt,
         clearing_speed_seconds,
         device_trust_score,
         foreign_card_ind,
         split_assignment_cd,
         is_fraudulent_ind
    FROM `enterprise.fraud.transaction_audit_fact`
   WHERE transaction_dt >= '2026-01-01'
)
```

---

## 3. Unsupervised Clustering and Decomposition

Unsupervised algorithms group rows and project dimensions without supervised labels.

### 3.1 K-Means Clustering

K-Means partitions input records into geometric clusters:

```sql
CREATE OR REPLACE MODEL `enterprise.ml.customer_segments_kmeans`
OPTIONS (
  model_type           = 'KMEANS',
  num_clusters         = 5,
  kmeans_init_method   = 'KMEANS++',
  distance_type        = 'COSINE',
  standardize_features = TRUE
)
AS (
  SELECT customer_id, monthly_order_qty, average_basket_amt, return_rate_p
    FROM `enterprise.analytics.customer_behavior_agg`
)
```

### 3.2 Principal Component Analysis (PCA)

PCA projects correlated high-dimensional features into orthogonal latent variables:

```sql
CREATE OR REPLACE MODEL `enterprise.ml.telemetry_pca`
OPTIONS (
  model_type               = 'PCA',
  num_principal_components = 10,
  pca_solver               = 'FULL'
)
AS (
  SELECT * EXCEPT(device_id, log_dt)
    FROM `enterprise.telemetry.sensor_readings_fact`
   WHERE log_dt = CURRENT_DATE()
)
```

---

## 4. Time-Series Forecasting (`ARIMA_PLUS`)

The `ARIMA_PLUS` model decomposes temporal data into trend, seasonal, and holiday components:

```sql
CREATE OR REPLACE MODEL `enterprise.ml.daily_revenue_forecaster`
OPTIONS (
  model_type                = 'ARIMA_PLUS',
  time_series_timestamp_col = 'order_dt',
  time_series_data_col      = 'daily_net_revenue',
  time_series_id_col        = 'product_line_cd',
  auto_arima                = TRUE,
  data_frequency            = 'DAILY',
  clean_spikes_and_dips     = TRUE,
  holiday_region            = 'US'
)
AS (
  SELECT product_line_cd, order_dt, SUM(order_amount) AS daily_net_revenue
    FROM `enterprise.sales.orders_fact`
   WHERE order_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 730 DAY)
   GROUP BY product_line_cd, order_dt
)
```

### 4.1 Generating Forecast Horizons

Generate future projections with the `ML.FORECAST` function:

```sql
SELECT product_line_cd,
       forecast_timestamp,
       ROUND(forecast_value, 2)                  AS projected_revenue,
       ROUND(prediction_interval_lower_bound, 2) AS lower_bound,
       ROUND(prediction_interval_upper_bound, 2) AS upper_bound
  FROM ML.FORECAST(
         MODEL `enterprise.ml.daily_revenue_forecaster`,
         STRUCT(30 AS horizon, 0.95 AS confidence_level)
       )
```

---

## 5. Model Assessment and Diagnostic Inspection

Assessing model accuracy prior to deployment validates production readiness.

### 5.1 Computing Standard Evaluation Metrics

Evaluate metrics against holdout validation splits:

```sql
SELECT roc_auc,
       accuracy,
       precision,
       recall,
       f1_score,
       log_loss
  FROM ML.EVALUATE(
         MODEL `enterprise.ml.churn_classifier`,
         (
           SELECT customer_id,
                  account_age_days,
                  total_spend_amt,
                  billing_tier_cd,
                  is_churned_ind
             FROM `enterprise.analytics.customer_profile_dim`
            WHERE snapshot_dt >= '2026-03-01'
         )
       )
```

### 5.2 Confusion Matrix and ROC Curve Diagnostics

Inspect false positive and true positive rates across classification thresholds:

```sql
-- Confusion Matrix at fixed 0.50 threshold
SELECT expected_label, predicted_label, num_predictions
  FROM ML.CONFUSION_MATRIX(
         MODEL `enterprise.ml.churn_classifier`,
         STRUCT(0.50 AS threshold)
       );

-- ROC Curve coordinate points
SELECT threshold, recall, false_positive_rate
  FROM ML.ROC_CURVE(
         MODEL `enterprise.ml.churn_classifier`
       );
```

### 5.3 Inspecting Feature Weights and Feature Importance

Examine learned regression coefficients and tree split gains:

```sql
-- Linear model weights
SELECT processed_input, weight, category_weights
  FROM ML.WEIGHTS(
         MODEL `enterprise.ml.churn_classifier`
       );

-- Boosted tree feature importance
SELECT feature, importance_weight, importance_gain
  FROM ML.FEATURE_IMPORTANCE(
         MODEL `enterprise.ml.fraud_boosted_tree`
       );
```

---

## 6. Batch Inference (`ML.PREDICT`)

Inference workloads run as parallelized SQL scans against scoring tables.

### 6.1 Classic GoogleSQL Inference

```sql
SELECT customer_id,
       predicted_is_churned_ind                       AS predicted_churn,
       predicted_is_churned_ind_probs[OFFSET(0)].prob AS churn_probability
  FROM ML.PREDICT(
         MODEL `enterprise.ml.churn_classifier`,
         (
           SELECT customer_id,
                  account_age_days,
                  total_spend_amt,
                  billing_tier_cd,
                  CAST(NULL AS BOOL) AS is_churned_ind
             FROM `enterprise.analytics.customer_profile_dim`
            WHERE snapshot_dt = CURRENT_DATE()
         )
       )
```

### 6.2 Pipe Syntax Integration

GoogleSQL Pipe Syntax invokes `ML.PREDICT` directly within the linear dataflow:

```sql
FROM `enterprise.analytics.customer_profile_dim`
|> WHERE snapshot_dt = CURRENT_DATE()
|> SELECT customer_id,
          account_age_days,
          total_spend_amt,
          billing_tier_cd,
          CAST(NULL AS BOOL) AS is_churned_ind
|> CALL ML.PREDICT(
          MODEL `enterprise.ml.churn_classifier`
        )
|> SELECT customer_id,
          predicted_is_churned_ind,
          ROUND(
            predicted_is_churned_ind_probs[OFFSET(0)].prob,
            4
          ) AS churn_score
|> WHERE churn_score >= 0.75
|> ORDER BY churn_score DESC
```

---

## 7. Vector Search and Embedding Inferences

BigQuery evaluates high-dimensional nearest neighbor lookups through the `VECTOR_SEARCH()` routine. The function operates over tables indexed with `CREATE VECTOR INDEX` using `IVF` algorithms or executes exact brute-force scans when unindexed.

### 7.1 Batch Vector Search
The search evaluates query vector embeddings against base table candidate embeddings:

```sql
SELECT query.query_id,
       base.product_id,
       base.product_nm,
       distance
  FROM VECTOR_SEARCH(
         TABLE `enterprise.catalog_04_anl.product_embeddings_feat`,
         'embedding_vec',
         TABLE `enterprise.catalog_04_anl.query_embeddings_stg`,
         'query_vec',
         top_k => 10,
         distance_type => 'COSINE',
         options => '{"fraction_lists_to_search": 0.05}'
       );
```

### 7.2 Inline Text Search with `ML.GENERATE_EMBEDDING`
Engineers combine `VECTOR_SEARCH()` with Vertex AI embedding endpoints to evaluate ad-hoc text search queries directly in SQL:

```sql
SELECT query.search_text,
       base.product_id,
       base.product_nm,
       ROUND(distance, 4) AS cosine_distance
  FROM VECTOR_SEARCH(
         TABLE `enterprise.catalog_04_anl.product_embeddings_feat`,
         'embedding_vec',
         (
           SELECT ml_generate_embedding_result AS query_vec,
                  content                       AS search_text
             FROM ML.GENERATE_EMBEDDING(
                    MODEL `enterprise.ml_04_anl.text_embedding_model`,
                    (SELECT 'waterproof trail running shoes' AS content)
                  )
         ),
         top_k => 5,
         distance_type => 'COSINE'
       );
```

---

## 8. Related References and Operational Tooling

- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table creation and schema evolution syntax.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for slot-efficient training design.
- **Pipe Syntax:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for linear dataflow construction.
- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for ML billing labels.

