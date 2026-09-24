# BigQuery Machine Learning (BQML) Engineering Specification

This document provides a technical specification of BigQuery Machine Learning (BQML). It covers declarative model training, feature transformations, time-series forecasting, remote model endpoints, model-less foundation functions, and vector search operations.

---

## 1. Architectural Foundations

BigQuery ML executes algorithms inside the analytical warehouse. By executing distributed training operations directly across Borg worker slots and Colossus storage blocks, the platform trains models without transmitting raw records across external network boundaries. Model artifacts persist as relational schema objects.

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

Remote foundation models connect Borg slots to Vertex AI APIs through Cloud Resource connections. Direct inference functions invoke foundation endpoints without persisting relational model objects.

---

## 2. Supervised Learning Models

Engineers define supervised regression and classification models using the `CREATE MODEL` statement. The query body provides feature columns and target labels.

### 2.1 Logistic and Linear Regression

Linear and logistic algorithms optimize weights through gradient-based numeric solvers. Solvers converge rapidly.

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
);
```

### 2.2 Gradient Boosted Trees and Random Forests

Tree-based ensembles capture non-linear decision boundaries and complex feature interactions across distributed training shards.

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
);
```

---

## 3. Unsupervised Clustering and Decomposition

Unsupervised algorithms discover patterns without ground-truth labels.

### 3.1 K-Means Clustering

K-Means partitions records into geometric clusters. Distance calculations iterate until centroids stabilize.

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
);
```

### 3.2 Principal Component Analysis (PCA)

PCA projects correlated high-dimensional features into orthogonal latent variables. Dimensions compress efficiently.

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
);
```

---

## 4. Time-Series Forecasting (`ARIMA_PLUS`)

The `ARIMA_PLUS` model decomposes temporal data into trend, seasonal, and holiday components.

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
);
```

### 4.1 Generating Forecast Horizons

Engineers generate future projections with the `ML.FORECAST` function. Intervals bound risk.

```sql
SELECT product_line_cd,
       forecast_timestamp,
       ROUND(forecast_value, 2)                  AS projected_revenue,
       ROUND(prediction_interval_lower_bound, 2) AS lower_bound,
       ROUND(prediction_interval_upper_bound, 2) AS upper_bound
  FROM ML.FORECAST(
         MODEL `enterprise.ml.daily_revenue_forecaster`,
         STRUCT(30 AS horizon, 0.95 AS confidence_level)
       );
```

---

## 5. Remote Foundation Models

BigQuery ML integrates external foundation models via Cloud Resource connections. These remote models query Vertex AI Gemini and embedding endpoints directly.

```sql
CREATE OR REPLACE MODEL `enterprise.ml_04_anl.gemini_remote_model`
REMOTE WITH CONNECTION `us.vertex_ai_conn`
OPTIONS (
  endpoint = 'gemini-1.5-pro'
);

CREATE OR REPLACE MODEL `enterprise.ml_04_anl.embedding_remote_model`
REMOTE WITH CONNECTION `us.vertex_ai_conn`
OPTIONS (
  endpoint = 'text-embedding-005'
);
```

Engineers call remote models using `ML.GENERATE_TEXT` or `ML.GENERATE_EMBEDDING`. These calls dispatch parallel requests across distributed workers.

---

## 6. Feature Preprocessing Pipelines (`TRANSFORM`)

The `TRANSFORM` clause embeds preprocessing logic directly into the compiled model artifact. By evaluating statistical aggregates across all training rows prior to model fitting, Tier 1 transformers ensure that normalization parameters remain completely deterministic across both training jobs and subsequent scoring queries.

### 6.1 Tier 1 and Tier 2 Transformers

BigQuery ML divides transformations into two operational tiers. Tiers separate concerns cleanly.

Tier 1 functions compute statistical moments across the training corpus. These functions require an empty window specification `OVER ()`.
- `ML.STANDARD_SCALER`: Computes mean and standard deviation for numeric scaling.
- `ML.MIN_MAX_SCALER`: Scales numeric values into bounded intervals `[0, 1]`.
- `ML.BUCKETIZE`: Divides continuous variables into discrete numerical buckets.
- `ML.QUANTILE_BUCKETIZE`: Partitions values based on empirical quantile thresholds.
- `ML.ONE_HOT_ENCODER`: Encodes categorical strings into boolean feature arrays.
- `ML.LABEL_ENCODER`: Maps categorical strings to sequential integer indexes.

Tier 2 expressions evaluate row-level deterministic operations. These functions execute without window specifications. Examples include arithmetic operators, string manipulation, date extractions, and `CAST` statements.

```sql
CREATE OR REPLACE MODEL `enterprise.ml.applicant_risk_model`
TRANSFORM (
  applicant_id,
  ML.STANDARD_SCALER(annual_income_amt) OVER () AS scaled_income,
  ML.MIN_MAX_SCALER(credit_score_val) OVER ()   AS scaled_credit,
  ML.BUCKETIZE(debt_to_income_rt, [0.2, 0.4])   AS dti_bucket,
  ML.ONE_HOT_ENCODER(employment_type_cd) OVER() AS encoded_employment,
  EXTRACT(DAYOFWEEK FROM application_ts)        AS application_dow,
  is_defaulted_ind
)
OPTIONS (
  model_type       = 'BOOSTED_TREE_CLASSIFIER',
  input_label_cols = ['is_defaulted_ind']
)
AS (
  SELECT applicant_id,
         annual_income_amt,
         credit_score_val,
         debt_to_income_rt,
         employment_type_cd,
         application_ts,
         is_defaulted_ind
    FROM `enterprise.lending.applications_fact`
);
```

### 6.2 Temporal Point-in-Time Joins (`ML.ENTITY_FEATURES_AT_TIME`)

Predictive systems must prevent future data leakage during feature generation. The `ML.ENTITY_FEATURES_AT_TIME` function joins entity events to historic feature snapshots. It selects the latest feature record preceding each event timestamp. This design prevents leakage.

```sql
SELECT entity.transaction_id,
       entity.customer_id,
       entity.transaction_amt,
       features.avg_daily_spend_amt,
       features.chargeback_count_qty
  FROM ML.ENTITY_FEATURES_AT_TIME(
         TABLE `enterprise.fraud.transactions_fact`,
         'customer_id',
         'transaction_ts',
         TABLE `enterprise.fraud.customer_daily_metrics_feat`,
         'snapshot_ts',
         num_rows => 1
       ) AS entity
  JOIN `enterprise.fraud.customer_daily_metrics_feat` AS features
    ON entity.customer_id = features.customer_id
   AND entity.snapshot_ts = features.snapshot_ts;
```

---

## 7. Model Assessment and Diagnostics

Assessing model accuracy prior to deployment validates production readiness.

### 7.1 Computing Standard Evaluation Metrics

Evaluate metrics against holdout validation splits. Verification confirms stability.

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
       );
```

### 7.2 Confusion Matrix and ROC Curve Diagnostics

Inspect false positive and true positive rates across classification thresholds.

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

### 7.3 Inspecting Feature Weights and Feature Importance

Examine learned regression coefficients and tree split gains. Gains reveal importance.

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

## 8. Batch Inference (`ML.PREDICT`)

Inference workloads run as parallelized SQL scans against scoring tables.

### 8.1 Classic GoogleSQL Inference

Inference scores batches efficiently.

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
       );
```

### 8.2 Pipe Syntax Integration

GoogleSQL Pipe Syntax invokes `ML.PREDICT` directly within linear dataflows.

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
|> ORDER BY churn_score DESC;
```

---

## 9. Model-Less Direct Inference (`AI.*` Functions)

BigQuery provides the `AI.*` function family for direct inference. These routines call foundation models without declaring relational model objects. Workflows run faster.

### 9.1 Generative Text and Classification

The `AI.GENERATE` routine executes generative language models against prompt text. It supports structured JSON output schemas. Prompts extract entities.

```sql
SELECT ticket_id,
       AI.GENERATE(
         CONCAT('Analyze ticket urgency and category: ', customer_inquiry_txt),
         connection_id => 'us.vertex_ai_conn',
         output_schema => '{"urgency": "STRING", "category": "STRING"}'
       ) AS extracted_metadata_json
  FROM `enterprise.support.customer_inquiries_fact`;
```

The `AI.CLASSIFY` and `AI.SCORE` routines classify text into target categories.

```sql
SELECT feedback_id,
       AI.CLASSIFY(
         feedback_txt,
         labels => ['positive', 'neutral', 'negative'],
         connection_id => 'us.vertex_ai_conn'
       ) AS sentiment_label,
       AI.SCORE(
         feedback_txt,
         connection_id => 'us.vertex_ai_conn'
       ) AS quality_score
  FROM `enterprise.feedback.customer_reviews_dim`;
```

### 9.2 Zero-Shot Tabular and Forecasting Models

Engineers run foundation models on tabular and temporal datasets.
- `AI.FORECAST`: Generates zero-shot temporal predictions using TimesFM models.
- `AI.PREDICT`: Produces zero-shot tabular inferences using TabFM models.
- `AI.DETECT_ANOMALIES`: Identifies point anomalies across multivariate time series.

```sql
SELECT product_id, forecast_timestamp, forecast_value
  FROM AI.FORECAST(
         TABLE `enterprise.inventory.daily_sales_fact`,
         timestamp_col => 'sale_dt',
         data_col      => 'units_sold_qty',
         horizon       => 14,
         connection_id => 'us.vertex_ai_conn'
       );
```

### 9.3 Autonomous Embedding Columns

BigQuery tables can generate text embeddings automatically upon record ingestion. Tables declare stored generated columns powered by `AI.EMBED`. Vectors persist automatically.

```sql
CREATE OR REPLACE TABLE `enterprise.knowledge.articles_dim` (
  article_id    STRING NOT NULL,
  title_txt     STRING,
  body_txt      STRING,
  embedding_vec ARRAY<FLOAT64> GENERATED ALWAYS AS (
    AI.EMBED(body_txt, connection_id => 'us.vertex_ai_conn')
  ) STORED
);
```

The `AI.SIMILARITY` function computes distances between embedding vectors. Supported metrics include `COSINE` and `EUCLIDEAN`.

```sql
SELECT a.article_id AS source_id,
       b.article_id AS target_id,
       AI.SIMILARITY(a.embedding_vec, b.embedding_vec, metric => 'COSINE') AS score_val
  FROM `enterprise.knowledge.articles_dim` AS a
  CROSS JOIN `enterprise.knowledge.articles_dim` AS b
 WHERE a.article_id < b.article_id;
```

### 9.4 Semantic Search over Autonomous Embedding Columns (`AI.SEARCH`)

The `AI.SEARCH` table-valued function executes semantic vector queries across tables configured with autonomous embedding generation. It embeds query text at runtime using the model connection declared on the base table, retrieving nearest neighbor records directly:

```sql
SELECT base.article_id,
       base.title_txt,
       distance
  FROM AI.SEARCH(
         TABLE `enterprise.knowledge.articles_dim`,
         'body_txt',
         'distributed systems consensus algorithms',
         top_k => 5,
         distance_type => 'COSINE'
       );
```

- **`base_table`**: Target table configured with autonomous embedding generation.
- **`column_to_search`**: Source text column that the generated embedding column derives from (such as `'body_txt'`), rather than the generated vector column name.
- **`query_value`**: Search string embedded on the fly by the underlying model connection.
- **`distance_type`**: Distance calculation metric (`'COSINE'`, `'EUCLIDEAN'`, or `'DOT_PRODUCT'`).

---

## 10. Vector Search Operations

BigQuery evaluates high-dimensional nearest neighbor queries through `VECTOR_SEARCH()`. The function utilizes vector indexes created with `IVF` algorithms. Indexes accelerate queries.

### 10.1 Batch Vector Search

The search matches query vector tables against candidate base tables.

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

### 10.2 Inline Text Search with Direct Embeddings

Engineers combine `VECTOR_SEARCH()` with `AI.EMBED` for real-time text lookups.

```sql
SELECT query.search_text,
       base.product_id,
       base.product_nm,
       ROUND(distance, 4) AS cosine_distance
  FROM VECTOR_SEARCH(
         TABLE `enterprise.catalog_04_anl.product_embeddings_feat`,
         'embedding_vec',
         (
           SELECT AI.EMBED('lightweight trail running shoes', connection_id => 'us.vertex_ai_conn') AS query_vec,
                  'lightweight trail running shoes' AS search_text
         ),
         top_k => 5,
         distance_type => 'COSINE'
       );
```

---

## 11. Related References and Operational Tooling

- **Procedural Scripting:** Consult [Procedural SQL and Scripting](procedural_sql_and_scripting.md) for automated ML pipelines.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table creation and schema evolution syntax.
- **Query Optimization:** Consult [Query Design and Optimization Framework](query_design_and_optimization.md) for slot-efficient training design.
- **Pipe Syntax:** Consult [Pipe Query Syntax Reference](pipe_syntax.md) for linear dataflow construction.
- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for ML billing labels.
