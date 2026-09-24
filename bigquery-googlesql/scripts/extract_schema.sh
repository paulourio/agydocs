#!/usr/bin/env bash
# BigQuery Schema Extraction CLI Wrapper
# Extracts table schema in canonical TableFieldSchema[] JSON representation.

set -euo pipefail

usage() {
  local exit_code="${1:-1}"
  cat <<EOF
Usage: $(basename "$0") [OPTIONS] <TABLE_REF>

Extracts canonical BigQuery schema JSON for a specified table.

Arguments:
  TABLE_REF             Table reference in 'project:dataset.table' or 'dataset.table' format.

Options:
  -o, --output FILE     Write JSON output to FILE instead of standard output.
  -h, --help            Display this help message.

Examples:
  $(basename "$0") my-project:analytics.events
  $(basename "$0") analytics.events -o /tmp/events_schema.json
EOF
  exit "$exit_code"
}

OUTPUT_FILE=""
TABLE_REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      OUTPUT_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage 0
      ;;
    *)
      if [[ -z "$TABLE_REF" ]]; then
        TABLE_REF="$1"
        shift
      else
        echo "Error: Unexpected argument '$1'" >&2
        usage
      fi
      ;;
  esac
done

if [[ -z "$TABLE_REF" ]]; then
  echo "Error: Missing required TABLE_REF argument." >&2
  usage
fi

if ! command -v bq >/dev/null 2>&1; then
  echo "Error: 'bq' CLI utility not found in PATH." >&2
  exit 1
fi

if ! SCHEMA_JSON=$(bq show --schema --format=prettyjson "$TABLE_REF" 2>&1); then
  echo "Error: Failed to extract schema for table '$TABLE_REF':" >&2
  echo "$SCHEMA_JSON" >&2
  exit 1
fi

if [[ -n "$OUTPUT_FILE" ]]; then
  mkdir -p "$(dirname "$OUTPUT_FILE")"
  printf '%s\n' "$SCHEMA_JSON" > "$OUTPUT_FILE"
  echo "Schema exported successfully to $OUTPUT_FILE"
else
  printf '%s\n' "$SCHEMA_JSON"
fi
