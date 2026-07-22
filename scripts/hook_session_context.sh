#!/usr/bin/env bash
set -euo pipefail

: "${PLUGIN_ROOT:?Codex must provide PLUGIN_ROOT}"
cat "$PLUGIN_ROOT/standards/coding-standards.md"
printf '\n'
cat "$PLUGIN_ROOT/standards/output-style.md"
