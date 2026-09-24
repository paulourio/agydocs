# GoogleSQL Data Definition Language (DDL) Reference

This reference details the GoogleSQL Data Definition Language (DDL) in BigQuery. It defines syntax rules, parameters, and invariants for datasets, persistent tables, views, search and vector indexes, routines, and machine learning models.

```sql
-- Canonical GoogleSQL DDL Declaration
CREATE OR REPLACE TABLE `enterprise.analytics.customer_orders`
(
  order_id        STRING
                  NOT NULL,
  customer_id     INT64
                  NOT NULL,
  order_timestamp TIMESTAMP
                  NOT NULL,
  order_amount    FLOAT64,
  order_status    STRING,
  order_items     ARRAY<STRUCT<sku STRING, quantity INT64, unit_price FLOAT64>>,
  order_date      DATE
                  NOT NULL,
  PRIMARY KEY (   order_id) NOT ENFORCED
)
PARTITION BY order_date
  CLUSTER BY customer_id, order_status
OPTIONS (
  description               = 'Canonical customer order ledger',
  require_partition_filter  = TRUE,
  partition_expiration_days = 730
);
```

---

## 1. Column Schemas, Data Types, and Relational Constraints

GoogleSQL schemas define structural data types, null handling, default expressions, and relational constraints.

### 1.1 Data Type System

The type system spans scalar primitives, temporal types, semi-structured containers, geospatial entities, and discrete intervals:

- **Numeric Types:**
  - `INT64`: Signed 64-bit integer (-$9,223,372,036,854,775,808$ to $9,223,372,036,854,775,807$).
  - `NUMERIC`: Fixed-point decimal with 38 decimal digits of precision and 9 decimal digits of scale.
  - `BIGNUMERIC`: Extended fixed-point decimal with 76+ decimal digits of precision and 38 decimal digits of scale.
  - `FLOAT64`: IEEE 754 double-precision floating point. Computations resulting in `FLOAT64` output must apply contextual `ROUND()` operations to bound precision.
- **Text and Binary Types:**
  - `STRING`: Variable-length UTF-8 text. Supports sort order settings (such as `COLLATE 'und:ci'` for case-insensitive comparisons).
  - `BYTES`: Variable-length raw binary sequences.
  - `BOOL`: Logical boolean states (`TRUE`, `FALSE`, `NULL`).
- **Temporal Types:**
  - `DATE`: Calendar date (`YEAR-MONTH-DAY`) without timezone context.
  - `TIME`: Wall-clock time (`HOUR:MINUTE:SECOND.MICROSECOND`) independent of date or timezone.
  - `DATETIME`: Calendar date and wall-clock time.
  - `TIMESTAMP`: Absolute point in time stored in UTC with microsecond precision ($0001\text{-}01\text{-}01\ 00:00:00$ to $9999\text{-}12\text{-}31\ 23:59:59.999999\ \text{UTC}$).
  - `INTERVAL`: Represents a duration across years, months, days, hours, minutes, and seconds.
- **Semi-Structured and Complex Types:**
  - `ARRAY<T>`: Ordered list of zero or more elements sharing identical data type `T`. Nested arrays of arrays are invalid; wrap the inner array in a `STRUCT` container.
  - `STRUCT<field_name TYPE, ...>`: Container of ordered fields where each field possesses an explicit name and data type.
  - `JSON`: Native RFC 8259 JavaScript Object Notation documents.
- **Geospatial and Range Types:**
  - `GEOGRAPHY`: Points, linestrings, and polygons mapped to the WGS 84 reference spheroid.
  - `RANGE<DATE>`, `RANGE<DATETIME>`, `RANGE<TIMESTAMP>`: Contiguous interval spanning an explicit start and end boundary.

### 1.2 Column Integrity Constraints

BigQuery enforces null constraints and default values on writes, while treating keys as non-enforced metadata hints:

```sql
CREATE TABLE `enterprise.crm.customers`
(
  customer_id  INT64
               NOT NULL,
  company_id   INT64
               NOT NULL,
  email_addr   STRING
               NOT NULL,
  created_at   TIMESTAMP,
  account_tier STRING,
  PRIMARY KEY (customer_id) NOT ENFORCED,
  CONSTRAINT fk_companies FOREIGN KEY (company_id)
  REFERENCES `enterprise.crm.companies` (company_id) NOT ENFORCED
);
```

- **`NOT NULL`:** Rejects write records containing `NULL` values for the declared column.
- **`DEFAULT expression`:** Assigns an evaluated literal expression or deterministic function (`CURRENT_TIMESTAMP()`, `CURRENT_DATE()`) when insert payloads omit the column attribute.
- **`PRIMARY KEY (cols) NOT ENFORCED`:** Declares entity uniqueness. The storage subsystem does not validate uniqueness during writes. The query planner relies on this metadata to eliminate redundant joins and push down aggregates.
- **`FOREIGN KEY (cols) REFERENCES parent(cols) NOT ENFORCED`:** Declares referential integrity across parent and child relations. The storage subsystem does not reject orphaned foreign keys. The optimizer leverages this relationship to rewrite outer joins into inner joins when referential guarantees hold.

### 1.3 Field Settings and Column Options

Column definitions accept an `OPTIONS(...)` block declaring field metadata and arithmetic rules:

- **`description`:** String documentation describing attribute semantics. Supported on top-level columns and nested `STRUCT` attributes.
- **`rounding_mode`:** Arithmetic rounding behavior for `NUMERIC` and `BIGNUMERIC` types (`'ROUND_HALF_AWAY_FROM_ZERO'` vs `'ROUND_HALF_EVEN'`).
- **`data_policies`:** Array of Dataplex policy resource identifiers for column security and dynamic data masking.

For the exhaustive catalog of all field and table parameters with performance guidance and alteration syntax, consult the [Table and Field Parameters Reference](table_and_field_options.md).

---

## 2. Dataset Declarations (`CREATE SCHEMA`)

Datasets serve as the top-level namespace and regional storage containers for tables, views, and routines.

### 2.1 Grammar and Options

The `CREATE SCHEMA` statement initializes a dataset within a specified Google Cloud project and region:

```sql
CREATE SCHEMA IF NOT EXISTS `finance-corp.core_ledger`
DEFAULT COLLATE 'und:ci'
OPTIONS (
  location                          = 'us-east4',
  description                       = 'Primary enterprise general ledger repository',
  default_table_expiration_days     = 1095,
  default_partition_expiration_days = 730,
  default_kms_key_name              = 'projects/corp-sec/locations/us-east4/keyRings/hsm/cryptoKeys/ledger-key',
  storage_billing_model             = 'PHYSICAL'
);
```

### 2.2 Operational Dataset Invariants

Dataset management obeys explicit administrative semantics:

- **Sort Order Inheritance:** Tables created without explicit collation inherit the dataset default collation string.
- **Storage Billing Model:** Setting `storage_billing_model = 'PHYSICAL'` charges for compressed physical storage bytes instead of active logical bytes. This choice alters cost profiles when tables achieve high Capacitor compression ratios.
- **Cascade Purge:** Dropping datasets containing underlying tables requires the `CASCADE` keyword (`DROP SCHEMA `finance-corp.core_ledger` CASCADE`). Omitting this keyword defaults to `RESTRICT`, which rejects deletion if database objects occupy the dataset container.

---

## 3. Persistent Table Statements (`CREATE TABLE`)

Persistent tables store columnar records in Capacitor format on Google Colossus storage.

### 3.1 Partitioning and Clustering Architecture

Partitioning divides large tables into segments to prune scan volume. Clustering sorts column data within individual partitions:

```sql
CREATE OR REPLACE TABLE `enterprise.telemetry.device_logs`
(
  device_id    STRING
               NOT NULL,
  event_time   TIMESTAMP
               NOT NULL,
  firmware_ver STRING,
  payload_json JSON,
  ingest_date  DATE
               NOT NULL
)
PARTITION BY ingest_date
  CLUSTER BY device_id, firmware_ver
OPTIONS (
  require_partition_filter  = TRUE,
  partition_expiration_days = 180
);
```

- **Partitioning Strategies:**
  - *Time-Unit Column Partitioning:* Groups data by a declared `DATE`, `DATETIME`, or `TIMESTAMP` column (such as `DATE(event_time)`). Supported granularities include `HOUR`, `DAY`, `MONTH`, and `YEAR`.
  - *Ingestion-Time Partitioning:* Partitions records by arrival timestamp using pseudo-columns `_PARTITIONDATE` or `_PARTITIONTIME`.
  - *Integer Range Partitioning:* Groups data across discrete numerical intervals using `RANGE_BUCKET(column_id, GENERATE_ARRAY(start, end, interval))`.
  - *Partition Limits:* BigQuery caps each table at 4,000 distinct physical partitions. Exceeding this boundary triggers write failures.
- **Clustering Rules:**
  - Tables accept up to four clustering columns.
  - Column sequence dictates physical sort precedence inside Capacitor storage blocks. Place high-cardinality equality filter attributes first, followed by range filter attributes.
  - Clustering operates on standard types: `INT64`, `STRING`, `DATE`, `DATETIME`, `TIMESTAMP`, `NUMERIC`, `BIGNUMERIC`, `BOOL`, and `GEOGRAPHY`.

### 3.2 Auxiliary Build Patterns: CTAS, Clones, and Snapshots

BigQuery provides specialized table build patterns to support data transformation and point-in-time state preservation:

```sql
-- Create Table As Select (CTAS)
CREATE OR REPLACE TABLE `enterprise.reporting.monthly_revenue`
PARTITION BY report_month
  CLUSTER BY business_unit
AS (
  SELECT DATE_TRUNC(order_date, MONTH) AS report_month,
         business_unit,
         COUNT(order_id)             AS total_orders,
         ROUND(SUM(order_amount), 2) AS total_revenue
    FROM `enterprise.analytics.customer_orders`
   GROUP BY 1, 2
);

-- Zero-Copy Table Clone
CREATE TABLE `enterprise.testing.orders_clone_staging`
CLONE `enterprise.analytics.customer_orders`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);

-- Point-In-Time Snapshot Table
CREATE SNAPSHOT TABLE `enterprise.snapshots.orders_audit_q4`
CLONE `enterprise.analytics.customer_orders`
OPTIONS (expiration_timestamp=TIMESTAMP '2027-01-01 00:00:00 UTC');

-- Metadata-Only Schema Copy
CREATE TABLE `enterprise.analytics.orders_template`
LIKE `enterprise.analytics.customer_orders`;
```

- **`CREATE TABLE ... CLONE`:** Creates an independent, writeable duplicate table referencing identical underlying Capacitor blocks. Storage billing tracks only net delta changes applied after clone setup.
- **`CREATE SNAPSHOT TABLE`:** Generates a read-only historical record of a table at a target timestamp. Snapshots reject direct DML mutations.
- **`CREATE TABLE ... LIKE`:** Copies column types, null constraints, partitioning, and clustering schemes into a new empty table without transferring records.

---

## 4. Views and Materialized Views

GoogleSQL distinguishes between virtual logical views and physically computed materialized views.

### 4.1 Standard Logical Views

Logical views store SQL query definitions. The engine inlines the view logic into executing query plans during compilation:

```sql
CREATE OR REPLACE VIEW `enterprise.reporting.active_customers`
OPTIONS (description='Customers who completed orders within the preceding 90 days')
AS (
  SELECT DISTINCT c.customer_id, c.company_id, c.email_addr
    FROM `enterprise.crm.customers` AS c
         INNER JOIN
         `enterprise.analytics.customer_orders` AS o
         ON c.customer_id = o.customer_id
   WHERE o.order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
);
```

### 4.2 Materialized Views and Automatic Query Rewriting

Materialized views store precomputed query aggregates. The engine maintains these views incrementally and rewrites user queries to scan precomputed summaries:

```sql
CREATE OR REPLACE MATERIALIZED VIEW `enterprise.reporting.daily_revenue_mv`
PARTITION BY report_date
  CLUSTER BY customer_id
OPTIONS (
  enable_refresh           = TRUE,
  refresh_interval_minutes = 30,
  max_staleness            = INTERVAL '0 0:30:0' DAY TO SECOND
)
AS (
  SELECT order_date AS report_date,
         customer_id,
         COUNT(*)                    AS order_count,
         ROUND(SUM(order_amount), 2) AS daily_revenue
    FROM `enterprise.analytics.customer_orders`
   GROUP BY report_date, customer_id
);
```

- **Incremental Refresh:** BigQuery updates materialized view partitions when underlying base table partitions absorb incoming data.
- **Smart Query Rewrite:** When a query targets the base table `customer_orders` with aggregation filters matching `daily_revenue_mv`, the compiler substitutes the materialized view automatically without user query intervention.
- **Syntactic Constraints:** Materialized view queries prohibit non-deterministic functions (`CURRENT_TIMESTAMP()`, `RAND()`), analytical window functions, and nested aggregate expressions.

---

## 5. Search and Vector Indexes

Indexes optimize filters and distance-based similarity searches across large dataset volumes.

### 5.1 Full-Text Search Indexes (`CREATE SEARCH INDEX`)

Search indexes accelerate text search filters using the `SEARCH()` function across high-cardinality text columns:

```sql
-- bqfmt: skip
-- Search Index on Targeted Columns
CREATE SEARCH INDEX IF NOT EXISTS customer_text_idx
ON `enterprise.crm.customers` (email_addr)
OPTIONS (
  analyzer = 'NO_OP_ANALYZER'
);

-- Search Index Across Entire Table Schema
CREATE SEARCH INDEX IF NOT EXISTS order_payload_search_idx
ON `enterprise.analytics.customer_orders` (ALL COLUMNS)
OPTIONS (
  analyzer = 'LOG_ANALYZER'
);
```

- **Analyzers:** The `LOG_ANALYZER` breaks strings into tokens based on punctuation and whitespace boundaries. The `NO_OP_ANALYZER` analyzer preserves exact string values for exact-match retrieval.
- **Index Maintenance:** BigQuery updates search indexes asynchronously in the background without locking table writes.

### 5.2 Vector Similarity Indexes (`CREATE VECTOR INDEX`)

Vector indexes accelerate approximate nearest neighbor calculations executed via the `VECTOR_SEARCH()` routine:

```sql
-- bqfmt: skip
CREATE VECTOR INDEX IF NOT EXISTS product_embedding_idx
ON `enterprise.catalog.product_embeddings` (embedding_vector)
OPTIONS (
  index_type    = 'IVF',
  distance_type = 'COSINE',
  ivf_options   = '{"num_lists": 2000}'
);
```

- **Index Types:** `IVF` (Inverted File Index) partitions high-dimensional vectors into Voronoi cells to accelerate nearest neighbor queries.
- **Distance Metrics:** Supported distance types include `COSINE`, `EUCLIDEAN`, and `DOT_PRODUCT`.
- **Vector Requirements:** The indexed column must represent an `ARRAY<FLOAT64>` containing consistent dimensional lengths across all rows.

---

## 6. Routines: User-Defined Functions, TVFs, and Stored Procedures

Routines encapsulate business transformations, analytical logic, and administrative workflows.

### 6.1 Scalar User-Defined Functions (UDFs)

GoogleSQL supports both declarative SQL UDFs and embedded JavaScript routines:

```sql
-- Declarative SQL Scalar Function
CREATE OR REPLACE FUNCTION `enterprise.utils.calculate_vat`
(
  amount FLOAT64,
  rate   FLOAT64
)
RETURNS FLOAT64
DETERMINISTIC
OPTIONS (description='Computes value-added tax rounded to standard currency cents')
AS (
  ROUND(amount * rate, 2)
);

-- JavaScript Scalar Function
CREATE OR REPLACE FUNCTION `enterprise.utils.parse_user_agent`(ua_string STRING)
RETURNS
  STRUCT<browser STRING, os STRING>
LANGUAGE js
OPTIONS (library=['gs://enterprise-udf-assets/ua-parser-bundle.js'])
AS r"""
  try {
    const parser = new UAParser(ua_string);
    const result = parser.getResult();
    return {
      browser: result.browser.name || 'UNKNOWN',
      os: result.os.name || 'UNKNOWN'
    };
  } catch (err) {
    return { browser: 'PARSE_ERROR', os: 'PARSE_ERROR' };
  }
""";
```

### 6.2 Table-Valued Functions (TVFs)

Table-valued functions return a dynamic relational table rather than a solitary scalar value:

```sql
CREATE OR REPLACE TABLE FUNCTION `enterprise.analytics.get_high_value_customers`(min_spend FLOAT64)
RETURNS
  TABLE<
    customer_id      INT64,
    lifetime_value   FLOAT64,
    first_order_date DATE
  >
AS (
  SELECT customer_id,
         ROUND(SUM(order_amount), 2) AS lifetime_value,
         MIN(order_date)             AS first_order_date
    FROM `enterprise.analytics.customer_orders`
   GROUP BY customer_id
  HAVING lifetime_value >= min_spend
);
```

Queries invoke TVFs directly within the `FROM` clause: `SELECT customer_id, customer_name, lifetime_value FROM enterprise.analytics.get_high_value_customers(10000.0)`.

### 6.3 Stored Procedures (`CREATE PROCEDURE`)

Stored procedures execute multi-statement control flow, variable manipulation, transaction boundaries, and dynamic SQL statements:

```sql
CREATE OR REPLACE PROCEDURE `enterprise.pipelines.archive_stale_orders`
(
  IN  days_threshold INT64,
  OUT archived_count INT64
)
OPTIONS (description='Transfers stale orders into cold storage and purges source partitions')
BEGIN
  DECLARE cutoff_date DATE;

  SET cutoff_date = DATE_SUB(CURRENT_DATE(), INTERVAL days_threshold DAY);

  BEGIN TRANSACTION;

  INSERT INTO `enterprise.cold_archive.customer_orders`
    (order_id, customer_id, order_date, order_amount)
  SELECT order_id, customer_id, order_date, order_amount
    FROM `enterprise.analytics.customer_orders`
   WHERE order_date < cutoff_date;

  SET archived_count = @@row_count;

  DELETE FROM `enterprise.analytics.customer_orders`
   WHERE order_date < cutoff_date;

  COMMIT TRANSACTION;
END;
```

---

## 7. Machine Learning Models (`CREATE MODEL`)

BigQuery ML integrates machine learning model training and Vertex AI remote inference into declarative DDL statements:

```sql
-- In-Database Linear Regression Model
CREATE OR REPLACE MODEL `enterprise.ml.churn_prediction_model`
OPTIONS (
  model_type         = 'LOGISTIC_REG',
  input_label_cols   = ['churned'],
  auto_class_weights = TRUE,
  data_split_method  = 'AUTO_SPLIT'
)
AS (
  SELECT churned, account_age_days, total_spend, support_ticket_count
    FROM `enterprise.features.customer_features`
);

-- Remote Vertex AI Model Binding
CREATE OR REPLACE MODEL `enterprise.ml.text_embedding_remote`
REMOTE WITH CONNECTION `us-east4.vertex-connection`
OPTIONS (endpoint='//aiplatform.googleapis.com/projects/corp-prod/locations/us-east4/publishers/google/models/text-embedding-005');
```

---

## 8. Schema Alteration and Object Removal (`ALTER` and `DROP`)

GoogleSQL provides statements to alter table attributes, adjust constraints, and remove persistent entities safely.

### 8.1 Schema Evolution Statements

Tables evolve without full data restructurings:

```sql
-- Adding Columns
ALTER TABLE `enterprise.analytics.customer_orders`
  ADD COLUMN IF NOT EXISTS tracking_number STRING,
  ADD COLUMN IF NOT EXISTS shipping_cost FLOAT64;

-- Modifying Column Attributes
ALTER TABLE `enterprise.analytics.customer_orders`
  ALTER COLUMN shipping_cost DROP DEFAULT;

ALTER TABLE `enterprise.analytics.customer_orders`
  ALTER COLUMN tracking_number SET DATA TYPE STRING;

ALTER TABLE `enterprise.analytics.customer_orders`
  DROP COLUMN IF EXISTS legacy_notes;

-- Renaming Columns
ALTER TABLE `enterprise.analytics.customer_orders`
  RENAME COLUMN shipping_cost TO freight_cost;

-- Altering Table Options
ALTER TABLE `enterprise.analytics.customer_orders`
  SET OPTIONS (
        partition_expiration_days = 365,
        description               = 'Updated production orders repository'
      );
```

### 8.2 Dropping Persistent Database Objects

Drop statements remove entities from the dataset namespace:

```sql
-- bqfmt: skip
DROP TABLE IF EXISTS `enterprise.analytics.customer_orders`;
DROP VIEW IF EXISTS `enterprise.reporting.active_customers`;
DROP MATERIALIZED VIEW IF EXISTS `enterprise.reporting.daily_revenue_mv`;
DROP SEARCH INDEX IF EXISTS customer_text_idx ON `enterprise.crm.customers`;
DROP VECTOR INDEX IF EXISTS product_embedding_idx ON `enterprise.catalog.product_embeddings`;
DROP FUNCTION IF EXISTS `enterprise.utils.calculate_vat`;
DROP TABLE FUNCTION IF EXISTS `enterprise.analytics.get_high_value_customers`;
DROP PROCEDURE IF EXISTS `enterprise.pipelines.archive_stale_orders`;
DROP MODEL IF EXISTS `enterprise.ml.churn_prediction_model`;
DROP SCHEMA IF EXISTS `enterprise.temporary_staging` CASCADE;
```

---

## 9. Related References and Operational Tooling

- **Table and Field Parameters:** Consult [Table and Field Options](table_and_field_options.md) for complete options and rounding parameters.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for partition boundary rules.
- **DML and Transactions:** Consult [DML and Transactions Guide](dml_and_transactions.md) for data modification and isolation levels.
- **Data Ingestion:** Consult [Data Ingestion and Export](data_loading_and_export.md) for data loading and batch export operations.
- **Executable DDL Patterns:** Inspect [DDL and DML Patterns](../examples/ddl_and_dml_patterns.sql) for canonical table creation, lakehouses, vector indexes, and partition layouts.
