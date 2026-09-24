#!/usr/bin/env bash
# BigQuery Query Dry-Run Cost & Scan Volume Estimator
# Executes dry-run query against GoogleSQL to calculate scan size and dollar cost.

set -euo pipefail

usage() {
  local exit_code="${1:-1}"
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Simulates BigQuery query execution to estimate bytes scanned and financial cost.

Options:
  -q, --query SQL       SQL query string to dry-run.
  -f, --file FILE       Path to SQL file to dry-run.
  -p, --project ID      GCP project ID to execute against.
  -h, --help            Display this help message.

Examples:
  $(basename "$0") -q "SELECT user_id, COUNT(*) AS event_qty FROM \`enterprise.telem_traffic_01_lnd.event_fact\` GROUP BY 1"
  $(basename "$0") -f ./reporting_query.sql -p my-project-id
EOF
  exit "$exit_code"
}

QUERY=""
SQL_FILE=""
PROJECT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -q|--query)
      QUERY="$2"
      shift 2
      ;;
    -f|--file)
      SQL_FILE="$2"
      shift 2
      ;;
    -p|--project)
      PROJECT="$2"
      shift 2
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      echo "Error: Unknown argument '$1'" >&2
      usage
      ;;
  esac
done

if [[ -z "$QUERY" && -z "$SQL_FILE" ]]; then
  echo "Error: Either -q (--query) or -f (--file) must be specified." >&2
  usage
fi

if [[ -n "$QUERY" && -n "$SQL_FILE" ]]; then
  echo "Error: Cannot specify both -q and -f." >&2
  usage
fi

if [[ -n "$SQL_FILE" ]]; then
  if [[ ! -f "$SQL_FILE" ]]; then
    echo "Error: SQL file '$SQL_FILE' not found." >&2
    exit 1
  fi
  QUERY=$(cat "$SQL_FILE")
fi

if ! command -v bq >/dev/null 2>&1; then
  echo "Error: 'bq' CLI utility not found in PATH." >&2
  exit 1
fi

BQ_CMD=(bq query --dry_run --use_legacy_sql=false --format=prettyjson)
if [[ -n "$PROJECT" ]]; then
  BQ_CMD+=(--project_id="$PROJECT")
fi

RAW_RESULT=$("${BQ_CMD[@]}" "$QUERY" 2>&1) || true

# Parse output using embedded Python helper
python3 -c '
import json
import sys
from decimal import Decimal

raw = sys.stdin.read()
try:
    data = json.loads(raw)
except Exception:
    # Print raw stderr if bq returned an error string
    print(raw, file=sys.stderr)
    sys.exit(1)

stats = data.get("statistics", {})
query_stats = stats.get("query", {})
bytes_scanned = Decimal(query_stats.get("totalBytesProcessed", 0))
bytes_billed = Decimal(query_stats.get("totalBytesBilled", 0))

gib = bytes_scanned / Decimal(1024**3)
# BigQuery on-demand pricing: $6.25 per decimal Terabyte (10^12 bytes), 10 MB minimum per query
bytes_per_tb = Decimal(10**12)
min_billable = Decimal(10 * 1024 * 1024)
effective_billed = bytes_billed if bytes_billed > 0 else (max(bytes_scanned, min_billable) if bytes_scanned > 0 else Decimal(0))
cost = (effective_billed / bytes_per_tb) * Decimal("6.25")

print("=== BigQuery Dry-Run Execution Analysis ===")
print(f"Total Bytes Processed : {bytes_scanned:,} bytes ({gib:.4f} GiB)")
print(f"Total Bytes Billed    : {effective_billed:,} bytes")
print(f"Estimated Cost (USD)  : ${cost:.4f} (@ $6.25 / TB on-demand)")

statement_type = query_stats.get("statementType")
if statement_type:
    print(f"Statement Type        : {statement_type}")

tables = query_stats.get("referencedTables", [])
if tables:
    print(f"Referenced Tables ({len(tables)}):")
    for t in tables:
        print(f"  - {t.get(\"projectId\")}:{t.get(\"datasetId\")}.{t.get(\"tableId\")}")
' <<< "$RAW_RESULT"
