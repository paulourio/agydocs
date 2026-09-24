# Resource Filtering, Formatting, and Projections Specification

This document details query expressions, server-side filtering, projection attributes, and output formatting in the Google Cloud CLI (`gcloud`). It specifies the mechanics of `--filter`, `--format`, `--flatten`, and nested resource transforms.

```bash
# Query running instances in us-central1, projecting internal and external IPs
gcloud compute instances list \
  --project=core-infra-prod \
  --filter="status=RUNNING AND zone:us-central1-*" \
  --format="table(name, zone.basename(), networkInterfaces[0].networkIP:label=INTERNAL_IP, networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP)"
```

---

## 1. Dual Execution Architecture: Server vs Client

The CLI resolves filter expressions through two processing tiers based on backend API features:

- **Server-Side Processing:** High-volume services (such as Compute Engine, Cloud Storage, and Cloud Logging) parse filter expressions directly within the Google Cloud storage and indexing engine. The backend prunes non-matching records before transmitting bytes over the network, minimizing egress volume and API latency.
- **Client-Side Processing:** APIs lacking native filter query parameters return full resource records to the client host. The local CLI runtime parses the complete JSON payload and applies boolean expressions in memory before output rendering.
- **Client-Side Format Processing:** Output formatting through `--format` executes exclusively on the local machine after receiving API responses.

```
┌───────────────────────────┐           Server-Side Query           ┌───────────────────────────┐
│ gcloud Client Host        ├──────────────────────────────────────►│ Cloud API Control Plane   │
│ Applies --format          │◄──────────────────────────────────────┤ Evaluates --filter on     │
│ Transforms & Colors Table │         Filtered JSON Payload         │ Storage Index Layers      │
└───────────────────────────┘                                       └───────────────────────────┘
```

---

## 2. Filter Expression Syntax

Filter expressions construct boolean logic to select matching resources from API responses.

### 2.1 Comparison Operators
Expressions support exact, prefix, substring, and regex operators:

| Operator | Syntax Example | Evaluation Semantics |
| :--- | :--- | :--- |
| **Exact Equality** | `status=RUNNING` | Matches keys equal to the target string. |
| **Inequality** | `status!=TERMINATED` | Matches keys not equal to the target string. |
| **Prefix / Substring** | `name:web-*` | Matches values beginning with or containing target text. |
| **Regular Expression** | `name ~ "^prod-(app\|api)-[0-9]+$"` | Evaluates PCRE regex patterns against the key value. |
| **Numerical Comparison** | `disks[0].diskSizeGb >= 500` | Compares integer and floating point values numerically. |

### 2.2 Boolean Composition
Combine multiple comparison terms with uppercase boolean keywords:

```bash
# Combine conditions using conjunction and disjunction
gcloud compute instances list \
  --project=core-infra-prod \
  --filter="(status=RUNNING OR status=PROVISIONING) AND tags.items:frontend"

# Filter resources created within the last seven days
gcloud compute disks list \
  --project=core-infra-prod \
  --filter="creationTimestamp > -P7D AND sizeGb > 100"
```

Parentheses clarify evaluation order between logical terms.

---

## 3. Format Specifiers and Table Projections

The `--format` flag translates JSON payloads into structured human-readable tables or machine-readable streams.

### 3.1 Format Types
The CLI supports multiple serialization formats:
- **`table`:** Renders tabular columns with automatic terminal width calculation.
- **`json`:** Emits indented JSON payloads for ingestion by tools or scripts.
- **`yaml`:** Formats records as structured YAML documents.
- **`csv`:** Outputs comma-delimited rows suitable for spreadsheet import.
- **`value(key)`:** Prints raw unquoted string values without headers, ideal for shell variable assignment.

### 3.2 Projection Attributes and Column Modifiers
Table projections customize column labels, alignments, and sort priority:

```bash
# Table projection with custom labels and sort ordering
gcloud compute instances list \
  --project=core-infra-prod \
  --format="table(name:sort=1, zone.basename():label=ZONE, status.color(green=RUNNING, red=TERMINATED):label=STATUS)"
```

Common attribute modifiers include:
- **`:label=STRING`:** Sets the column header title.
- **`:sort=INTEGER`:** Sets multi-column sort priority, with negative integers reversing order.
- **`:align=left|center|right`:** Controls column text alignment.

---

## 4. Built-In Transform Functions

Transform functions manipulate projection values directly inside format specifiers:

| Transform Function | Example Invocation | Output Transformation |
| :--- | :--- | :--- |
| **`basename()`** | `zone.basename()` | Truncates fully qualified URIs down to their trailing segment. |
| **`date()`** | `creationTimestamp.date(format='%Y-%m-%d')` | Formats ISO 8601 timestamps into standard calendar strings. |
| **`color()`** | `status.color(green=RUNNING, red=STOPPED)` | Applies ANSI color escapes based on string match. |
| **`yesno()`** | `canIpForward.yesno(yes='TRUE', no='FALSE')` | Converts boolean values into custom strings. |
| **`segment()`** | `id.segment(0)` | Splits string keys by slashes and selects zero-based index tokens. |

---

## 5. Array Flattening and Unnesting

Nested resource arrays (such as IAM policy bindings or multi-NIC network attachments) emit complex structures. The `--flatten` flag expands array elements into discrete top-level rows:

```bash
# Flatten IAM policy bindings to inspect members per role
gcloud projects get-iam-policy core-infra-prod \
  --flatten="bindings[].members" \
  --format="table(bindings.role, bindings.members)"
```

Using `--flatten` allows downstream filter and format expressions to evaluate repeated fields as scalar attributes.
