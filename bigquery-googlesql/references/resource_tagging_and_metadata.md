# BigQuery Resource Tagging, Labeling, and Query Metadata Specification

This specification defines the standards for labeling BigQuery datasets, tables, views, and SQL query jobs. It establishes a unified metadata taxonomy for cost tracking, access control, and pipeline audits. Consistent labels allow engineering teams to monitor compute spend, enforce data privacy rules, and maintain compliance across distributed cloud environments.

---

## 1. Metadata Primitives: Labels vs Policy Tags

Google Cloud BigQuery provides distinct mechanisms for managing table and query metadata. Teams must understand the operational boundary between these primitives:

```text
+-----------------------------------------------------------------------------------+
| BigQuery Labels (Key-Value Strings)                                               |
| - Scope: Datasets, Tables, Views, Query Jobs                                      |
| - Usage: FinOps billing, cost center chargeback, inventory search, SLA tracking   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| Dataplex Policy Tags (IAM Taxonomy)                                               |
| - Scope: Table Columns / Specific Schema Fields                                   |
| - Usage: Column-level access control, dynamic data masking (CPF, Card PAN, PII)   |
+-----------------------------------------------------------------------------------+
```

Labels attach arbitrary string pairs to resources for billing and discovery. Policy tags link schema fields directly to Cloud IAM roles to enforce fine-grained access control and cryptographic data masking.

---

## 2. Canonical Label Taxonomy

Every dataset, table, view, and production query job must include standard metadata labels. Label keys use lowercase alphanumeric characters and hyphens in emitted tags (such as `data-domain`), while infrastructure manifests use underscores (such as `data_domain`).

### 2.1 Label Keys and Constraints

The table below lists all standard label keys and their validation constraints.

| Label Key | Scope | Requirement | Permitted Values / Pattern |
| :--- | :--- | :--- | :--- |
| `data-layer` | Datasets, Tables, Jobs | Required | `01_landing`, `02_structured`, `03_integration`, `04_analytical`, `05_feature`, `06_training_set`, `07_inference`, `08_metrics` |
| `data-domain` | Datasets, Tables, Jobs | Required | `core_banking`, `payments`, `external_data`, `lending`, `credit`, `crm`, `marketing`, `fraud_prevention`, `ml_platform`, `risk` |
| `data-subdomain` | Datasets, Tables, Jobs | Required | Valid subdomain token (such as `cards`, `pix`, `identity`, `credit_risk`) |
| `data-product` | Tables, Jobs | Optional | Associated product engine (such as `card_ledger`, `behavioral_scorecard`) |
| `data-classification`| Tables, Views | Required | `public`, `internal`, `confidential`, `restricted_pii` |
| `owner-team` | Datasets, Tables, Jobs | Required | Squad slug (such as `credit-data-eng`, `fraud-ml-ops`, `core-platform`) |
| `environment` | Datasets, Tables, Jobs | Required | `dev`, `staging`, `prod` |
| `cost-center` | Jobs, Datasets | Optional | Finance chargeback code (such as `cc-1042-risk`, `cc-2080-cards`) |
| `pipeline-cadence` | Tables, Jobs | Optional | `streaming`, `hourly`, `daily`, `monthly`, `ad_hoc` |

### 2.2 Enterprise Financial Taxonomy Catalog

The platform enforces a standardized domain hierarchy across analytical assets. The tables below define canonical domains, subdomains, and data products.

#### Core Banking Domain (`core_banking`)
The foundational operational tier of the bank. This domain manages master accounts, universal customer identities, and fiat ledgers.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `identity` | `kyc_onboarding` | Onboarding funnels, document optical character recognition, biometrics. |
| `identity` | `customer_profile` | Master Data Management: tax identifiers, verified addresses, contact info. |
| `identity` | `income_inference` | Statistical inference estimating individual true customer income. |
| `identity` | `revenue_inference`| Statistical models estimating corporate entity revenue. |
| `ledger` | `account_pf` | Retail checking account ledgers (*Conta Corrente PF*). |
| `ledger` | `account_pj` | Corporate business account ledgers (*Conta PJ* / MEI). |
| `ledger` | `account_global` | Multi-currency foreign exchange accounts (USD and EUR ledgers). |
| `open_finance` | `inbound_consents` | Inbound consent tokens and external banking data ingestion. |
| `open_finance` | `outbound_apis` | External consumption tracking for regulatory open finance endpoints. |
| `reference_data`| `business_lookups` | Universal lookups: merchant codes, ISO country tables, bank holidays. |

#### Payments Domain (`payments`)
High-throughput transaction clearing, messaging, and acquiring infrastructure.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `pix` | `p2p_transfers` | Standard instant payments, scheduled Pix, and copy-paste transfers. |
| `pix` | `qr_engine` | Dynamic and static QR code generation and settlement records. |
| `transfers` | `ted_doc` | Legacy interbank wire transfers and clearing logs. |
| `transfers` | `boletos` | Barcode slip issuance, clearing house files, and settlement logs. |
| `acquiring` | `pos_terminals` | Point-of-sale terminal telemetry, settlements, and merchant payouts. |
| `acquiring` | `payment_links` | E-commerce digital checkout sessions and gateway authorizations. |

#### External Data Domain (`external_data`)
Data originating outside enterprise boundaries, needed for landing and unified tables.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `bureau` | `serasa` | Serasa Experian credit bureau scores, negativations, and credit history. |
| `bureau` | `boa_vista` | Boa Vista SCPC consumer behavioral records and credit risk ratings. |
| `regulatory` | `bacen_scr` | Central Bank credit information system systemic exposure tables. |
| `regulatory` | `receita_federal` | Federal Revenue corporate registry, tax status, and CNAE codes. |
| `market_clearing`| `cip_b3_anbima` | Interbank clearing house settlement and custody transaction files. |

#### Lending and Credit Domains (`lending` and `credit`)
Operational loan lifecycles, credit cards, risk underwriting, and mathematical provisioning.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `cards` | `card_ledger` | Canonical card billing statements, charge authorizations, and payments. |
| `cards` | `card_ops` | Physical card fulfillment, dispute lifecycles, and token issuance. |
| `loans` | `personal_loans` | Unsecured personal loans and overdraft credit facilities. |
| `loans` | `payroll_loans` | Payroll-deducted consigned loans for public and private employees. |
| `financing` | `auto_loans` | Secured vehicle financing agreements and collateral tracking. |
| `financing` | `home_equity` | Residential property secured credit agreements. |
| `recovery` | `collections` | Delinquent accounts, debt collection placements, and write-offs. |
| `scoring` | `origination_scorecard`| Default probability models evaluated during account opening. |
| `scoring` | `behavioral_scorecard` | Ongoing customer limit management and dynamic risk deciles. |
| `scoring` | `collection_scoring` | Propensity models predicting recovery likelihood for past-due debts. |
| `exposure` | `limit_inference` | External limit estimation using open finance and bureau indicators. |
| `provisioning` | `ifrs9_retail` | Regulatory Expected Credit Loss models for individual portfolios. |
| `provisioning` | `ifrs9_corporate` | Regulatory Expected Credit Loss models for corporate business loans. |

#### Customer Relationship and Marketing Domains (`crm` and `marketing`)
Customer care, outbound campaigns, sales tracking, and predictive scores.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `customer_care` | `crm_tickets` | Support ticket lifecycles and customer satisfaction scoring. |
| `customer_care` | `chat_assistant` | Chatbot conversational turn logs, intent detection, and resolution. |
| `engagement` | `consent` | Customer opt-in preferences across marketing channels. |
| `engagement` | `contact_policy` | Campaign fatigue rules and outbound touch frequency caps. |
| `growth` | `campaigns` | Push notifications, email campaigns, and ad conversion tracking. |
| `customer_intel`| `churn_prediction` | Propensity models identifying customer flight risk across products. |
| `customer_intel`| `product_propensity`| Cross-sell recommendation models for financial products. |
| `customer_intel`| `next_best_offer` | Real-time banner prioritization models in mobile applications. |
| `retention` | `lifetime_value` | Long-term customer financial value projections. |

#### Fraud Prevention and Platform Domains (`fraud_prevention` and `ml_platform`)
Real-time financial crime detection, identity verification, and machine learning operations.

| Subdomain | Data Product | Operational Scope and Description |
| :--- | :--- | :--- |
| `transactional_fraud`| `pix_engine` | Real-time fraud scoring for instant payment transfers. |
| `transactional_fraud`| `card_engine` | Real-time card swipe fraud detection and authorization decisions. |
| `transactional_fraud`| `boleto_engine`| Barcode slip validation to detect fraudulent issuance. |
| `identity_fraud`| `application_fraud`| Synthetic identity and stolen tax credential detection models. |
| `identity_fraud`| `account_takeover` | Anomaly detection flagging credential stuffing and impossible travel. |
| `financial_crime`| `aml_monitoring` | Anti-Money Laundering alerts and Politically Exposed Persons screening. |
| `data_quality` | `lake_ingestion_tracker`| Data lake freshness checks, schema drift monitors, and volume stats. |
| `model_ops` | `model_monitoring` | Production drift tracking, population stability index, and calibration. |

---

## 3. Tagging Tables and Datasets

BigQuery supports label management through declarative DDL statements, command-line utilities, and infrastructure-as-code manifests.

### 3.1 Applying Labels via GoogleSQL DDL

Tables configure metadata labels inside the table options block when tables are defined. The SQL snippet below demonstrates canonical table labeling.

```sql
CREATE OR REPLACE TABLE `mybank-analytics-prod.lend_card_04_anl.statement_payment_fact`
(
  billing_id  STRING
              NOT NULL
              OPTIONS (description='Surrogate primary key'),
  customer_id STRING
              NOT NULL
              OPTIONS (description='Foreign key to customer_dim'),
  clearing_dt DATE
              NOT NULL
              OPTIONS (description='Clearing event partition date'),
  billed_amt  NUMERIC
              NOT NULL
              OPTIONS (description='Total billed amount in BRL')
)
PARTITION BY clearing_dt
  CLUSTER BY customer_id
OPTIONS (
  description = 'Consolidated statement payment facts for retail credit card accounts',
  labels      = [
                  ('data-layer', '04_analytical'),
                  ('data-domain', 'lending'),
                  ('data-subdomain', 'cards'),
                  ('data-product', 'card_ledger'),
                  ('data-classification', 'confidential'),
                  ('owner-team', 'credit-data-eng'),
                  ('environment', 'prod'),
                  ('pipeline-cadence', 'daily')
                ]
)
```

To update labels on an existing table without modifying its data or schema, execute an `ALTER TABLE` statement. The query below updates environment and classification labels.

```sql
ALTER TABLE `mybank-analytics-prod.lend_card_04_anl.statement_payment_fact`
  SET OPTIONS (
        labels = [
                   ('data-layer', '04_analytical'),
                   ('data-domain', 'lending'),
                   ('data-subdomain', 'cards'),
                   ('data-product', 'card_ledger'),
                   ('data-classification', 'restricted_pii'),
                   ('owner-team', 'credit-data-eng'),
                   ('environment', 'prod')
                 ]
      )
```

### 3.2 Applying Labels via bq CLI

The `bq` command-line tool updates table and dataset metadata directly. The command below applies domain and ownership labels to an analytical dataset.

```bash
# Update dataset metadata
bq update \
  --set_label data-domain:lending \
  --set_label owner-team:credit-data-eng \
  --set_label environment:prod \
  mybank-analytics-prod:lend_card_04_anl

# Update table metadata
bq update \
  --set_label data-classification:confidential \
  --set_label pipeline-cadence:daily \
  mybank-analytics-prod:lend_card_04_anl.statement_payment_fact
```

---

## 4. Query and Job Tagging for FinOps

Analytical queries submitted without metadata run as anonymous slot consumers. Unlabelled queries obscure compute costs and prevent fine-grained chargeback allocation. Attaching labels to every execution job ensures complete transparency across business units. Cost tracking requires labeled jobs.

### 4.1 CLI Query Labeling

The `bq query` command accepts one or more `--label` flags. The command below attaches execution metadata to a batch analytical query.

```bash
bq query \
  --use_legacy_sql=false \
  --label=data-domain:lending \
  --label=data-subdomain:cards \
  --label=data-product:card_ledger \
  --label=owner-team:credit-data-eng \
  --label=environment:prod \
  --label=pipeline_task:build_cred_card_statement_fact \
  'SELECT customer_id, SUM(billed_amt) FROM `lend_card_04_anl.statement_payment_fact` GROUP BY 1;'
```

### 4.2 Python SDK Query Job Labeling

Production applications submit BigQuery jobs using official client libraries. The Python listing below configures execution labels on a `QueryJobConfig` instance.

```python
from google.cloud import bigquery

client = bigquery.Client(project="mybank-analytics-prod")

job_config = bigquery.QueryJobConfig(
    labels={
        "data-domain": "lending",
        "data-subdomain": "cards",
        "data-product": "card_ledger",
        "owner-team": "credit-data-eng",
        "environment": "prod",
        "pipeline_task": "build_cred_card_statement_fact",
    }
)

sql = """
SELECT customer_id, SUM(billed_amt) AS total_billed
FROM `mybank-analytics-prod.lend_card_04_anl.statement_payment_fact`
WHERE clearing_dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY customer_id
"""

query_job = client.query(sql, job_config=job_config)
```

---

## 5. Metadata Auditing via System Views

Engineering leaders and FinOps analysts query BigQuery administrative views to verify compliance with tagging standards.

### 5.1 Auditing Table Labels

The `INFORMATION_SCHEMA.TABLE_OPTIONS` view captures all configuration parameters declared on tables. The query below identifies analytical tables missing mandatory domain or classification labels.

```sql
SELECT table_schema AS dataset_id,
       table_name,
       option_value AS labels_json
  FROM `mybank-analytics-prod.region-us.INFORMATION_SCHEMA.TABLE_OPTIONS`
 WHERE option_name = 'labels'
   AND table_schema LIKE '%_04_anl'
   AND NOT REGEXP_CONTAINS(option_value, r'data-domain')
 ORDER BY table_schema, table_name
```

### 5.2 Detecting Unlabelled Queries

FinOps guardrails reject queries executing without mandatory domain tags. The audit query below identifies unlabelled jobs consuming significant slot resources.

```sql
SELECT job_id,
       user_email,
       creation_time,
       ROUND(total_slot_ms / 1000.0, 2) AS slot_seconds,
       query
  FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
 WHERE creation_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
   AND job_type = 'QUERY'
   AND (
            ARRAY_LENGTH(labels) = 0
         OR NOT EXISTS(
                  SELECT 1
                    FROM UNNEST(labels)
                   WHERE key = 'data-domain'
            )
       )
 ORDER BY slot_seconds DESC
 LIMIT 50
```

---

## 6. Dataplex Policy Tags and Dynamic Data Masking

While resource labels govern cost tracking, Dataplex Policy Tags enforce column-level access controls. Policy tags define hierarchical taxonomy trees linked directly to BigQuery schema fields.

### 6.1 Policy Tag Hierarchy

Security administrators configure taxonomies within Dataplex:

```text
Taxonomy: DataSensitivity
 ├── PII
 │    ├── TaxIdentifier (CPF / CNPJ)
 │    └── ContactDetails (Email, Phone)
 └── FinancialData
      ├── CardPAN
      └── CardCVV
```

### 6.2 Applying Data Policies in Table DDL

To restrict column visibility or enable dynamic SHA-256 hash masking, attach the fully qualified data policy resource name to the column definition:

```sql
CREATE OR REPLACE TABLE `mybank-analytics-prod.lend_card_02_str.card_customer_rec`
(
  customer_id STRING
              NOT NULL
              OPTIONS (description='Surrogate customer identifier'),
  tax_bk      STRING
              NOT NULL
              OPTIONS (
                description   = 'Customer CPF natural key',
                data_policies = ['projects/mybank-prod/locations/us/dataPolicies/cpf-masking-policy']
              ),
  card_pan_bk STRING
              NOT NULL
              OPTIONS (
                description   = 'Primary Account Number',
                data_policies = ['projects/mybank-prod/locations/us/dataPolicies/pan-masking-policy']
              ),
  created_ts  TIMESTAMP
              NOT NULL
              OPTIONS (description='Record ingestion timestamp')
)
PARTITION BY DATE(created_ts)
OPTIONS (
  labels = [
             ('data-layer', '02_structured'),
             ('data-domain', 'lending'),
             ('data-subdomain', 'cards'),
             ('data-classification', 'restricted_pii'),
             ('owner-team', 'credit-data-eng')
           ]
);
```

Users lacking the Fine-Grained Reader role on the policy tag cannot inspect plaintext values. BigQuery automatically replaces sensitive strings with null values, hashed digests, or masked tokens according to configured data masking rules.

> **API Representation:** BigQuery REST API and client libraries represent column policy tags in `schema.fields[].policyTags.names`. Within GoogleSQL DDL statements, attach masking rules with `data_policies` or configure policy tags through the Cloud Console, BigQuery CLI (`bq update`), or Terraform.

---

## 7. Related References and Operational Tooling

- **Naming Conventions:** Consult [Naming Conventions Specification](naming_conventions.md) for domain taxonomy and prefix definitions.
- **Data Lifecycle:** Consult [Data Architecture and Lifecycle](data_architecture_and_lifecycle.md) for tier classification tags.
- **Partitioning and Clustering:** Consult [Partitioning and Clustering Guide](partitioning_and_clustering_guide.md) for storage optimization.
- **DDL Specifications:** Consult [DDL Reference](ddl_reference.md) for table and view provisioning syntax.
