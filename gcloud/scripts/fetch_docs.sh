#!/usr/bin/env bash
# fetch_docs.sh: Helper runner for Google Cloud CLI documentation fetcher & link rewriter
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run python fetcher forwarding all arguments
python3 "${SCRIPT_DIR}/fetch_docs.py" "$@"
