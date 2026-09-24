#!/usr/bin/env bash
# BigQuery Skill Artifact Verification Smoke Test
# Validates Go and Python example code compiles, vets, and passes unit tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
EXAMPLES_DIR="$SKILL_ROOT/examples"

PASS=0
FAIL=0

run_check() {
  local label="$1"
  shift
  printf "  %-45s" "$label"
  if "$@" >/dev/null 2>&1; then
    echo "✅ PASS"
    PASS=$((PASS + 1))
  else
    echo "❌ FAIL"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== BigQuery Skill Verification ==="
echo ""

# --- Go checks ---
echo "[Go]"
if command -v go >/dev/null 2>&1; then
  run_check "go vet" go -C "$EXAMPLES_DIR" vet ./...
  run_check "go build" go -C "$EXAMPLES_DIR" build -o /dev/null ./...
  run_check "go test" go -C "$EXAMPLES_DIR" test ./... -count=1 -short
else
  echo "  SKIP: 'go' not found in PATH"
fi

echo ""

# --- Python checks ---
echo "[Python]"
if command -v python3 >/dev/null 2>&1; then
  run_check "python3 syntax check (schema_extraction)" \
    python3 -m py_compile "$EXAMPLES_DIR/schema_extraction.py"
  run_check "python3 syntax check (tests)" \
    python3 -m py_compile "$EXAMPLES_DIR/test_schema_extraction.py"

  # Unit tests run only if google-cloud-bigquery is installed
  if python3 -c "import google.cloud.bigquery" 2>/dev/null; then
    run_check "python3 unittest" \
      python3 -m pytest "$EXAMPLES_DIR/test_schema_extraction.py" -q --tb=short
  else
    echo "  SKIP: 'google-cloud-bigquery' not installed, skipping unit tests"
  fi
else
  echo "  SKIP: 'python3' not found in PATH"
fi

echo ""

# --- Shell script checks ---
echo "[Shell]"
if command -v bash >/dev/null 2>&1; then
  run_check "bash syntax check (dry_run.sh)" \
    bash -n "$SCRIPT_DIR/dry_run.sh"
  run_check "bash syntax check (extract_schema.sh)" \
    bash -n "$SCRIPT_DIR/extract_schema.sh"
  run_check "bash syntax check (verify.sh)" \
    bash -n "$SCRIPT_DIR/verify.sh"
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
