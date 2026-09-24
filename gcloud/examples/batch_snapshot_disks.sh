#!/usr/bin/env bash
# batch_snapshot_disks.sh: Server-side filtered disk querying and async snapshotting with operation polling.
set -euo pipefail

export CLOUDSDK_CORE_DISABLE_PROMPTS=1

PROJECT_ID="${1:-core-infra-prod}"
TARGET_ZONE="${2:-us-central1-a}"
RETENTION_TAG="${3:-daily}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"

echo "==> Querying persistent disks in zone ${TARGET_ZONE} matching tag ${RETENTION_TAG}..."
DISKS=$(gcloud compute disks list \
  --project="${PROJECT_ID}" \
  --filter="zone:${TARGET_ZONE} AND labels.backup:${RETENTION_TAG}" \
  --format="value(name)" \
  --quiet)

if [[ -z "${DISKS}" ]]; then
  echo "No disks found matching criteria. Exiting."
  exit 0
fi

OPERATIONS=()

for DISK in ${DISKS}; do
  SNAP_NAME="${DISK}-snap-${TIMESTAMP}"
  echo "==> Initiating asynchronous snapshot for disk ${DISK} -> ${SNAP_NAME}..."
  OP_NAME=$(gcloud compute disks snapshot "${DISK}" \
    --project="${PROJECT_ID}" \
    --zone="${TARGET_ZONE}" \
    --snapshot-names="${SNAP_NAME}" \
    --storage-location="us-central1" \
    --labels="source-disk=${DISK},backup-tag=${RETENTION_TAG}" \
    --async \
    --format="value(name)" \
    --quiet)

  echo "    Dispatched operation: ${OP_NAME}"
  OPERATIONS+=("${OP_NAME}")
done

echo "==> Polling ${#OPERATIONS[@]} snapshot operations until completion..."
for OP in "${OPERATIONS[@]}"; do
  while true; do
    STATUS=$(gcloud compute operations describe "${OP}" \
      --project="${PROJECT_ID}" \
      --zone="${TARGET_ZONE}" \
      --format="value(status)" \
      --quiet)

    if [[ "${STATUS}" == "DONE" ]]; then
      echo "✅ Operation ${OP} completed successfully."
      break
    fi
    echo "    Operation ${OP} is ${STATUS}. Waiting 5 seconds..."
    sleep 5
  done
done

echo "✅ All snapshot operations finished successfully."
