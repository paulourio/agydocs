# BigQuery JSON Schema Templates and Physical Definitions

This document provides JSON schema definitions conforming to the BigQuery `TableFieldSchema[]` specification. It supplies templates for primitive types, nested structs, repeated arrays, policy tags, and partitioning.

```json
[
  {
    "name": "entity_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Primary UUID key"
  },
  {
    "name": "created_at",
    "type": "TIMESTAMP",
    "mode": "REQUIRED"
  }
]
```

---

## 1. Canonical Schema Specification (`TableFieldSchema[]`)

BigQuery tools serialize schemas as JSON field arrays:

| Field Property | JSON Type | Allowed Values | Semantic Definition |
| :--- | :--- | :--- | :--- |
| **`name`** | String | 1–128 characters | Identifier name (must match `[a-zA-Z_][a-zA-Z0-9_]*`). |
| **`type`** | String | Standard BigQuery Types | `STRING`, `BYTES`, `INTEGER` (`INT64`), `FLOAT` (`FLOAT64`), `NUMERIC`, `BIGNUMERIC`, `BOOLEAN` (`BOOL`), `TIMESTAMP`, `DATE`, `TIME`, `DATETIME`, `GEOGRAPHY`, `RECORD`, `JSON`, `RANGE`. |
| **`mode`** | String | `NULLABLE`, `REQUIRED`, `REPEATED` | Column cardinality (defaults to `NULLABLE` if omitted). |
| **`description`** | String | Up to 16,384 characters | Human documentation attached to column metadata. |
| **`fields`** | Array | Array of `TableFieldSchema` | Recursive definitions active when `type="RECORD"`. |
| **`policyTags`** | Object | `{"names": ["projects/..."]}` | Column-level security taxonomies for fine-grained IAM masking. |
| **`defaultValueExpression`** | String | SQL literal or expression | Expression providing default values (such as `GENERATE_UUID()`). |
| **`roundingMode`** | String | Rounding rule | Rounding strategy for numeric types: `ROUND_HALF_AWAY_FROM_ZERO` or `ROUND_HALF_EVEN`. |

---

## 2. Production Schema Template: Nested Telemetry Records

The JSON listing below defines a telemetry schema with nested repeated structs and column policy tags:

```json
[
  {
    "name": "event_id",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Canonical UUIDv4 event identifier"
  },
  {
    "name": "event_timestamp",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "UTC timestamp of event creation"
  },
  {
    "name": "tenant_id",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "Organizational tenant identifier used as primary clustering key"
  },
  {
    "name": "user_id",
    "type": "INTEGER",
    "mode": "NULLABLE",
    "description": "Internal customer identifier"
  },
  {
    "name": "event_type",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Categorical event classification (e.g. LOGIN, CHECKOUT)"
  },
  {
    "name": "payload",
    "type": "JSON",
    "mode": "NULLABLE",
    "description": "Semi-structured schema-less operational payload"
  },
  {
    "name": "line_items",
    "type": "RECORD",
    "mode": "REPEATED",
    "description": "Repeated line-item structures representing order items",
    "fields": [
      {
        "name": "item_id",
        "type": "STRING",
        "mode": "REQUIRED",
        "description": "Unique SKU identifier"
      },
      {
        "name": "quantity",
        "type": "INTEGER",
        "mode": "REQUIRED"
      },
      {
        "name": "unit_price",
        "type": "NUMERIC",
        "mode": "REQUIRED",
        "roundingMode": "ROUND_HALF_AWAY_FROM_ZERO"
      },
      {
        "name": "tags",
        "type": "STRING",
        "mode": "REPEATED",
        "description": "Classification tags attached to line item"
      }
    ]
  },
  {
    "name": "user_email",
    "type": "STRING",
    "mode": "NULLABLE",
    "description": "Personally identifiable email address masked by Data Catalog",
    "policyTags": {
      "names": [
        "projects/enterprise-security/locations/us/taxonomies/10928374/policyTags/99887766"
      ]
    }
  }
]
```

---

---

## 3. Incremental Merge Target Schema Template

Target tables maintained via recurrent partition merges must declare audit columns (`load_ts`, `update_ts`, `data_hd`). The listing below provides the canonical JSON schema array:

```json
[
  {
    "name": "person_bk",
    "type": "STRING",
    "mode": "REQUIRED",
    "description": "Primary business key for debtor entity"
  },
  {
    "name": "month_dt",
    "type": "DATE",
    "mode": "REQUIRED",
    "description": "Partition date defining billing month boundary"
  },
  {
    "name": "debt_amt",
    "type": "NUMERIC",
    "mode": "NULLABLE",
    "description": "Outstanding debt balance"
  },
  {
    "name": "delinquent_ind",
    "type": "BOOLEAN",
    "mode": "NULLABLE",
    "description": "Delinquency status flag"
  },
  {
    "name": "active_ind",
    "type": "BOOLEAN",
    "mode": "NULLABLE",
    "description": "Active account indicator"
  },
  {
    "name": "load_ts",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Timestamp when record was initially inserted"
  },
  {
    "name": "update_ts",
    "type": "TIMESTAMP",
    "mode": "REQUIRED",
    "description": "Timestamp when record was most recently updated"
  },
  {
    "name": "data_hd",
    "type": "INTEGER",
    "mode": "REQUIRED",
    "description": "FARM_FINGERPRINT 64-bit integer hash digest of payload fields"
  }
]
```

### 3.1 Equivalent DDL Definition
The DDL statement below provisions the partitioned target entity with mandatory partition filters:

```sql
CREATE OR REPLACE TABLE `enterprise.lend_debt_04_anl.customer_debt_fact`
(
  person_bk      STRING
                 NOT NULL,
  month_dt       DATE
                 NOT NULL,
  debt_amt       NUMERIC,
  delinquent_ind BOOL,
  active_ind     BOOL,
  load_ts        TIMESTAMP
                 NOT NULL,
  update_ts      TIMESTAMP
                 NOT NULL,
  data_hd        INT64
                 NOT NULL
)
PARTITION BY month_dt
  CLUSTER BY person_bk
OPTIONS (
  require_partition_filter = TRUE,
  description              = 'Monthly debtor financial profiles maintained via partition-pruned merge'
)
```

---

## 4. Physical Table Provisioning via BigQuery CLI

Run the  command to create the partitioned table:

```bash
# Provision table with Day partitioning, clustering, and enforced partition filters
bq mk \
  --table \
  --schema=telemetry_schema.json \
  --time_partitioning_field=event_timestamp \
  --time_partitioning_type=DAY \
  --time_partitioning_expiration=7776000 \
  --require_partition_filter=true \
  --clustering_fields=tenant_id,event_type,user_id \
  --description="Production telemetry events table" \
  enterprise-prod:analytics.user_telemetry
```
