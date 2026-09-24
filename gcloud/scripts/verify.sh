#!/usr/bin/env bash
# Gcloud Skill Verification Smoke Test
# Validates shell syntax and formatting, Go SDK formatting and tests,
# Python SDK linting, formatting, and unit tests, and evaluation runner assertions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
EXAMPLES_DIR="$SKILL_ROOT/examples"
RESOURCES_DIR="$SKILL_ROOT/resources"

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

echo "=== Google Cloud CLI (gcloud) Skill Verification ==="
echo ""

# Shell syntax and formatting checks
echo "[Shell Scripts]"
if command -v bash >/dev/null 2>&1; then
  for script_file in "$SCRIPT_DIR"/*.sh; do
    if [[ -f "$script_file" ]]; then
      run_check "bash syntax check ($(basename "$script_file"))" bash -n "$script_file"
    fi
  done
  for script_file in "$EXAMPLES_DIR"/*.sh; do
    if [[ -f "$script_file" ]]; then
      run_check "bash syntax check ($(basename "$script_file"))" bash -n "$script_file"
    fi
  done
fi

SHFMT_BIN="$(command -v shfmt 2>/dev/null || echo "/home/ff/go/bin/shfmt")"
if [[ -x "$SHFMT_BIN" ]]; then
  run_check "shfmt formatting check (2-space indent)" "$SHFMT_BIN" -i 2 -ci -d "$EXAMPLES_DIR"/*.sh "$SCRIPT_DIR"/*.sh
else
  echo "  SKIP: shfmt utility not found"
fi

# Documentation Ingestion Tests
echo ""
echo "[Documentation Ingestion Pipeline]"
if [[ -f "$SCRIPT_DIR/test_fetch_docs.py" ]]; then
  run_check "fetch_docs unit tests" python3 -m unittest "$SCRIPT_DIR/test_fetch_docs.py"
fi

# Go example verification
echo ""
echo "[Go SDK Client]"
if command -v go >/dev/null 2>&1 && [[ -f "$EXAMPLES_DIR/go.mod" ]]; then
  run_check "gofmt diff check" bash -c "test -z \"\$(gofmt -d \"$EXAMPLES_DIR\")\""
  run_check "go vet" go -C "$EXAMPLES_DIR" vet ./...
  run_check "go test" go -C "$EXAMPLES_DIR" test ./... -count=1 -short
else
  echo "  SKIP: Go runtime not available or no go.mod in examples/"
fi

# Python example verification
echo ""
echo "[Python SDK Client & Ingestion Pipeline]"
if command -v python3 >/dev/null 2>&1; then
  if command -v ruff >/dev/null 2>&1; then
    run_check "ruff linter check" ruff check "$SKILL_ROOT"
    run_check "ruff formatting check" ruff format --check "$EXAMPLES_DIR" "$SCRIPT_DIR" "$RESOURCES_DIR"
  fi
  py_files=$(find "$EXAMPLES_DIR" "$SCRIPT_DIR" "$RESOURCES_DIR" -maxdepth 1 -name "*.py" 2>/dev/null || true)
  if [[ -n "$py_files" ]]; then
    run_check "python3 syntax check" python3 -m py_compile $py_files
    run_check "python3 client unit tests" python3 -m unittest "$EXAMPLES_DIR/test_client.py"
  fi
else
  echo "  SKIP: Python3 runtime not available"
fi

# Eval runner verification
echo ""
echo "[Automated Evaluation Runner]"
if [[ -f "$RESOURCES_DIR/eval_runner.py" ]] && [[ -f "$RESOURCES_DIR/test_eval_runner.py" ]]; then
  run_check "eval runner unit tests" python3 -m unittest "$RESOURCES_DIR/test_eval_runner.py"
  if [[ -f "$RESOURCES_DIR/eval_spec.json" ]]; then
    run_check "eval_spec (query_infrastructure.sh)" \
      python3 "$RESOURCES_DIR/eval_runner.py" --spec "$RESOURCES_DIR/eval_spec.json" --artifact "$EXAMPLES_DIR/query_infrastructure.sh"
    run_check "eval_spec (batch_snapshot_disks.sh)" \
      python3 "$RESOURCES_DIR/eval_runner.py" --spec "$RESOURCES_DIR/eval_spec.json" --artifact "$EXAMPLES_DIR/batch_snapshot_disks.sh"
    run_check "eval_spec (provision_service_account.sh)" \
      python3 "$RESOURCES_DIR/eval_runner.py" --spec "$RESOURCES_DIR/eval_spec.json" --artifact "$EXAMPLES_DIR/provision_service_account.sh"
  fi
fi

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
