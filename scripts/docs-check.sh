#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3 scripts/validate_markdown_links.py README.md docs plans

python3 - <<'PY'
import json
from pathlib import Path

root = Path('.')
skill_names = {path.parent.name for path in root.glob('skills/*/SKILL.md')}
page_names = {
    path.stem
    for path in (root / 'docs' / 'skills').glob('*.md')
    if path.stem != 'index'
}

assert page_names == skill_names, (
    f'skill documentation mismatch: missing={sorted(skill_names - page_names)}, '
    f'extra={sorted(page_names - skill_names)}'
)

manifest = json.loads((root / '.codex-plugin' / 'plugin.json').read_text(encoding='utf-8'))
config = (root / 'docs' / '.vitepress' / 'config.ts').read_text(encoding='utf-8')
workflow = (root / '.github' / 'workflows' / 'docs.yml').read_text(encoding='utf-8')

for skill_name in sorted(skill_names):
    assert f"link: '/skills/{skill_name}'" in config, f'{skill_name} is missing from the sidebar'

version = manifest['version'].split('+', 1)[0]
assert "base: '/codex-codeops/'" in config
assert f"text: '{version}'" in config
assert f'/releases/tag/v{version}' in config
assert 'branches: [main]' in workflow
assert 'docs/.vitepress/dist' in workflow
PY

if rg -n 'commands will be published|TODO|TBD|claude-codeops/|codeops_state\.py' README.md docs; then
  printf 'Documentation contains unfinished or stale release text.\n' >&2
  exit 1
fi

if git ls-files --error-unmatch docs/.vitepress/dist >/dev/null 2>&1; then
  printf 'Generated VitePress output must not be tracked.\n' >&2
  exit 1
fi

npm run docs:build

printf 'Documentation checks passed.\n'
