#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

failures=0

run_check() {
  local label="$1"
  shift
  printf '==> %s\n' "$label"
  if "$@"; then
    printf 'PASS: %s\n' "$label"
  else
    printf 'FAIL: %s\n' "$label" >&2
    failures=$((failures + 1))
  fi
}

validate_skills() {
  local skill
  for skill in skills/*; do
    [[ -d "$skill" ]] || continue
    python3 scripts/validate_skill.py "$skill" || return 1
  done
}

validate_marketplace() {
  python3 - <<'PY'
import json
from pathlib import Path

path = Path('.agents/plugins/marketplace.json')
data = json.loads(path.read_text(encoding='utf-8'))
assert isinstance(data.get('name'), str) and data['name']
assert isinstance(data.get('plugins'), list) and data['plugins']
entry = next(item for item in data['plugins'] if item.get('name') == 'codeops')
assert entry['source']['source'] in {'url', 'git-subdir', 'local'}
assert entry['policy']['installation'] in {'AVAILABLE', 'INSTALLED_BY_DEFAULT', 'NOT_AVAILABLE'}
assert entry['policy']['authentication'] in {'ON_INSTALL', 'ON_USE'}
assert isinstance(entry.get('category'), str) and entry['category']
PY
}

validate_native_terms() {
  local matches
  matches="$(rg -n --glob '!plans/**' --glob '!docs/**' --glob '!scripts/fixtures/**' \
    'CLAUDE_PLUGIN_ROOT|~/.claude|\.claude/agents|model: (opus|sonnet|fable)|Follow the project.s CLAUDE.md' \
    skills _shared standards agent-templates hooks 2>/dev/null || true)"
  if [[ -n "$matches" ]]; then
    printf '%s\n' "$matches" >&2
    return 1
  fi
}

validate_links() {
  python3 scripts/validate_markdown_links.py \
    skills _shared standards plans README.md AGENTS.md
}

run_check "plugin manifest" python3 scripts/validate_plugin.py .
run_check "skill manifests" validate_skills
run_check "marketplace metadata" validate_marketplace
run_check "Codex-native shipped terminology" validate_native_terms
run_check "local Markdown links" validate_links
run_check "shell syntax" bash -n scripts/*.sh bin/codeops-worktree
run_check "state conformance" python3 -m unittest discover -s tests/conformance -p 'test_*.py'

if (( failures > 0 )); then
  printf '\n%d validation group(s) failed.\n' "$failures" >&2
  exit 1
fi

printf '\nAll Codex validation groups passed.\n'
