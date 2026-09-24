# GoogleSQL Table and Field Parameters Reference

This reference catalogs the complete set of column settings and table parameters available in BigQuery and GoogleSQL. It provides syntax rules, supported data types, allowed values, performance trade-offs, and operational guidance across persistent tables, materialized views, indexes, routines, and machine learning models.

```sql
-- Canonical Table and Column Options Declaration
CREATE OR REPLACE TABLE `enterprise.warehouse.orders_ledger`
(
  order_id     STRING
               NOT NULL
               OPTIONS (description='Surrogate order UUID identifier'),
  customer_id  INT64
               NOT NULL
               OPTIONS (description='Foreign key referencing customer entity'),
  order_amount NUMERIC(12, 2)
               NOT NULL
               OPTIONS (
                 description   = 'Total order charge in USD',
                 rounding_mode = 'ROUND_HALF_AWAY_FROM_ZERO'
               ),
  order_date   DATE
               NOT NULL
)
PARTITION BY order_date
  CLUSTER BY customer_id
OPTIONS (
  description               = 'Enterprise core orders transactional ledger',
  friendly_name             = 'Orders Core Ledger',
  require_partition_filter  = TRUE,
  partition_expiration_days = 730,
  default_rounding_mode     = 'ROUND_HALF_AWAY_FROM_ZERO',
  storage_billing_model     = 'PHYSICAL',
  labels                    = [
                                ('env', 'prod'),
                                ('domain', 'sales'),
                                ('tier', 'p1')
                              ]
)
```

---

## 1. Column and Field Parameters

Column parameters define field documentation, numerical rounding modes, and policy tags. Engineers specify parameters immediately following the column data type.

### 1.1 Field Settings Specification

| Parameter Name | Data Type | Scope | Allowed Values / Syntax | Default |
| :--- | :--- | :--- | :--- | :--- |
| **`description`** | `STRING` | Top-level columns and nested `STRUCT` fields | UTF-8 text string (maximum 1,024 characters) | `NULL` |
| **`rounding_mode`** | `STRING` | `NUMERIC` and `BIGNUMERIC` columns | `'ROUND_HALF_AWAY_FROM_ZERO'`, `'ROUND_HALF_EVEN'` | Table default or `'ROUND_HALF_AWAY_FROM_ZERO'` |
| **`policy_tags`** | `ARRAY<STRING>` | Top-level columns and nested `STRUCT` fields | Fully qualified Dataplex taxonomy tag resource paths | `NULL` |

### 1.2 Operational Guidance for Column Settings

#### `description`
- **Scope:** Assign explicit descriptions to every primary key, foreign key, quantitative measure, and status flag in dimensional models.
- **Nested Struct Fields:** BigQuery supports parameters on individual nested struct attributes:
  ```text
  user_address STRUCT<
    street STRING OPTIONS (description = 'Primary street delivery line'),
    postal_code STRING OPTIONS (description = 'Postal code formatted in standard ZIP or postal code notation')
  > OPTIONS (description = 'Validated recipient physical mailing address')
  ```
- **Catalog Visibility:** Populating field descriptions exposes attributes to Google Cloud Dataplex and internal schema search tools.

#### `rounding_mode`
- **Arithmetic Rounding (`'ROUND_HALF_AWAY_FROM_ZERO'`):** Rounds half-way values away from zero, such as rounding 3.5 to 4, and -3.5 to -4. Apply this mode for retail billing, customer invoices, and commercial contracts where standard commercial arithmetic is mandated.
- **Banker's Rounding (`'ROUND_HALF_EVEN'`):** Rounds half-way values toward the nearest even integer, such as rounding 3.5 to 4, 2.5 to 2, and -2.5 to -2. Apply this mode for high-frequency accounting ledgers, banking clearing houses, and statistical summaries to eliminate positive cumulative drift.

#### `policy_tags`
- **Scope:** Attach Dataplex policy tags to protect sensitive attributes such as PII, credit card tokens, and salary values.
- **Access Verification:** BigQuery checks column access against the user role during query planning, masking or denying access based on the tag policy.

---

## 2. Table Storage and Policy Settings

Storage and policy parameters dictate data lifecycle windows, scan pruning rules, billing models, and encryption keys.

### 2.1 Storage Parameters Specification

| Parameter Name | Data Type | Allowed Values / Format | Production Default |
| :--- | :--- | :--- | :--- |
| **`description`** | `STRING` | UTF-8 text string | `NULL` |
| **`friendly_name`** | `STRING` | UTF-8 display name (UI presentation) | `NULL` |
| **`labels`** | `ARRAY<STRUCT<STRING, STRING>>` | Key-value pairs matching `[a-z0-9_-]+` (max 64) | `[]` |
| **`require_partition_filter`** | `BOOL` | `TRUE`, `FALSE` | `FALSE` |
| **`partition_expiration_days`** | `FLOAT64` | Positive decimal or integer day count | `NULL` (never expires) |
| **`expiration_timestamp`** | `TIMESTAMP` | Explicit UTC timestamp string | `NULL` (never expires) |
| **`storage_billing_model`** | `STRING` | `'LOGICAL'`, `'PHYSICAL'` | Dataset default or `'LOGICAL'` |
| **`kms_key_name`** | `STRING` | Cloud KMS crypto key resource path | Google-managed encryption |
| **`default_rounding_mode`** | `STRING` | `'ROUND_HALF_AWAY_FROM_ZERO'`, `'ROUND_HALF_EVEN'` | `'ROUND_HALF_AWAY_FROM_ZERO'` |

### 2.2 Operational Guidance for Storage Settings

#### `require_partition_filter = TRUE`
- **Behavior:** Rejects any query targeting the table that omits a partition filter in its top-level `WHERE` clause or `MERGE` join condition.
- **Production Standard:** Mandate `require_partition_filter = TRUE` on all production partitioned tables exceeding $10\text{ GB}$. This rule prevents accidental full-table scans that exhaust slot capacity and generate billable byte waste.

#### `partition_expiration_days`
- **Mechanics:** BigQuery tracks the age of individual partitions based on the partition key value. Partitions older than the expiration threshold undergo automatic background purge by Colossus garbage workers.
- **Guidance:** Apply partition expiration to bronze ingestion zones, staging scratch tables, and raw telemetry streams (for example, 90 to 365 days). Never configure partition expiration on immutable financial audit ledgers.

#### `storage_billing_model = 'PHYSICAL'`
- **Cost Foundations:** Logical billing charges for uncompressed table bytes plus time-travel storage. Physical storage billing charges for compressed Capacitor blocks on Colossus plus 7-day time travel and 7-day fail-safe storage.
- **Guidance:** Switch tables to physical storage billing when column compression ratios exceed $2:1$. Wide analytical tables containing repetitive strings, JSON documents, or sparse arrays often achieve $3:1$ to $5:1$ compression ratios, cutting storage expenditure by 50% or more.

#### `kms_key_name`
- **Security Compliance:** Binds the table to an external customer-managed encryption key (CMEK) managed in Cloud KMS.
- **Lifecycle Warning:** Revoking or destroying the KMS key renders the table immediately inaccessible to all queries and storage jobs.

---

## 3. Materialized Views Settings

Materialized views store precomputed query results and support background maintenance settings.

### 3.1 Materialized View Parameters

| Parameter Name | Data Type | Allowed Values / Format | Default |
| :--- | :--- | :--- | :--- |
| **`enable_refresh`** | `BOOL` | `TRUE`, `FALSE` | `TRUE` |
| **`refresh_interval_minutes`** | `INT64` / `FLOAT64` | Positive number $\ge 1$ minute | `30` |
| **`max_staleness`** | `INTERVAL` | Valid BigQuery interval literal | `INTERVAL "0 0:0:0" DAY TO SECOND` |

### 3.2 Operational Guidance for Materialized View Settings

#### `enable_refresh` and `refresh_interval_minutes`
- **Automatic Maintenance:** When `enable_refresh = TRUE`, BigQuery initiates background refresh jobs as underlying base tables absorb writes.
- **Conserving Slot Compute:** On base tables subject to continuous micro-batch writes, configure `refresh_interval_minutes` to 60 or 120 minutes. An aggressive refresh cadence (such as 1 to 5 minutes) consumes background slots continuously.

#### `max_staleness`
- **Faster Query Rewrites:** The `max_staleness` setting allows queries to read precomputed materialized view data even if the base table absorbed changes more recently than the last refresh pass, provided staleness remains within the declared interval.
- **Guidance:** For executive dashboards and analytical reports, assign `max_staleness = INTERVAL "0 1:0:0" DAY TO SECOND` (1 hour) or `INTERVAL 30 MINUTE`. This setting permits BigQuery to rewrite base queries into instant materialized view scans without recalculating expensive base table aggregates.

---

## 4. Search and Vector Indexes Settings

Search and vector indexes accelerate text retrieval and embedding distance calculations.

### 4.1 Index Parameters Specification

| Index Type | Parameter Name | Data Type | Allowed Values | Guidance |
| :--- | :--- | :--- | :--- | :--- |
| **Search Index** | **`analyzer`** | `STRING` | `'LOG_ANALYZER'`, `'NO_OP_ANALYZER'`, `'PATTERN_ANALYZER'` | Use `'LOG_ANALYZER'` for freeform logs and prose. Use `'NO_OP_ANALYZER'` for exact matches on codes, IDs, and emails. |
| **Vector Index** | **`index_type`** | `STRING` | `'IVF'` | Inverted File index partitioning vector space into Voronoi cells. |
| **Vector Index** | **`distance_type`** | `STRING` | `'COSINE'`, `'EUCLIDEAN'`, `'DOT_PRODUCT'` | Select `'COSINE'` for normalized text embeddings. Select `'EUCLIDEAN'` for spatial metric distances. |
| **Vector Index** | **`ivf_options`** | `STRING` | JSON string: `'{"num_lists": N}'` | Calibrate list count to dataset row scale ($N \approx \sqrt{\text{rows}}$). |

---

## 5. Machine Learning Models Parameters (`CREATE MODEL`)

BigQuery ML model declarations accept training hyper-parameters and Vertex AI remote endpoint settings.

### 5.1 Model Parameters Specification

| Parameter Name | Data Type | Purpose and Guidance |
| :--- | :--- | :--- |
| **`model_type`** | `STRING` | Model algorithm (`'LOGISTIC_REG'`, `'LINEAR_REG'`, `'BOOSTED_TREE_CLASSIFIER'`, `'RANDOM_FOREST_REGRESSOR'`, `'KMEANS'`, `'PCA'`, `'ARIMA_PLUS'`). |
| **`input_label_cols`** | `ARRAY<STRING>` | Target prediction columns evaluated during supervised training. |
| **`auto_class_weights`** | `BOOL` | Balances positive and negative class weights in imbalanced classification sets. |
| **`data_split_method`** | `STRING` | Dataset split strategy: `'AUTO_SPLIT'`, `'RANDOM'`, `'CUSTOM'`, `'SEQ'`, `'NO_SPLIT'`. |
| **`early_stop`** | `BOOL` | Halts training when validation metric convergence plateaus, conserving slot hours. |
| **`endpoint`** | `STRING` | Vertex AI remote model endpoint URL when binding remote models. |

---

## 6. Dynamic Alteration and Settings Introspection

Engineers alter active parameters on existing tables and inspect active settings through information schema metadata views.

### 6.1 Modifying and Clearing Table Parameters

The `ALTER TABLE SET OPTIONS` statement updates table configuration settings dynamically:

```sql
-- Update active table options
ALTER TABLE `enterprise.warehouse.orders_ledger`
  SET OPTIONS (
        partition_expiration_days = 365,
        require_partition_filter  = TRUE,
        description               = 'Updated enterprise orders ledger with 1-year retention'
      );

-- Clear a parameter and revert to system default (assign NULL)
ALTER TABLE `enterprise.warehouse.orders_ledger`
  SET OPTIONS (
        partition_expiration_days = NULL,
        friendly_name             = NULL
      );
```

### 6.2 Modifying and Clearing Column Parameters

The `ALTER TABLE ALTER COLUMN SET OPTIONS` statement updates column metadata:

```sql
-- Update column description and rounding mode
ALTER TABLE `enterprise.warehouse.orders_ledger`
  ALTER COLUMN order_amount
    SET OPTIONS (
          description   = 'Adjusted gross order amount in USD',
          rounding_mode = 'ROUND_HALF_EVEN'
        );

-- Clear column description (assign NULL)
ALTER TABLE `enterprise.warehouse.orders_ledger`
  ALTER COLUMN order_amount
    SET OPTIONS (description=NULL);
```

### 6.3 Auditing Settings via INFORMATION_SCHEMA

BigQuery provides system views to inspect active table and field configuration parameters:

```sql
-- Inspect all table-level options across a dataset
SELECT table_name, option_name, option_type, option_value
  FROM `enterprise.warehouse.INFORMATION_SCHEMA.TABLE_OPTIONS`
 WHERE table_name = 'orders_ledger';

-- Inspect all column-level options across a dataset
SELECT table_name,
       column_name,
       option_name,
       option_type,
       option_value
  FROM `enterprise.warehouse.INFORMATION_SCHEMA.COLUMN_OPTIONS`
 WHERE table_name = 'orders_ledger';
```

---

## 7. Related References and Operational Tooling

- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table creation and schema definitions.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for partition bounds.
- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for labels and policy tags.
- **System Views:** Consult [INFORMATION_SCHEMA System Views](information_schema_reference.md) for metadata catalog views.
