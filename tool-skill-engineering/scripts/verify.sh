#!/usr/bin/env bash
# Tool Skill Engineering Verification Smoke Test
# Asserts syntax validity, reference SDK unit tests, eval runner tests, and scaffolding behavior.
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

echo "=== Tool Skill Engineering Verification ==="
echo ""

# Shell syntax checks
echo "[Shell Scripts]"
if command -v bash >/dev/null 2>&1; then
  run_check "bash syntax check (scaffold_tool_skill.sh)" \
    bash -n "$SCRIPT_DIR/scaffold_tool_skill.sh"
  run_check "bash syntax check (verify.sh)" \
    bash -n "$SCRIPT_DIR/verify.sh"
  run_check "bash syntax check (verify.sh.tmpl)" \
    bash -n "$SKILL_ROOT/resources/skill_template/scripts/verify.sh.tmpl"
fi

# Eval runner tests
echo ""
echo "[Automated Evaluation Runner]"
if command -v python3 >/dev/null 2>&1; then
  run_check "eval runner unit tests" \
    python3 -m unittest discover -s "$RESOURCES_DIR" -p "test_*.py"
fi

# In-tree Go SDK reference checks
echo ""
echo "[Reference Go SDK Client]"
if command -v go >/dev/null 2>&1; then
  run_check "go vet (examples)" go -C "$EXAMPLES_DIR" vet ./...
  run_check "go test (examples)" go -C "$EXAMPLES_DIR" test ./... -count=1 -short
fi

# In-tree Python SDK reference checks
echo ""
echo "[Reference Python SDK Client]"
if command -v python3 >/dev/null 2>&1; then
  run_check "python3 syntax check (examples)" \
    python3 -m py_compile "$EXAMPLES_DIR/client.py" "$EXAMPLES_DIR/test_client.py"
  run_check "python3 unit tests (examples)" \
    python3 -m unittest discover -s "$EXAMPLES_DIR" -p "test_*.py"
fi

# Scaffolding smoke test in temp directory
echo ""
echo "[Scaffolding End-to-End Test]"
TMP_SCAFFOLD="$(mktemp -d)"
trap 'rm -rf "$TMP_SCAFFOLD"' EXIT

run_check "scaffold_tool_skill execution" \
  bash "$SCRIPT_DIR/scaffold_tool_skill.sh" test-tool "$TMP_SCAFFOLD/test-tool"

run_check "scaffolded verify.sh end-to-end execution" \
  bash "$TMP_SCAFFOLD/test-tool/scripts/verify.sh"

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
