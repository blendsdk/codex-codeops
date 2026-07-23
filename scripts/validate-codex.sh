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
    skills _shared standards references docs plans README.md AGENTS.md
}

validate_scenarios() {
  local scenario
  for scenario in compiler financial web; do
    python3 scripts/compare_scenarios.py "tests/scenarios/$scenario" || return 1
  done
}

validate_release_evidence() {
  python3 - <<'PY'
import json
import re
from pathlib import Path

manifest = json.loads(Path('.codex-plugin/plugin.json').read_text(encoding='utf-8'))
scenario = json.loads(Path('tests/scenarios/evidence.json').read_text(encoding='utf-8'))
review = json.loads(Path('tests/evidence/release-review-final.json').read_text(encoding='utf-8'))
assert scenario['codex']['pluginVersion'].startswith('0.2.0')
assert scenario['claude']['pluginVersion'] == '3.12.0'
assert scenario['scope'] == 'requirements-stage ambiguity discovery and gate behavior'
assert review['verdict'] == 'PASS'
assert not any(item['severity'] in {'critical', 'major'} for item in review['findings'])
install = Path('tests/evidence/install-cli.md').read_text(encoding='utf-8')
recorded = re.search(r'- Plugin: `[^`]+`, version `([^`]+)`', install).group(1)
current = manifest['version'].split('+', 1)[0]
assert recorded == current
plan = Path('plans/auto-design/99-execution-plan.md').read_text(encoding='utf-8')
if '- [ ] 3.1.4 ' in plan:
    # A release commit must exist before its remote marketplace install can be observed. The
    # pre-publication state is explicit, version-matched, and may exist only while the release
    # task remains open; completing the task requires replacing it with tagged install evidence.
    assert '- Evidence state: pre-publication package validation' in install
    assert f'- Source state: working tree for planned `v{current}`' in install
else:
    assert f'- Repository source: release tag `v{current}`' in install
    assert re.search(rf'enabled at\s+`{re.escape(current)}`', install)
assert current in Path('CHANGELOG.md').read_text(encoding='utf-8')
PY
}

validate_preflight_contract() {
  python3 - <<'PY'
from pathlib import Path

skill = Path('skills/preflight/SKILL.md').read_text(encoding='utf-8')
report = Path('skills/preflight/report-format.md').read_text(encoding='utf-8')
dimensions = Path('skills/preflight/dimensions.md').read_text(encoding='utf-8')
auditor = Path('agent-templates/preflight-auditor.md').read_text(encoding='utf-8')

assert '## Audit scope contract' in skill
assert 'contextual, not scope expansion' in skill
assert 'require a fresh-session audit or an explicit user decision' in skill
assert 'Preserve finding identity across iterations' in skill
assert 'requirements/00-preflight-report-RD-NN.md' in skill
assert 'all remaining 🟡 explicitly accepted' in report
assert 'Finding identifiers name root causes' in report
assert 'Freeze the scope' in dimensions
assert 'Respect the audit boundary' in auditor

roadmap = Path('skills/roadmap/SKILL.md').read_text(encoding='utf-8')
assert 'A narrow report never advances sibling RDs' in roadmap
assert 'proves only that document passed' in roadmap
PY
}

validate_plan_execution_contracts() {
  python3 - <<'PY'
from pathlib import Path

make_plan = Path('skills/make-plan/SKILL.md').read_text(encoding='utf-8')
exec_plan = Path('skills/exec-plan/SKILL.md').read_text(encoding='utf-8')
protocol = Path('skills/exec-plan/execution-protocol.md').read_text(encoding='utf-8')
template = Path('skills/make-plan/templates.md').read_text(encoding='utf-8')

assert '## Planning scope contract' in make_plan
assert 'exact expanded modification set' in make_plan
assert 'explicitly approved `⏸ Deferred`' in make_plan
assert 'after two post-gate ambiguity batches' in make_plan
assert 'except the incrementally persisted Ambiguity' in make_plan
assert '--gate plan --target <target>' in make_plan.replace(' \\\n  ', ' ')
assert '--gate execution --target <plan-target>' in exec_plan.replace(' \\\n  ', ' ')
assert '--request <transition-request.json>' in exec_plan.replace(' \\\n  ', ' ')
assert '`task-complete`' in exec_plan
assert 'codeops_worktree_snapshot.py\" snapshot' in protocol
assert 'codeops_worktree_snapshot.py\" diff' in protocol
assert 'three consecutive failures with the same failure signature' in protocol
assert 'expected modification set' in protocol
assert 'Phase baseline tree' in template
PY
}

validate_auto_design_contract() {
  python3 - <<'PY'
from pathlib import Path

policy = Path('_shared/auto-design.md').read_text(encoding='utf-8')
supported = (
    Path('skills/make-requirements/SKILL.md'),
    Path('skills/make-plan/SKILL.md'),
    Path('skills/preflight/SKILL.md'),
    Path('skills/exec-plan/SKILL.md'),
)

for token in (
    'Authority: AI — delegated by --auto-design',
    '## Reserved authority',
    'does not grant action permission',
    'root invocation ID',
    'never widen',
    'bounded escalation',
):
    assert token in policy, token

for path in supported:
    text = path.read_text(encoding='utf-8')
    assert '## Auto-design option' in text, path
    assert 'exact standalone `--auto-design` token' in text, path
    assert 'before the first `--` sentinel' in text, path
    assert 'zero occurrences means normal mode' in text, path
    assert 'more than one is invalid' in text, path
    assert 'tokens at or after the sentinel are target content' in text, path
    assert '../../_shared/auto-design.md' in text, path
    assert 'unsupported child fails closed' in text, path
    assert 'does not grant action permission' in text, path
    assert 'Normal mode:' in text, path

for path in Path('skills').glob('*/SKILL.md'):
    if path not in supported:
        assert '../../_shared/auto-design.md' not in path.read_text(encoding='utf-8'), path

assert 'does not imply `--auto-commit`' in supported[-1].read_text(encoding='utf-8')
assert 'never auto-waive risk or dismiss a critical/major finding' in (
    supported[2].read_text(encoding='utf-8')
)

requirements_add = Path('skills/make-requirements/review-and-add.md').read_text(encoding='utf-8')
requirements = supported[0].read_text(encoding='utf-8')
plan = supported[1].read_text(encoding='utf-8')
plan_checklist = Path('skills/make-plan/quality-checklist.md').read_text(encoding='utf-8')
preflight_report = Path('skills/preflight/report-format.md').read_text(encoding='utf-8')
execution = supported[-1].read_text(encoding='utf-8')
execution_protocol = Path('skills/exec-plan/execution-protocol.md').read_text(encoding='utf-8')

assert 'With active auto-design, resolve eligible technical items' in requirements_add
assert 'complete auto-design delegated record' in requirements
assert 'active auto-design resolves eligible technical decisions' in requirements
assert 'complete delegated provenance for every eligible resolution' in plan
assert 'under the auto-design policy' in plan_checklist
assert 'canonical delegated marker' in preflight_report
assert 'does not authorize applying the fix or waiving a finding' in preflight_report
assert 'With active auto-design, resolve an eligible technical choice' in execution
assert 'active auto-design resolves eligible technical decisions' in execution
assert 'active auto-design to an eligible technical choice' in execution_protocol

combined_authoritative = '\n'.join((preflight_report, execution, execution_protocol)).lower()
for forbidden in (
    '--auto-design authorizes',
    '--auto-design grants',
    'auto-design automatically applies',
    'auto-design automatically commits',
    'auto-design automatically pushes',
    'auto-design automatically deploys',
):
    assert forbidden not in combined_authoritative, forbidden

preflight = supported[2].read_text(encoding='utf-8')
assert 'In normal mode, every finding' in preflight
assert 'With active auto-design, eligible technical resolutions' in preflight
assert 'In normal mode, 🔴 CRITICAL and 🟠 MAJOR findings' in execution
assert 'With active auto-design, select and record' in execution
PY
}

run_check "plugin manifest" python3 scripts/validate_plugin.py .
run_check "skill manifests" validate_skills
run_check "marketplace metadata" validate_marketplace
run_check "Codex-native shipped terminology" validate_native_terms
run_check "local Markdown links" validate_links
run_check "shell syntax" bash -n scripts/*.sh bin/codeops-worktree
run_check "preflight scope and convergence contract" validate_preflight_contract
run_check "plan and execution scope contracts" validate_plan_execution_contracts
run_check "auto-design authority contract" validate_auto_design_contract
run_check "state conformance" python3 -m unittest discover -s tests/conformance -p 'test_*.py'
run_check "retained adversarial parity evidence" validate_scenarios
run_check "release evidence provenance" validate_release_evidence

if (( failures > 0 )); then
  printf '\n%d validation group(s) failed.\n' "$failures" >&2
  exit 1
fi

printf '\nAll Codex validation groups passed.\n'
