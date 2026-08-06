#!/usr/bin/env bash
# Unix compatibility launcher; portable behavior lives in codeops_roadmap.py.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$SCRIPT_DIR/codeops_roadmap.py" sync --root . "$@"
