#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/validate_markdown_links.py README.md docs plans

if rg -n 'commands will be published|TODO|TBD|claude-codeops/' README.md docs; then
  printf 'Documentation contains unfinished or stale release text.\n' >&2
  exit 1
fi

printf 'Documentation checks passed.\n'
