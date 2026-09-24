# Observability, Asynchronous Operations, and Scripting Discipline

This document specifies logging queries, operational log sinks, asynchronous task polling, and idempotent shell scripting in the Google Cloud CLI (`gcloud`). It details Cloud Logging filter grammar, operation status polling loops, and headless build rules.

```bash
# Query recent application error logs from Cloud Run revisions
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' \
  --project=core-infra-prod \
  --limit=25 \
  --format="table(timestamp.date('%Y-%m-%d %H:%M:%S'), severity, textPayload)"
```

---

## 1. Cloud Logging Query Syntax and Log Sinks

Cloud Logging indexes structured log records emitted across Google Cloud services.

### 1.1 Querying Structured Log Records
The `gcloud logging read` command filters entries using Cloud Logging query language expressions:

```bash
# Stream error entries containing specific error codes across services
gcloud logging read 'severity=ERROR AND jsonPayload.status_code=500' \
  --project=core-infra-prod \
  --freshness=1d \
  --limit=50 \
  --format="json"

# Read logs formatted as plain text timestamps and messages
gcloud logging read 'resource.type="gce_instance" AND logName:"syslog"' \
  --project=core-infra-prod \
  --limit=10 \
  --format="value(textPayload)"
```

### 1.2 Provisioning Centralized Log Sinks
Log sinks route events in real time to external destinations (such as Pub/Sub topics or BigQuery datasets):

```bash
# Export audit logs to a regional Pub/Sub topic for security monitoring
gcloud logging sinks create security-audit-sink \
  pubsub.googleapis.com/projects/core-infra-prod/topics/security-events \
  --project=core-infra-prod \
  --log-filter='logName:"cloudaudit.googleapis.com%2Factivity"' \
  --quiet
```

---

## 2. Asynchronous Operation Polling

Mutating commands accept the `--async` flag to return immediately without blocking pipelines. Headless scripts query the returned operation identifier until the task finishes.

### 2.1 Polling Compute Engine Operations
Compute operations transition through `PENDING`, `RUNNING`, and `DONE` states:

```bash
# Trigger asynchronous instance deletion
OP_ID=$(gcloud compute instances delete worker-old \
  --project=core-infra-prod \
  --zone=us-central1-a \
  --async \
  --format="value(name)")

# Poll operation status until completion
while true; do
  STATUS=$(gcloud compute operations describe "${OP_ID}" \
    --project=core-infra-prod \
    --zone=us-central1-a \
    --format="value(status)")
  if [[ "${STATUS}" == "DONE" ]]; then
    echo "Compute operation ${OP_ID} completed successfully."
    break
  fi
  echo "Operation status: ${STATUS}. Waiting 5 seconds..."
  sleep 5
done
```

This polling pattern prevents timeout failures on slow network connections.

---

## 3. Idempotent Shell Scripting Standards

Production shell scripts must run repeatedly without failing when target resources already exist.

### 3.1 Resource Existence Guards
Scripts query resource status before attempting to create new assets:

```bash
# Check if target storage bucket exists before running creation
BUCKET_NAME="gs://app-artifacts-prod-2026"
PROJECT_ID="core-infra-prod"
if ! gcloud storage buckets describe "${BUCKET_NAME}" >/dev/null 2>&1; then
  echo "Bucket ${BUCKET_NAME} missing. Creating bucket..."
  gcloud storage buckets create "${BUCKET_NAME}" \
    --project="${PROJECT_ID}" \
    --location=us-central1 \
    --quiet
else
  echo "Bucket ${BUCKET_NAME} already exists. Skipping creation."
fi
```

### 3.2 Headless Script Environment Setup
Shell scripts should establish strict error handling and non-interactive variables upfront:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Disable interactive prompts across all gcloud invocations
export CLOUDSDK_CORE_DISABLE_PROMPTS=1

# Define target project identifier
PROJECT_ID="core-infra-prod"
```

These environment primitives eliminate hanging terminal sessions across automated test runners.
