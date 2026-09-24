#!/usr/bin/env bash
# query_infrastructure.sh: Advanced resource querying with transforms, projections, and flattening.
set -euo pipefail

export CLOUDSDK_CORE_DISABLE_PROMPTS=1

PROJECT_ID="${1:-core-infra-prod}"

INSTANCE_FORMAT="table(name:sort=1,zone.basename():label=ZONE,"
INSTANCE_FORMAT+="machineType.basename():label=MACHINE_TYPE,"
INSTANCE_FORMAT+="networkInterfaces[0].networkIP:label=INTERNAL_IP,"
INSTANCE_FORMAT+="networkInterfaces[0].accessConfigs[0].natIP:label=EXTERNAL_IP,"
INSTANCE_FORMAT+="status.color(green=RUNNING,red=TERMINATED):label=STATUS)"

echo "=== 1. Running Compute Instances with Network Projection ==="
gcloud compute instances list \
  --project="${PROJECT_ID}" \
  --filter="status=RUNNING" \
  --format="${INSTANCE_FORMAT}" \
  --quiet

echo ""
echo "=== 2. Storage Buckets with Standard Storage Class ==="
gcloud storage buckets list \
  --project="${PROJECT_ID}" \
  --format="table(name,location,defaultStorageClass,timeCreated.date('%Y-%m-%d'):label=CREATED)" \
  --quiet

echo ""
echo "=== 3. Project IAM Policy Flattened by Role and Member ==="
gcloud projects get-iam-policy "${PROJECT_ID}" \
  --flatten="bindings[].members" \
  --format="table(bindings.role:sort=1,bindings.members)" \
  --limit=25 \
  --quiet
