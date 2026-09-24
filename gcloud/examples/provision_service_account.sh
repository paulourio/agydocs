#!/usr/bin/env bash
# provision_service_account.sh: Idempotent service account provisioning with least-privilege IAM bindings.
set -euo pipefail

export CLOUDSDK_CORE_DISABLE_PROMPTS=1

PROJECT_ID="${1:-core-infra-prod}"
SA_NAME="${2:-analytics-worker}"
SA_DISPLAY_NAME="${3:-Analytics Background Worker}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Checking if service account ${SA_EMAIL} exists..."
EXISTS=$(gcloud iam service-accounts list \
  --project="${PROJECT_ID}" \
  --filter="email=${SA_EMAIL}" \
  --format="value(email)")

if [[ -z "${EXISTS}" ]]; then
  echo "==> Creating service account ${SA_NAME}..."
  gcloud iam service-accounts create "${SA_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="${SA_DISPLAY_NAME}" \
    --quiet
else
  echo "==> Service account ${SA_EMAIL} already exists. Skipping creation."
fi

# Apply narrow runtime roles
echo "==> Binding runtime logging and metrics roles..."
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/monitoring.metricWriter" \
  --quiet

echo "✅ Service account provisioning completed successfully: ${SA_EMAIL}"
