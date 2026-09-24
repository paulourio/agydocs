#!/usr/bin/env bash
# Stylometric Quality Gate Runner
# Automates execution and on-demand compilation of the Go quality gate binary.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BIN_PATH="${SKILL_DIR}/bin/quality_gate"

# Rebuild binary if missing
if [[ ! -x "${BIN_PATH}" ]]; then
  echo "==> Building quality_gate binary..." >&2
  (cd "${SKILL_DIR}" && go build -o "${BIN_PATH}" ./cmd/quality_gate)
fi

exec "${BIN_PATH}" "$@"
