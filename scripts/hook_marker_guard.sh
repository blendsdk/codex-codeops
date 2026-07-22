#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
case "$input" in
  *"codeops/.codeops.yml"*)
    printf '%s\n' \
      'CodeOps warning: codeops/.codeops.yml is the layout marker and is owned by setup-codeops; edit it only through the setup/migration workflow.' \
      >&2
    ;;
esac
exit 0
