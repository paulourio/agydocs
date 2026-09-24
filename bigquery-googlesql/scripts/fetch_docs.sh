#!/usr/bin/env bash
# fetch_docs.sh: Helper runner for BigQuery documentation fetcher & link rewriter
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Run python fetcher forwarding all arguments
python3 "${SCRIPT_DIR}/fetch_docs.py" "$@"
