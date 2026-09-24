# BigQuery Data Architecture and Lifecycle Specification

This specification defines the multi-tier data architecture and lifecycle model for Google Cloud BigQuery. It formalizes processing guarantees, physical storage configurations, and ownership boundaries across the data platform. Clean architectural boundaries prevent schema coupling, eliminate training-serving skew, and support petabyte-scale analytical workloads.

---

## 1. Architectural Principles

The data platform divides analytical duties between two operational rules:

1. **The Entity Rule (Layers `01` through `04`):** Managed by Data Engineering squads. Tables in these layers model core business concepts, financial ledgers, and operational events. A single data product encompasses all assets required to operate an engine. Upstream source systems anchor schemas in these tiers.
2. **The Consumer Rule (Layers `05` through `08`):** Managed by Data Science and Machine Learning squads. The model is the product. Tables in these layers organize signals around statistical consumers and algorithms. If a risk team trains a behavioral scorecard, the resulting data product reflects the scoring engine, regardless of upstream feature provenance.

Separating entity models from consumer features preserves architectural stability. When upstream vendors alter raw payload schemas, engineers update integration mappings without corrupting production feature stores.

```text
+-------------------------------------------------------------------------------------------------+
|                                 DATA PLATFORM LIFECYCLE                                         |
|                                                                                                 |
| [01_landing]   --> [02_structured]  --> [03_integration] --> [04_analytical]                  |
| Raw Payloads       Cleaned Casts        Data Vault 2.0        Kimball Star Schemas / OBT        |
| (Data Eng)         (Data Eng)           (Data Eng)            (Data Eng)                        |
|                                                                    |                            |
|                                                                    v                            |
| [08_metrics]   <-- [07_inference]   <-- [06_training_set] <-- [05_feature]                     |
| Observability      Model Scores         Frozen Snapshots      ML Feature Store                  |
| (MLOps)            (Data Science)       (Data Science)        (Data Science)                    |
+-------------------------------------------------------------------------------------------------+
```

---

## 2. Eight-Layer Lifecycle Specification

Every table resides within an explicit lifecycle layer. Each layer provides distinct physical guarantees.

### 2.1 Layer 1: Landing (`01_landing` / `01_lnd`)

The landing layer serves as the immutable arrival buffer for raw files, external vendor drops, and backtest datasets. Tables in this layer represent raw payloads dumped exactly as received from providers.

- **Storage Format:** Raw JSON strings or bytes stored in native BigQuery columns (`payload STRING` or `record_bytes BYTES`).
- **Processing Guarantee:** Append-only ingest. The landing tier provides no uniqueness guarantees across business keys, capturing raw arrival snapshots rather than cleaned business timelines.
- **Partitioning and Clustering:** Ingestion-time partitioning using `_PARTITIONTIME` set to daily intervals. Tables configure partition retention between 30 and 90 days.
- **Access Control:** Restricted to automated ingest service accounts and ingestion monitoring pipelines.

### 2.2 Layer 2: Structured (`02_structured` / `02_str`)

The structured layer mirrors source systems 1:1 while parsing raw strings into native BigQuery data types. It flattens simple payloads and retains complex hierarchies using native `STRUCT` and `ARRAY` types.

- **Storage Format:** Strongly typed schemas using `INT64`, `NUMERIC`, `TIMESTAMP`, and `ARRAY<STRUCT<...>>`.
- **Processing Guarantee:** Deduplicated at source record boundaries. Cross-system joins are strictly prohibited in this tier.
- **Partitioning and Clustering:** Partitioned by source event date (`event_dt`). Clustered by high-cardinality natural keys (`customer_id`, `account_id`).
- **Use Case:** Serves as the validated baseline for all enterprise transformations.

### 2.3 Layer 3: Integration (`03_integration` / `03_int` / `03_uni`)

The integration layer unifies fractured operational systems representing the exact same business entity into a single standard format. For example, this layer maps multiple disparate legacy feeds of credit bureau data into a consolidated credit card history table. This layer integrates technical systems rather than business concepts.

- **Storage Format:** Data Vault 2.0 components: Hubs (`_hub`), Links (`_lnk`), and Satellites (`_sat`).
- **Processing Guarantee:** Cryptographic hash keys (`SHA256` stored as `BYTES`) replace vendor surrogate keys. Records load with audit timestamps (`load_ts`) and record source tags (`record_source_cd`).
- **Partitioning and Clustering:** Partitioned by ingest date (`load_dt`). Clustered by primary hash keys (`customer_hk`).
- **Engine Optimization:** Clustered hash keys prevent costly full-table scans during multi-satellite joins.

### 2.4 Layer 4: Analytical (`04_analytical` / `04_anl`)

The analytical layer delivers conformed enterprise star schemas and domain abstraction views. In this tier, cross-entity joins occur to build unified business concepts, such as merging internal account ledgers with conformed bureau records to create comprehensive customer financial health profiles.

- **Storage Format:** Kimball dimensional stars (`_dim`, `_fact`, `_agg`) and denormalized One Big Table structures.
- **Processing Guarantee:** Enforces business consistency, referential integrity, and conformed dimensional hierarchies.
- **Shielding Downstream Consumers:** The domain layer isolates downstream machine learning applications from upstream vendor schema changes. When vendors alter payload formats, engineers modify raw-to-domain mappings without breaking downstream feature extractors.
- **Feature Engineering Baseline:** Serves as the primary source for analytical queries and feature engineering pipelines.

### 2.5 Feature Store (`05_feature` / `05_fea` / `05_feat`)

The feature layer computes standardized mathematical aggregations, rolling statistical signals, and categorical encodings for machine learning models. Feature extractors consume conformed analytical tables to ensure parity between offline training and online serving.

- **Storage Format:** Entity-keyed wide tables and structured feature vectors (`ARRAY<FLOAT64>`).
- **Processing Guarantee:** Deterministic calculations computed across fixed sliding windows (`rolling_30d_spend_amt`, `count_swipe_7d_qty`). Shared transformation logic eliminates training-serving skew.
- **Model Stacking Receptor:** This layer accepts upstream model predictions from `07_inference` to enable multi-stage model stacking.
- **Partitioning and Clustering:** Partitioned by feature calculation date (`feature_dt`). Clustered by entity identifier (`customer_id`).

### 2.6 Model Training (`06_training_set` / `06_trn`)

The training set layer stores frozen, immutable data matrices used to fit supervised and unsupervised machine learning algorithms. Every training set aligns historical feature observations with subsequent label outcomes.

- **Storage Format:** Static, unpartitioned or snapshot-partitioned tables pairing features with explicit target labels (`_lbl`).
- **Point-in-Time Correctness:** Feature vectors join to label observations using historical timestamps to eliminate lookahead bias and data leakage.
- **Strict Ingestion Boundary:** Training sets must not join directly from operational prediction logs or `07_inference`. For model stacking architectures, input predictions must first be standardized within `05_feature`.
- **Processing Guarantee:** Read-only upon creation. Training matrices are retained across model lifecycles to support regulatory audit compliance.

### 2.7 Model Inference (`07_inference` / `07_inf`)

The inference layer logs all predictions, probability distributions, risk deciles, and model scores generated by deployed models. It supports both batch scoring jobs and real-time streaming inference pipelines.

- **Storage Format:** Append-only prediction ledgers containing entity keys, model version identifiers, prediction scores, and execution timestamps.
- **Processing Guarantee:** Idempotent appends keyed on `(entity_id, model_version_id, scoring_ts)`.
- **Partitioning and Clustering:** Partitioned by scoring date (`scoring_dt`). Clustered by model identifier and entity key (`model_id`, `customer_id`).
- **Lineage Loop:** Upstream feature pipelines in `05_feature` ingest these prediction logs when stacking complex risk models.

### 2.8 Observability and Metrics (`08_metrics` / `08_met`)

The metrics layer tracks data pipeline health, data quality pass rates, and statistical model drift. It provides automated alerts when incoming data distributions diverge from training baselines.

- **Storage Format:** Aggregated statistical summaries containing null rates, standard deviations, quantile boundaries, and Population Stability Index scores.
- **Processing Guarantee:** Continuous telemetry aggregation. Heavy operational tables roll up into lightweight monitoring views.
- **Partitioning and Clustering:** Partitioned by metric computation date (`metric_dt`). Clustered by asset identifier and metric type.

---

## 3. Physical Storage and Query Optimization Guidelines

BigQuery architecture separates storage allocation on Colossus from distributed Borg slot compute. High-performance queries depend on physical layout optimization across Capacitor column stripes.

### 3.1 Partitioning Strategies by Layer

Partitioning divides large tables into discrete segments based on a date, timestamp, or integer range column. The table below lists partitioning standards across platform layers.

| Layer Code | Recommended Partition Field | Partition Granularity | Ingestion Retention |
| :--- | :--- | :--- | :--- |
| `01_lnd` | `_PARTITIONTIME` (System Ingest) | Daily | 30 to 90 Days |
| `02_str` | `event_dt` (Source Event Date) | Daily | None |
| `03_int` / `03_uni` | `load_dt` (Data Vault Load Date) | Daily | None |
| `04_anl` | `transaction_dt` (Business Date) | Daily or Monthly | None |
| `05_fea` / `05_feat` | `feature_dt` (Feature Snapshot Date) | Daily | None |
| `06_trn` | `snapshot_dt` (Fixed Vintage Date) | None or Monthly | 365 Days |
| `07_inf` | `scoring_dt` (Model Execution Date) | Daily | None |
| `08_met` | `metric_dt` (Observation Date) | Daily | 730 Days |

### 3.2 Clustering Multi-Tenant Tables

Clustering sorts table data based on up to four specified columns. Capacitor co-locates rows with matching cluster keys within the same storage blocks.

1. **Ordering Matters:** Specify cluster columns in order of descending filter frequency. Place high-cardinality equality keys first (`customer_id`), followed by lower-cardinality grouping attributes (`channel_cd`).
2. **Cluster on Join Keys:** In `03_integration`, cluster tables on cryptographic hash keys (`_hk`). In `04_analytical`, cluster fact tables on primary dimensional foreign keys.
3. **Avoid Over-Clustering:** Do not cluster low-volume lookup tables containing fewer than one gigabyte of data. Small tables fit entirely within minimal block allocations, rendering clustering ineffective.
4. **Decision Protocol:** Consult the [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) to evaluate table sizing thresholds, partition granularity, and row distribution skew.

---

## 4. Authoritative Domain Taxonomy

The data platform organizes datasets across ten core business domains. The table below establishes canonical domain and subdomain boundaries.

| Domain Identifier | Subdomain Identifier | Description and Core Assets |
| :--- | :--- | :--- |
| `core_banking` | `identity` | Customer Master Data Management (MDM), KYC onboarding funnels, biometrics |
| `core_banking` | `ledger` | Checking accounts (Conta Corrente), balances, currency ledgers |
| `core_banking` | `open_finance` | Inbound consent telemetry and outbound regulatory APIs |
| `core_banking` | `reference_data` | Global business lookups, ISO currency codes, clearing calendars |
| `payments` | `pix` | Instant payment clearing, QR engines, peer-to-peer transfers |
| `payments` | `transfers` | Legacy wire transfers (TED, DOC) and bank slip clearing (Boletos) |
| `payments` | `acquiring` | Point-of-Sale (POS) terminal telemetry, merchant payment links |
| `lending` | `cards` | Card account ledgers, authorizations, disputes, monthly statements |
| `lending` | `loans` | Personal credit lines, overdraft loans, consigned payroll debt |
| `lending` | `financing` | Vehicle financing, collateral liens, home equity credit |
| `lending` | `recovery` | Delinquent recovery, renegotiation agreements, debt charge-offs |
| `credit` | `scoring` | Default probability models (PD), behavioral credit scoring, limit inference |
| `credit` | `provisioning` | Expected Credit Loss models (BACEN Resolution 2682, IFRS9 retail and corporate) |
| `risk` | `credit_risk` | Probability of Default (PD), behavioral limits, exposure inference |
| `risk` | `regulatory_risk`| Central Bank risk provisioning (BACEN Resolution 2682, IFRS9 models) |
| `external_data` | `bureau` | Credit bureau scores and negative registries (Serasa, Boa Vista) |
| `external_data` | `regulatory` | Brazilian Central Bank SCR feeds, Federal Revenue company records |
| `external_data` | `market_clearing`| Interbank clearing settlements (CIP, B3, Anbima market feeds) |
| `fraud_prevention`| `transactional` | Real-time transaction fraud scoring engines (Pix, Card Swipes) |
| `fraud_prevention`| `identity_fraud` | Account takeover protection, synthetic identity detection |
| `fraud_prevention`| `aml` | Anti-Money Laundering monitoring, Politically Exposed Persons (PEP) |
| `crm` | `customer_care` | Support tickets, contact center interactions, customer sentiment |
| `crm` | `engagement` | Contact policy rules, message fatigue prevention models |
| `marketing` | `campaigns` | Conversion attribution, push notification delivery funnels |
| `marketing` | `customer_intel` | Cross-sell propensity models, churn prediction, Next Best Offer |
| `ml_platform` | `data_quality` | Lake ingestion tracking, column completeness, anomaly monitors |
| `ml_platform` | `model_ops` | Prediction drift trackers, model stability metrics, calibration monitors |

---

## 5. Related References and Operational Tooling

- **Naming Conventions:** Consult [Naming Conventions Specification](naming_conventions.md) for identifier grammar and layer code tokens.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for tier-specific physical layouts.
- **Storage Architecture:** Consult [Storage and Capacitor Architecture](storage_and_capacitor.md) for columnar physical layouts.
- **Metadata Management:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for FinOps taxonomy and policy tags.
