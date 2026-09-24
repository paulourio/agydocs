# Data Platform Naming Conventions and Lexicon Specification

This specification establishes the canonical naming standards for Google Cloud BigQuery datasets, tables, views, columns, and workflow tasks. It formalizes a unified grammar across Data Vault 2.0, Kimball dimensional modeling, and Machine Learning Feature Stores. Consistent names simplify catalog search, prevent operational drift, and ensure reliable data lineage tracking across domains. Names matter. When multiple engineering squads query shared analytical datasets simultaneously, standard prefixes ensure that engineers locate authoritative upstream tables without inspecting raw SQL definitions or pipeline source code.

---

## 1. Resource Hierarchy

BigQuery organizes analytical assets within a three-tier namespace. Every data object resides within an explicit Google Cloud project and dataset boundary.

$$\underbrace{\text{project\_id}}_{\text{Google Cloud Project}} \cdot \underbrace{\text{dataset\_id}}_{\text{Domain, Subdomain, and Layer}} \cdot \underbrace{\text{table\_id}}_{\text{Entity or Product Asset}}$$

```text
+---------------------------------------------------------------------------------+
| Google Cloud Project: mybank-analytics-prod                                     |
|  |                                                                              |
|  +-- Dataset: lend_card_04_anl                                                  |
|       |                                                                         |
|       +-- Table: statement_payment_fact                                         |
|       +-- Table: card_account_dim                                               |
|       +-- View:  active_cardholders_vw                                          |
+---------------------------------------------------------------------------------+
```

All identifiers must use lowercase alphanumeric characters separated by single underscores (`snake_case`). Hyphens, uppercase characters, and special symbols are prohibited in dataset and table names. Uniform casing rules ensure reliable execution across SQL engines, schedulers, and metadata catalogs. Standards prevent silent failures.

---

## 2. Dataset Naming Conventions

Dataset identifiers delineate data ownership boundaries and data lifecycle tiers. Every dataset identifier adheres to a standard three-part structure.

$$\langle\text{domain}\rangle\_\langle\text{subdomain}\rangle\_\langle\text{layer\_code}\rangle$$

### 2.1 Layer Codes

The layer code indicates the lifecycle stage and processing guarantees of the underlying tables. The table below lists all approved layer codes and their target architectures.

| Layer Code | Lifecycle Layer | Description | Target Modeling Pattern |
| :--- | :--- | :--- | :--- |
| `01_lnd` | `01_landing` | Immutable raw ingest payloads and external drops | Append-only raw schemas, vendor formats |
| `02_str` | `02_structured` | Type-cast, schema-validated source mirrors | Denormalized records, native data types |
| `03_int` / `03_uni` | `03_integration` / `03_unified` | Conformed cross-system integration tier | Data Vault 2.0 (Hubs, Links, Satellites) |
| `04_anl` | `04_analytical` | Enterprise star schemas and conformed entities | Kimball Facts, Dimensions, Aggregates |
| `05_fea` / `05_feat` | `05_feature` | Standardized, reusable machine learning features | Wide feature matrices, entity-keyed arrays |
| `06_trn` | `06_training_set`| Point-in-time frozen snapshots for model training| Immutable training matrices with labels |
| `07_inf` | `07_inference` | Model prediction outputs and score logs | Append-only model scorecards, probabilities|
| `08_met` | `08_metrics` | Pipeline telemetry, drift metrics, and audit summaries | Aggregated drift stats, SLA tracking tables|

### 2.2 Canonical Dataset Examples

Production datasets reflect business domain ownership and lifecycle progression. Each layer maintains strict physical boundaries.
- Dataset `core_ident_02_str` stores cleaned and cast identity records from onboarding funnels.
- Dataset `pay_pix_03_uni` contains Data Vault 2.0 hub, link, and satellite tables for instant clearing.
- Dataset `lend_card_04_anl` holds star schema dimensional tables covering card statements and billed charges.
- Dataset `risk_scoring_05_feat` provides curated behavioral features for credit exposure models.
- Dataset `frd_trx_07_inf` maintains production inference scores for real-time transactions.

---

## 3. Table Naming Conventions

Table naming follows two distinct paradigms depending on whether the asset belongs to Data Engineering or Data Science.

### 3.1 Entity-First Naming (Layers `01_lnd` through `04_anl`)

Tables representing core operational entities, master ledgers, transactions, or conformed business concepts start with the primary business entity. The entity token anchors the table within the operational domain. Entities govern pipelines.

$$\langle\text{entity}\rangle\_\langle\text{context}\rangle\_\langle\text{suffix}\rangle$$

Entity-first naming clusters related business records in alphabetical listings. The naming pattern applies uniformly across operational layers.

```text
-- Pattern components:
-- [entity]   : Primary business concept (customer, card, statement, loan, contract).
-- [context]  : Business operation or relationship qualifier (kyc, billing, payment).
-- [suffix]   : Modeling pattern and asset type (dim, fact, hub, sat, jnl, doc).

-- Canonical production examples:
`mybank-prod.lend_card_02_str.statement_jnl`
`mybank-prod.pay_pix_03_uni.transfer_jnl`
`mybank-prod.core_ident_04_anl.customer_kyc_fact`
`mybank-prod.lend_card_04_anl.statement_payment_fact`
`mybank-prod.lend_loan_03_uni.contract_doc`
`mybank-prod.lend_recv_04_anl.settlement_agreement_fact`
`mybank-prod.frd_aml_04_anl.suspicious_activity_fact`
```

### 3.2 Product-First Naming (Layers `05_fea` through `08_met`)

Tables representing machine learning feature pipelines, statistical inference engines, or monitoring systems start with the model product or action. In analytical layers, consumers locate tables by model family rather than upstream source entities. Models are products.

$$\langle\text{product/action}\rangle\_\langle\text{context}\rangle\_\langle\text{suffix}\rangle$$

Product-first naming keeps downstream scoring outputs and training snapshots isolated from upstream schema updates. When source engineers alter upstream operational tables, dedicated feature extractors shield downstream statistical models from breaking contract changes.

```text
-- Pattern components:
-- [product/action] : Machine learning system, model, or task (cadpos, scorecard, churn).
-- [context]        : Feature window, target concept, or architecture (behavior, default).
-- [suffix]         : Machine learning artifact type (feat, mtx, lbl, pred, met).

-- Canonical production examples:
`mybank-prod.risk_scoring_05_feat.cadpos_behavior_feat`
`mybank-prod.risk_scoring_06_trn.cadpos_embedding_mtx`
`mybank-prod.risk_scoring_06_trn.bacen_default_lbl`
`mybank-prod.credit_scoring_07_inf.credit_pf_app_v5_pred`
`mybank-prod.risk_monitoring_08_met.scorecard_behavioral_psi_met`
```

---

## 4. Definitive Suffix Dictionary

Every table, view, and materialized view must conclude with an approved suffix indicating its structural schema archetype. Explicit suffixes eliminate ambiguity during automated query parsing and catalog indexing. Suffixes define contracts.

### 4.1 Operational, Logging, Staging, and Document Suffixes (Layers `01` and `02`)

Operational suffixes designate raw ingestion assets, pipeline logs, unstructured documents, and transient intermediate staging tables. The table below lists each suffix and its functional purpose.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_raw` | Raw Payload | Untouched JSON or binary blobs stored directly from APIs | `bureau_gateway_equifax_raw` |
| `_rec` | Source Record | Structured source record mapped 1:1 to external provider schemas | `crivo_bank_operation_rec` |
| `_jnl` | Journal / Ledger | Append-only, immutable sequence of business state changes | `statement_jnl`, `transfer_jnl` |
| `_snp` | Snapshot | Full periodic extract dump sent by vendors regardless of delta status | `cadpos_bvs_weekly_snp` |
| `_bat` | Delta Batch | Periodic delta batch containing inserted or updated source records | `bacen_scr_monthly_bat` |
| `_stg` | Staging Table | Ephemeral pipeline intermediate table with an automatic expiration | `df_primary_stg` |
| `_log` | Pipeline Log | Operational execution logs, pipeline traces, or API audit histories | `crivo_bank_operation_log` |
| `_err` | Dead-Letter Table | Records failing schema validation, type parsing, or quality gates | `cadpos_bvs_api_err` |
| `_doc` | Document Store | Unstructured or semi-structured payload capturing document artifacts | `contract_doc` |

### 4.2 Data Vault 2.0 Suffixes (Layer `03_int` / `03_uni`)

Integration layer assets model enterprise relationships using Data Vault 2.0 primitives. The table below specifies all valid integration suffixes.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_hub` | Hub | Unique business keys, surrogate hash keys, and first-load timestamps | `customer_hub` |
| `_lnk` | Link | Unique associations and transactions connecting two or more Hubs | `customer_loan_lnk` |
| `_sat` | Satellite | Contextual descriptive attributes and temporal validity windows | `customer_address_sat` |
| `_hlnk` / `_hlink` | Hierarchical Link| Recursive parent-child relationships within the same Hub entity | `geo_region_hlnk` |
| `_sal` / `_salnk` | Same-As Link | Cross-system key resolution mapping duplicates to a single entity | `customer_dedup_sal` |
| `_esat` | Effectivity Sat | Tracks temporal validity and relationship active dates on Links | `account_signatory_esat` |
| `_masat`| Multi-Active Sat| Handles multiple active contextual rows for a Hub on the same timestamp | `loans_masat` |
| `_nhlnk`| Non-Historized Lnk| Immutable high-volume transactional events without temporal tracking | `card_trx_event_nhlnk` |
| `_pit` | Point-in-Time | Query optimization join helper table aligning Satellite validity spans | `customer_bureau_pit` |
| `_explnk`| Exploration Link | Ad-hoc hypothesis link joining entities during analytical discovery | `customer_churn_explnk` |

### 4.3 Kimball Dimensional Suffixes (Layer `04_anl`)

Analytical marts represent conformed business dimensions and additive historical event facts. The table below lists all dimensional suffixes.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_dim` | Dimension | Conformed business context containing SCD Type 1 or Type 2 attributes | `customer_dim` |
| `_fact` | Fact Table | Measurable business metrics tied to a temporal foreign key coordinate | `statement_payment_fact` |
| `_agg` | Aggregate Fact | Pre-calculated rollups and multi-dimensional metric summaries | `monthly_spend_agg` |
| `_brdg` / `_bridge`| Bridge Table | Resolves many-to-many relationships where nested arrays are unsuitable | `customer_account_brdg` |
| `_hist` | Entity History | Explicit row-level state change ledger tracking entity lifecycles | `credit_limit_hist` |

### 4.4 Machine Learning and Feature Store Suffixes (Layers `05` through `07`)

Data science assets store engineered model features, vectorized arrays, and historical evaluation targets. The table below details these model artifacts.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_feat` / `_fea` | Feature Group | Human-interpretable mathematical aggregations and signals | `cadpos_behavior_feat` |
| `_mtx` | Feature Matrix | Fully encoded, normalized numerical array formatted for model input | `cadpos_embedding_mtx` |
| `_lbl` | Training Label | Isolated ground-truth binary or continuous target for supervised tasks | `bacen_default_lbl` |
| `_pred`| Prediction Log | Model inference outputs, probabilities, deciles, and shapley values | `credit_pf_app_v5_pred` |

### 4.5 Reference and Master Data Suffixes

Enterprise master data tables provide shared lookup codes and cross-system mappings. The table below outlines master data types.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_lkp` | Lookup Table | Static dictionary mapping codes to descriptions | `mcc_category_lkp` |
| `_ref` | Reference Data | Enterprise-wide regulatory tables, master calendars, or currencies | `brazilian_calendar_ref` |
| `_map` | Mapping Table | Cross-reference table translating external vendor IDs to internal IDs | `cadpos_bvs_to_nuclea_map` |

### 4.6 Views and Pipeline Control Suffixes

Virtual relations and pipeline state markers utilize explicit administrative suffixes. The table below lists these control objects.

| Suffix | Asset Type | Description | Canonical Example |
| :--- | :--- | :--- | :--- |
| `_vw` | Logical View | Standard SQL query saved as a virtual relation executing at runtime | `active_customers_vw` |
| `_mvw` | Materialized View| BigQuery managed materialized query maintained incrementally | `cadpos_bvs_batch_input_mvw` |
| `_ctrl`| Control Table | Pipeline orchestration state tracking watermarks and partition status | `cadpos_bvs_partition_ctrl` |

---

## 5. Column and Attribute Grammar

Attribute identifiers conform to the ISO 11179 metadata standard. Each column name decomposes into three grammatical elements.

$$\text{AttributeName} := \langle\text{PrimeWord}\rangle\text{ } [\langle\text{ModifyingWord}\rangle\dots]\text{ }\langle\text{ClassWord}\rangle$$

The prime word identifies the primary business subject, such as a customer or loan account. Modifying words add domain qualifiers, such as billing or overdue. The class word must always serve as the final suffix token. By enforcing immutable class word suffixes on every column, analytical tools and downstream data pipelines deterministically infer column semantics, storage constraints, and join invariants across heterogeneous domain boundaries.

### 5.1 Business Name Grammar and Structural Rules

Every attribute name adheres to standard grammatical principles:
1. Business names use singular nouns for objects and present tense verbs for operational states.
2. Identifiers must remain self-documenting and easily distinguishable without external data dictionaries.
3. Modifying words add specific context. When `phone` modifies `customer_number`, it forms `customer_phone_number`. When `last` modifies `customer_name`, it forms `customer_last_name`.
4. Names must avoid redundant qualifications when contained within a parent struct or entity. In customer tables, declare `customer.last_name` rather than `customer.customer_last_name`.
5. When attributes span multiple business domains, include multiple prime words. For credit scorecards evaluating customers, declare `customer_credit_scorecard_score`.

### 5.2 Canonical Class Word Suffixes

Class words define the physical data category and semantic role of each attribute. The table below lists all canonical class words and their target BigQuery types.

| Category | Class Word | Recommended Data Type | Suffix | Description and Example |
| :--- | :--- | :--- | :--- | :--- |
| **Label** | Surrogate Key | `INT64`, `STRING` | `_id` | System-assigned primary or foreign key (`person_id`, `account_id`). |
| **Label** | Business Key | `STRING` | `_bk` | Natural business key from source systems (`customer_bk`, `tax_bk`). |
| **Label** | Hash Key | `BYTES`, `STRING` | `_hk` | Data Vault cryptographic hash key (`customer_hk`). |
| **Label** | Hash Difference| `BYTES`, `INT64` | `_hd` | Data Vault record change detection hash (`customer_hd`). |
| **Label** | Name | `STRING` | `_nm` | Human-readable proper name or label (`group_nm`, `merchant_nm`). |
| **Label** | Title | `STRING` | `_title`, `_ttl`| Official role or professional title (`profession_title`). |
| **Label** | Code | `STRING` | `_cd` | Standardized category code or enumeration value (`currency_cd`). |
| **Label** | Number | `STRING` | `_num` | Numeric string not used for counters or math (`phone_num`, `part_num`). |
| **Label** | Indicator | `BOOL`, `INT64`, `STRING`| `_ind` | Two-state flag (`is_active_ind`, `borrow_ind`, `ever60mob6_ind`). |
| **Chronology** | Date | `DATE` | `_dt` | Calendar date without time components (`ref_dt`, `contract_dt`). |
| **Chronology** | Time | `TIME` | `_tm` | Wall-clock time without date component (`operation_tm`). |
| **Chronology** | Timestamp | `TIMESTAMP` | `_ts` | Point in time with microsecond precision (`event_ts`, `created_ts`). |
| **Measurement**| Amount | `NUMERIC`, `FLOAT64` | `_amt` | Monetary value expressed in currency units (`loan_amt`, `order_amt`). |
| **Measurement**| Quantity | `INT64` | `_qty`, `_qt` | Count of discrete items or events (`contract_qt`, `installment_qty`). |
| **Measurement**| Proportion | `FLOAT64` | `_p` | Bounded fraction between 0.0 and 1.0 (`revolving_spend_p`, `diamonds_p`). |
| **Measurement**| Ratio | `FLOAT64`, `NUMERIC` | `_rt` | Dimensionless quotient comparing two values (`overdue_rt`, `cc_debt_rt`). |
| **Measurement**| Rate | `FLOAT64` | `_rate` | Temporal quotient across different units (`savings_growth_rate`). |
| **Measurement**| Percent | `FLOAT64`, `INT64` | `_pct` | Value scaled to a hundred-point baseline (`cc_debt_pct`). |
| **Description**| Description | `STRING` | `_desc` | Human-readable explanation of a code or state (`profession_desc`). |
| **Description**| Text | `STRING` | `_text` | Freeform unstructured notes or narrative content (`transaction_text`). |

### 5.3 Nested and Array Fields Naming Grammar

Nested structs and repeated arrays reflect hierarchical business relationships directly within BigQuery storage. The schema listing below demonstrates canonical repeated structures.

```text
-- Canonical nested and array field declarations:
probs                      ARRAY<FLOAT64>
operations                 ARRAY<STRUCT<op_nm STRING, created_ts TIMESTAMP>>
embedding_vec              ARRAY<FLOAT64>
predicted_distr            ARRAY<STRUCT<outcome_nm STRING, prob_p FLOAT64>>
spending_summary           ARRAY<STRUCT<industry_nm STRING, tot_amt NUMERIC>>
product_usage_index_arr    ARRAY<FLOAT64>
```

Field naming within nested records adheres to strict scoping rules:
1. Array attributes use collective nouns or plural terminology (`operations`, `probs`).
2. Vector embeddings representing dense numerical coordinate spaces conclude with the `_vec` token (`embedding_vec`).
3. Discrete probability distributions conclude with the `_distr` token (`predicted_distr`).
4. The generic token `arr` represents a fallback class word. Engineers must avoid using `_arr` when a more descriptive semantic class word is available.
5. Nested struct elements follow standard ISO 11179 grammar for their individual column leaves (`op_nm`, `created_ts`, `tot_amt`).

### 5.4 Mathematical Foundations: Proportion, Ratio, and Rate

Analytical feature pipelines distinguish strictly between proportions, ratios, and rates. Precise naming prevents conceptual confusion during statistical modeling.
- **Proportion (`_p`):** A proportion represents a fraction of a whole. Its value is strictly bounded between $0.0$ and $1.0$. For example, in a standard deck of 52 playing cards containing 13 diamonds, the proportion of diamonds is calculated as $13 / 52 = 0.25$, yielding attribute `diamonds_p`.
- **Ratio (`_rt`):** A ratio represents the relative magnitude of two measurements sharing the same unit of measurement. For example, comparing 13 diamond cards to 13 heart cards yields a 1:1 relationship, resulting in numeric feature value $1.0$ named `diamond_hearts_rt`. Similarly, dividing current debt by total income produces `debt_to_income_rt`.
- **Rate (`_rate`):** A rate represents a quotient where numerator and denominator use different units of measurement, or where a measurement changes across elapsed time. For example, computing annual balance changes across consecutive years produces `savings_growth_rate`.

### 5.5 Expanded Mathematical and Statistical Feature Modifiers

Machine learning feature groups use standardized prefixes and suffixes to define transformations. These tokens ensure consistency across offline training sets and online feature stores. The table below summarizes these mathematical modifiers.

| Concept | Token | Placement | Example |
| :--- | :--- | :--- | :--- |
| **Logarithmic Transformation** | `log1p` | Prefix | `log1p_annual_revenue_amt` |
| **Array Structure** | `arr` | Suffix | `product_usage_index_arr` |
| **Average / Mean** | `avg` | Modifier | `avg_transaction_amt_30d` |
| **Distribution** | `distr` | Suffix | `predicted_outcome_distr` |
| **Entropy** | `entropy`, `s` | Modifier | `spend_category_entropy` |
| **Error Term** | `err` | Modifier | `prediction_residual_err` |
| **Frequency** | `freq` | Modifier | `monthly_swipe_freq` |
| **Herfindahl Index** | `hhi` | Suffix | `merchant_spend_hhi` |
| **Maximum** | `max` | Modifier | `max_overdue_days_qty` |
| **Minimum** | `min` | Modifier | `min_credit_balance_amt` |
| **Multiplier** | `mult` | Modifier | `credit_limit_mult` |
| **Percentage Points** | `pp` | Suffix | `interest_delta_pp` |
| **Percentile Rank** | `prank` | Suffix | `customer_spend_prank` |
| **Percentile Boundary** | `p00` - `p99` | Suffix | `transaction_amt_p95` |
| **Quantile Boundary** | `q0000` - `q9999`| Suffix | `revenue_quantile_q0500` |
| **Quantile Bucket** | `ntile` | Suffix | `risk_propensity_ntile` |
| **Quantile Rank** | `qrank` | Suffix | `credit_exposure_qrank` |
| **Rank** | `rank` | Suffix | `merchant_volume_rank` |
| **Square Root** | `sqrt` | Prefix | `sqrt_merchant_count_qty` |
| **Standard Deviation** | `std` | Modifier | `std_daily_spend_amt` |
| **Total / Sum** | `tot`, `sum` | Modifier | `tot_revolving_interest_amt` |
| **Vector Embedding** | `vec` | Suffix | `customer_embedding_vec` |
| **Trend Slope** | `trend`, `tr` | Suffix | `monthly_spend_trend` |
| **Z-Score Normalization** | `zscore`| Suffix | `customer_spend_zscore` |

### 5.6 Temporal Windowing, Offsets, and the Anti-Over-Specification Principle

Features computed across sliding lookback windows use standard temporal tokens. The table below lists the approved window specifications.

| Token | Semantic Window Definition | Example |
| :--- | :--- | :--- |
| `7d` | Trailing 7 calendar days | `tot_swipe_count_7d_qty` |
| `30d` | Trailing 30 calendar days | `tot_billing_amt_30d` |
| `90d` | Trailing 90 calendar days | `max_dpd_90d_qty` |
| `p6m` | Past 6 calendar months excluding current day | `avg_monthly_balance_p6m_amt` |
| `p12m` | Past 12 calendar months | `tot_chargeback_qty_p12m` |
| `mobXX` | Months on Book vintage index | `default_overdue90_mob6_ind` |
| `mXX` | Offset back $XX$ months in the past ($M-XX$) | `card_limit_utilization_m2_rt` |
| `mpXX` | Offset forward $XX$ months in the future ($M+XX$) | `target_balance_mp6_amt` |
| `pXXm_mYY` | Previous $XX$ months evaluated $YY$ months ago | `avg_spend_p6m_m12_amt` |

Feature naming must balance precision against readability:
1. **Omit Redundant Context:** When all features within a training matrix share identical observation offsets, omit repetitive offset tokens from attribute names.
2. **Prevent Operation Chaining:** Avoid compounding multiple transformations into unreadable identifiers. An attribute named `cc_debt_avg_p6m_m8_p6m_m2_rt` obscures business meaning. Replace compounded identifiers with clear business terms such as `cc_debt_term_tr` or `cc_debt_term_rt`, documenting mathematical specifics in column metadata options.

### 5.7 System-Driven Audit Columns

System columns provide immutable pipeline traceability and change detection across operational tiers. The table below outlines standard audit columns.

| Column Name | BigQuery Data Type | Description |
| :--- | :--- | :--- |
| `_hk` | `BYTES` / `STRING` | Data Vault cryptographic hash key representing business identity. |
| `_hd` | `BYTES` / `INT64` | Data Vault hash difference token tracking descriptive changes. |
| `load_ts` | `TIMESTAMP` | Canonical timestamp when record was ingested into BigQuery. |
| `load_dt` | `DATE` | Ingestion calendar date used for physical partition pruning. |
| `load_end_ts` | `TIMESTAMP` | Historical validity closing timestamp in SCD Type 2 tables. |
| `load_end_dt` | `DATE` | Historical validity closing calendar date. |
| `record_source` | `STRING` | Source system or pipeline identifier responsible for record creation. |
| `snapshot_ts` | `TIMESTAMP` | Point-in-time timestamp of vendor periodic extract. |
| `snapshot_dt` | `DATE` | Calendar date of vendor periodic extract. |
| `update_ts` | `TIMESTAMP` | Timestamp when existing row was last modified in place. |

### 5.8 Credit Bureaux Abbreviation Dictionary

External bureau integrations adhere to standard institutional abbreviations. The table below lists canonical bureau tokens.

| Full Institutional Entity | Token | Description |
| :--- | :--- | :--- |
| **Bacen SCR** | `scr` | Sistema de Informações de Crédito do Banco Central. |
| **Banco Central do Brasil** | `bc` | Brazilian Central Bank regulatory agency. |
| **Boa Vista SCPC** | `bvs` | Boa Vista consumer credit bureau. |
| **Receita Federal do Brasil** | `srf` | Brazilian Federal Revenue Department. |
| **Cadastro Positivo** | `pcpo` | Brazilian positive credit history framework. |
| **Serasa Experian** | `srs` | Serasa credit bureau records and scorecards. |

### 5.9 Banking and Credit Operations Abbreviation Dictionary

Financial products and banking operations use concise domain abbreviations. The table below details authorized banking terms.

| Banking Term | Token | Banking Term | Token |
| :--- | :--- | :--- | :--- |
| **Account** | `acct` | **Accrual** | `accr` |
| **Adjustment** | `adj` | **Advance** | `adv` |
| **Available Limit** | `avail_lim` | **Balance** | `bal` |
| **Borrower** | `borrow` | **Borrowing Limit** | `borrow_lim` |
| **Closed-End Loan** | `cls` | **Consolidation** | `cnsld` |
| **Consortium / Consórcio** | `cons` | **Credit Card** | `cc` |
| **Currency** | `ccy` | **Financing** | `fin` |
| **Future Balance** | `fut` | **Limit** | `lim` |
| **Mortgage** | `mort` | **Origination** | `org` |
| **Overdraft / Cheque Especial**| `od` | **Payment** | `pmt` |
| **Payroll Loan / Consignado** | `prl` | **Personal Loan** | `pl` |
| **Prepayment** | `ppmt` | **Revolving Credit** | `rev` |
| **Term** | `trm` | **Utilization Index** | `ui` |
| **Value at Risk** | `var` | **Vehicle Financing** | `vh` |
| **Working Capital Loan** | `wc` | **Total / Sum** | `tot` |

### 5.10 Application-Agnostic Abbreviation Dictionary

General data engineering pipelines use standardized abbreviations across administrative and operational scopes. The table below lists these common tokens.

| Full Term | Token | Full Term | Token |
| :--- | :--- | :--- | :--- |
| **Pessoa Jurídica (Corporate)**| `pj` | **Pessoa Física (Individual)** | `pf` |
| **Address** | `addr` | **Categorical Variable** | `cat` |
| **Customer** | `cust` | **Detail** | `dtl` |
| **Dimension** | `dim` | **End of Period** | `eop` |
| **Frequency** | `freq` | **History** | `hist` |
| **Message** | `msg` | **Number** | `num` |
| **Option** | `opt` | **Source** | `src` |
| **Status** | `stat` | **Temporary** | `temp` |
| **Value** | `val` | **Description** | `desc` |

---

## 6. Orchestration Task and DAG Naming

Workflow tasks in Cloud Composer and Airflow must reflect their position in the data lifecycle. Every task identifier adheres to an explicit four-part structure.

$$\langle\text{verb}\rangle\_\langle\text{domain}\rangle\_\langle\text{subdomain}\rangle\_\langle\text{product\_or\_asset}\rangle$$

The task verb denotes the physical operation executed during pipeline execution. The table below details authorized verbs across each layer.

| Lifecycle Layer | Authorized Verbs | Prohibited Verbs | Purpose and Example |
| :--- | :--- | :--- | :--- |
| `01_landing` | `ingest`, `extract`, `fetch` | `clean`, `transform` | Ingesting untouched vendor drops (`ingest_ext_bur_bvs_scorename`). |
| `02_structured` | `parse`, `clean`, `transform`, `denorm`, `map`, `flatten`, `cast`, `structure` | `merge`, `join` | Schema validation and native typing (`denorm_core_ident_kyc_crivo_bank`). |
| `03_integration` | `unify`, `merge`, `resolve`, `reconcile`, `dedup` | `calc`, `aggregate` | Resolving multi-vendor source tables (`unify_reg_bacen_scr2`). |
| `04_analytical` & `05_feature` | `build`, `dim`, `fact`, `aggregate`, `agg`, `calc`, `extract_fea`, `compute_fea` | `infer`, `predict` | Generating dimensional models and feature sets (`build_cred_card_statement_fact`). |
| `06_training_set`| `freeze_trn`, `snapshot_trn`, `align_trn` | `predict` | Materializing point-in-time training matrices (`freeze_trn_risk_crisk_default_mob6`). |
| `07_inference` | `score`, `predict`, `train`, `infer` | `aggregate` | Running model scoring across feature tables (`score_frd_trx_pix_high_amount`). |
| `08_metrics` | `audit_drift`, `track_sla`, `evaluate` | `transform` | Computing drift statistics and telemetry (`audit_drift_risk_crisk_scorecard`). |

### 6.1 Domain and Subdomain Abbreviation Dictionary

Tasks use abbreviated tokens to constrain identifier lengths within orchestration engines. The table below lists standard abbreviations across major business units.

| Full Domain | Abbr | Full Subdomain | Subdomain Abbr | Example Task Identifier |
| :--- | :--- | :--- | :--- | :--- |
| `core_banking` | `core` | `identity` | `ident` | `parse_core_ident_kyc_events` |
| `core_banking` | `core` | `ledger` | `ledg` | `denorm_core_ledg_account_balance` |
| `payments` | `pay` | `pix` | `pix` | `unify_pay_pix_clearing_records` |
| `payments` | `pay` | `transfers` | `trf` | `ingest_pay_trf_ted_settlement` |
| `credit` | `cred` | `cards` | `card` | `build_cred_card_statement_fact` |
| `credit` | `cred` | `loans` | `loan` | `clean_cred_loan_contract_documents`|
| `risk` | `risk` | `credit_risk` | `crisk`| `compute_fea_risk_crisk_behavioral_30d`|
| `external_data`| `ext` | `bureau` | `bur` | `fetch_ext_bur_serasa_score` |
| `external_data`| `ext` | `regulatory` | `reg` | `ingest_ext_reg_bacen_scr_monthly` |
| `fraud_prevention`| `frd` | `transactional`| `trx` | `score_frd_trx_pix_high_amount` |

---

## 7. Concrete BigQuery DDL Implementation

This DDL specification illustrates the complete integration of dataset prefixes, table suffixes, and attribute class words. It provisions an analytical fact table for retail credit cards.

```sql
CREATE OR REPLACE TABLE `mybank-analytics-prod.lend_card_04_anl.statement_payment_fact`
(
  payment_id             STRING
                         NOT NULL
                         OPTIONS (description='Surrogate primary key for payment event'),
  account_id             STRING
                         NOT NULL
                         OPTIONS (description='Foreign key to card_account_dim'),
  customer_id            STRING
                         NOT NULL
                         OPTIONS (description='Foreign key to customer_dim'),
  clearing_ts            TIMESTAMP
                         NOT NULL
                         OPTIONS (description='Timestamp when clearing completed'),
  clearing_dt            DATE
                         NOT NULL
                         OPTIONS (description='Partition date of clearing event'),
  billed_amt             NUMERIC
                         NOT NULL
                         OPTIONS (description='Total monetary amount billed in BRL'),
  principal_amt          NUMERIC
                         NOT NULL
                         OPTIONS (description='Portion applied to principal balance'),
  interest_amt           NUMERIC
                         NOT NULL
                         OPTIONS (description='Portion applied to revolving interest'),
  is_late_clearing_ind   BOOL
                         NOT NULL
                         OPTIONS (description='True if clearing finished past due date'),
  clearing_channel_cd    STRING
                         NOT NULL
                         OPTIONS (description='Channel code: PIX, BOLETO, AUTO_DEBIT'),
  installment_qty        INT64
                         NOT NULL
                         OPTIONS (description='Total number of installments selected'),
  clearing_to_minimum_rt FLOAT64
                         NOT NULL
                         OPTIONS (description='Ratio of amount cleared to minimum due'),
  load_ts                TIMESTAMP
                         NOT NULL
                         OPTIONS (description='Audit timestamp when row was inserted')
)
PARTITION BY clearing_dt
  CLUSTER BY customer_id, account_id, clearing_channel_cd
OPTIONS (
  description = 'Consolidated statement payment facts for retail credit card accounts',
  labels      = [
                  ('data-layer', '04_analytical'),
                  ('data-domain', 'lending'),
                  ('data-subdomain', 'cards'),
                  ('data-product', 'card_ledger')
                ]
)
```

---

## 8. Related References and Operational Tooling

- **Data Lifecycle:** Consult [Data Architecture and Lifecycle](data_architecture_and_lifecycle.md) for layer processing guarantees.
- **Resource Tagging:** Consult [Resource Tagging and Metadata](resource_tagging_and_metadata.md) for label definitions and policy tags.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for storage optimization.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table and view provisioning syntax.
