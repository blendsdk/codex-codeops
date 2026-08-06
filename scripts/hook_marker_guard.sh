#!/usr/bin/env bash
set -euo pipefail

: "${PLUGIN_ROOT:?Codex must provide PLUGIN_ROOT}"
exec python3 "$PLUGIN_ROOT/scripts/codeops_hooks.py" --event PreToolUse
