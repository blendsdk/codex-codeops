#!/usr/bin/env bash
#
# agents-sync-check.sh — specification-test suite for the agent-sync engine.
#
# CodeOps Skills Version: 3.12.0
#
# Drives scripts/codeops-agents-sync.sh against throwaway temp git repos whose CLAUDE.md carries
# a quality-profile block, and asserts the engine's contract: only effort-bearing overrides
# materialize a file, generated bodies are byte-identical to the plugin's, generated files are
# stamped and idempotent, hand-authored files are never overwritten or pruned, withdrawn
# overrides are pruned, --check reports drift without writing, and repo data is never executed.
# Each check corresponds to one specification case (ST-1…ST-14). It is a specification test:
# written from the contract BEFORE the engine exists, so it is RED until the engine lands.
#
# It NEVER mutates the plugin's own agents/ directory — every case builds a temp repo and the
# engine is pointed at this repo as CODEOPS_PLUGIN_ROOT.
#
# Usage:  ./scripts/agents-sync-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SYNC="$REPO_ROOT/scripts/codeops-agents-sync.sh"

FAILURES=0

pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

TMP_DIRS=()
cleanup() {
  for d in "${TMP_DIRS[@]:-}"; do
    [[ -n "$d" && -d "$d" ]] && rm -rf "$d"
  done
}
trap cleanup EXIT

GIT_ID=(-c user.email=test@example.com -c user.name=test)

# mk_repo [<agent_models value>] — temp git repo with a CLAUDE.md quality block; echo its path.
# Omit the argument for a repo with no quality-profile block at all.
mk_repo() {
  local tmp; tmp="$(mktemp -d)"; TMP_DIRS+=("$tmp")
  git -C "$tmp" init -q
  if [[ $# -ge 1 ]]; then
    {
      printf '# Fixture project\n\n## Quality profile (CodeOps)\n'
      printf '<!-- CODEOPS-QUALITY:START -->\n'
      printf 'lenses: []\nsecurity_profile: []\nperf_critical: false\nreview_hook: on\ntelemetry: on\n'
      printf 'agent_models: %s\n' "$1"
      printf '<!-- CODEOPS-QUALITY:END -->\n'
    } > "$tmp/CLAUDE.md"
  else
    printf '# Fixture project\n' > "$tmp/CLAUDE.md"
  fi
  git -C "$tmp" "${GIT_ID[@]}" add -A
  git -C "$tmp" "${GIT_ID[@]}" commit -q -m "fixture"
  printf '%s\n' "$tmp"
}

is_clean() { [[ -z "$(git -C "$1" status --porcelain)" ]]; }

# run_sync <repo> <args...> — run the engine inside <repo>; set OUT + RC.
OUT=""
RC=0
run_sync() {
  local repo="$1"; shift
  if [[ ! -x "$SYNC" ]]; then OUT="engine missing or not executable: $SYNC"; RC=127; return; fi
  OUT="$(cd "$repo" && CODEOPS_PLUGIN_ROOT="$REPO_ROOT" "$SYNC" "$@" 2>&1)"
  RC=$?
}

# fm <file> <key> — echo the frontmatter scalar for <key>.
fm() { sed -n '/^---$/,/^---$/p' "$1" | sed -n "s/^$2:[[:space:]]*//p" | head -1; }

# body_of <file> — echo everything after the closing frontmatter delimiter, with any
# CODEOPS-GENERATED marker line removed, so plugin and generated bodies compare directly.
body_of() {
  awk 'BEGIN{d=0} /^---$/{d++; next} d>=2' "$1" | grep -v 'CODEOPS-GENERATED'
}

PLUGIN_VERSION="$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  "$REPO_ROOT/.claude-plugin/plugin.json" | head -1)"

printf '\033[1mCodeOps agent-sync engine — specification suite\033[0m\n'
printf 'engine: %s\nplugin version: %s\n' "$SYNC" "$PLUGIN_VERSION"

# -----------------------------------------------------------------------------
# ST-1 — a repo with no quality-profile block is a no-op.
# -----------------------------------------------------------------------------
section "ST-1: no quality-profile block → no-op"
repo="$(mk_repo)"
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
[[ ! -d "$repo/.claude/agents" ]] && pass "no .claude/agents/ created" || fail ".claude/agents/ was created"
is_clean "$repo" && pass "repo untouched" || fail "repo was modified"

# -----------------------------------------------------------------------------
# ST-2 — an empty agent_models map materializes nothing.
# -----------------------------------------------------------------------------
section "ST-2: empty agent_models → nothing materialized"
repo="$(mk_repo '{}')"
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
[[ -z "$(ls -A "$repo/.claude/agents" 2>/dev/null)" ]] && pass "no agent files" || fail "agent files were written"

# -----------------------------------------------------------------------------
# ST-3 — a model-only override does NOT materialize a file: model is applied at
# dispatch time and needs no fork.
# -----------------------------------------------------------------------------
section "ST-3: model-only override materializes no file"
repo="$(mk_repo '{codebase-scout: opus}')"
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
[[ ! -f "$repo/.claude/agents/codebase-scout.md" ]] && pass "no file for a model-only override" \
  || fail "model-only override materialized a file"

# -----------------------------------------------------------------------------
# ST-4 — an effort-bearing override materializes a stamped agent whose body is
# byte-identical to the plugin's and whose model falls back to the plugin's pin.
# -----------------------------------------------------------------------------
section "ST-4: effort override materializes a faithful, stamped agent"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo"
gen="$repo/.claude/agents/phase-reviewer.md"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
if [[ -f "$gen" ]]; then
  pass "materialized $(basename "$gen")"
  [[ "$(fm "$gen" effort)" == "xhigh" ]] && pass "effort: xhigh" || fail "effort is '$(fm "$gen" effort)'"
  [[ "$(fm "$gen" model)" == "$(fm "$REPO_ROOT/agents/phase-reviewer.md" model)" ]] \
    && pass "model inherited from the plugin pin" || fail "model is '$(fm "$gen" model)'"
  [[ "$(fm "$gen" name)" == "phase-reviewer" ]] && pass "name preserved" || fail "name is '$(fm "$gen" name)'"
  if diff -q <(body_of "$gen") <(body_of "$REPO_ROOT/agents/phase-reviewer.md") >/dev/null; then
    pass "body byte-identical to the plugin's"
  else
    fail "body drifted from the plugin's"
  fi
  grep -q 'CODEOPS-GENERATED' "$gen" && pass "carries the CODEOPS-GENERATED marker" || fail "no marker"
  grep -q "version=$PLUGIN_VERSION" "$gen" && pass "marker stamped $PLUGIN_VERSION" || fail "marker version stamp wrong/missing"
else
  fail "no file materialized for an effort override"
fi

# -----------------------------------------------------------------------------
# ST-5 — a {model, effort} override rewrites both fields.
# -----------------------------------------------------------------------------
section "ST-5: {model, effort} rewrites both"
repo="$(mk_repo '{security-auditor: {model: opus, effort: max}}')"
run_sync "$repo"
gen="$repo/.claude/agents/security-auditor.md"
if [[ -f "$gen" ]]; then
  [[ "$(fm "$gen" model)" == "opus" ]] && pass "model: opus" || fail "model is '$(fm "$gen" model)'"
  [[ "$(fm "$gen" effort)" == "max" ]] && pass "effort: max" || fail "effort is '$(fm "$gen" effort)'"
else
  fail "no file materialized"
fi

# -----------------------------------------------------------------------------
# ST-6 — a second run is a no-op: generated content is deterministic.
# -----------------------------------------------------------------------------
section "ST-6: idempotent"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo"
git -C "$repo" "${GIT_ID[@]}" add -A >/dev/null 2>&1
git -C "$repo" "${GIT_ID[@]}" commit -q -m "generated" >/dev/null 2>&1
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0 on re-run" || fail "exit $RC on re-run ($OUT)"
is_clean "$repo" && pass "second run changed nothing" || fail "second run rewrote the file"
grep -qi 'unchanged' <<<"$OUT" && pass "reports UNCHANGED" || fail "no UNCHANGED report: $OUT"

# -----------------------------------------------------------------------------
# ST-7 — a generated file stamped at an older version is regenerated. This is the
# staleness fix: a fork frozen at an old plugin release can never go unnoticed.
# -----------------------------------------------------------------------------
section "ST-7: stale stamp is regenerated"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo"
gen="$repo/.claude/agents/phase-reviewer.md"
if [[ -f "$gen" ]]; then
  sed -i "s/version=$PLUGIN_VERSION/version=0.0.1/" "$gen"
  printf 'STALE BODY LINE\n' >> "$gen"
  run_sync "$repo"
  grep -q "version=$PLUGIN_VERSION" "$gen" && pass "re-stamped to $PLUGIN_VERSION" || fail "stamp not refreshed"
  grep -q 'STALE BODY LINE' "$gen" && fail "stale body survived regeneration" || pass "stale body replaced"
  grep -qiE 'updated' <<<"$OUT" && pass "reports UPDATED" || fail "no UPDATED report: $OUT"
else
  fail "setup failed — no file materialized"
fi

# -----------------------------------------------------------------------------
# ST-8 — a hand-authored agent (no marker) is never overwritten.
# -----------------------------------------------------------------------------
section "ST-8: hand-authored agent is never overwritten"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
mkdir -p "$repo/.claude/agents"
printf -- '---\nname: phase-reviewer\nmodel: haiku\neffort: low\n---\n\nMY OWN PROMPT\n' \
  > "$repo/.claude/agents/phase-reviewer.md"
git -C "$repo" "${GIT_ID[@]}" add -A >/dev/null 2>&1
git -C "$repo" "${GIT_ID[@]}" commit -q -m "hand-authored" >/dev/null 2>&1
run_sync "$repo"
grep -q 'MY OWN PROMPT' "$repo/.claude/agents/phase-reviewer.md" && pass "hand-authored file preserved" \
  || fail "hand-authored file was overwritten"
is_clean "$repo" && pass "nothing rewritten" || fail "repo was modified"
grep -qiE 'skip' <<<"$OUT" && pass "reports SKIPPED" || fail "no SKIPPED report: $OUT"
[[ "$RC" -eq 0 ]] && pass "exit 0 (a deliberate fork is legal)" || fail "exit $RC, expected 0"

# -----------------------------------------------------------------------------
# ST-9 — withdrawing an override prunes its generated file; hand-authored files
# are never pruned.
# -----------------------------------------------------------------------------
section "ST-9: withdrawn override is pruned; hand-authored is not"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo"
mkdir -p "$repo/.claude/agents"
printf -- '---\nname: perf-auditor\nmodel: haiku\neffort: low\n---\n\nMINE\n' \
  > "$repo/.claude/agents/perf-auditor.md"
sed -i 's/^agent_models: .*/agent_models: {}/' "$repo/CLAUDE.md"
run_sync "$repo"
[[ ! -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "generated file pruned" || fail "generated file survived"
[[ -f "$repo/.claude/agents/perf-auditor.md" ]] && pass "hand-authored file kept" || fail "hand-authored file was pruned"
grep -qiE 'prune' <<<"$OUT" && pass "reports PRUNED" || fail "no PRUNED report: $OUT"

# -----------------------------------------------------------------------------
# ST-10 — --check reports drift and exits 1 without writing; exits 0 when in sync.
# -----------------------------------------------------------------------------
section "ST-10: --check reports drift, writes nothing"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo" --check
[[ "$RC" -eq 1 ]] && pass "exit 1 on drift" || fail "exit $RC on drift, expected 1 ($OUT)"
[[ ! -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "--check wrote nothing" || fail "--check wrote a file"
grep -qiE 'drift' <<<"$OUT" && pass "reports DRIFT" || fail "no DRIFT report: $OUT"
run_sync "$repo"
run_sync "$repo" --check
[[ "$RC" -eq 0 ]] && pass "exit 0 once in sync" || fail "exit $RC when in sync ($OUT)"

# -----------------------------------------------------------------------------
# ST-11 — an override naming an unknown agent warns and is ignored; the rest apply.
# -----------------------------------------------------------------------------
section "ST-11: unknown agent name warns, never blocks"
repo="$(mk_repo '{no-such-agent: {effort: xhigh}, phase-reviewer: {effort: xhigh}}')"
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
grep -qiE 'warn' <<<"$OUT" && pass "warns about the unknown name" || fail "no warning: $OUT"
[[ ! -f "$repo/.claude/agents/no-such-agent.md" ]] && pass "no file for the unknown agent" || fail "wrote an unknown agent"
[[ -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "the valid entry still applied" || fail "valid entry dropped"

# -----------------------------------------------------------------------------
# ST-12 — an effort outside low|medium|high|xhigh|max warns and is ignored.
# -----------------------------------------------------------------------------
section "ST-12: invalid effort warns, materializes nothing"
repo="$(mk_repo '{phase-reviewer: {effort: turbo}}')"
run_sync "$repo"
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
grep -qiE 'warn' <<<"$OUT" && pass "warns about the bad value" || fail "no warning: $OUT"
[[ ! -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "nothing materialized" || fail "materialized on a bad value"

# -----------------------------------------------------------------------------
# ST-13 — repo data is parsed, never executed.
# -----------------------------------------------------------------------------
section "ST-13: profile data is never executed"
repo="$(mk_repo '{phase-reviewer: {effort: $(touch /tmp/codeops-agents-pwned)}}')"
rm -f /tmp/codeops-agents-pwned
run_sync "$repo"
[[ ! -e /tmp/codeops-agents-pwned ]] && pass "no command substitution executed" || fail "profile data was executed"
rm -f /tmp/codeops-agents-pwned
[[ ! -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "nothing materialized from a bad value" \
  || fail "materialized from a bad value"

# -----------------------------------------------------------------------------
# ST-14 — --dry-run prints the would-be work and writes nothing.
# -----------------------------------------------------------------------------
section "ST-14: --dry-run writes nothing"
repo="$(mk_repo '{phase-reviewer: {effort: xhigh}}')"
run_sync "$repo" --dry-run
[[ "$RC" -eq 0 ]] && pass "exit 0" || fail "exit $RC, expected 0 ($OUT)"
[[ ! -f "$repo/.claude/agents/phase-reviewer.md" ]] && pass "wrote nothing" || fail "--dry-run wrote a file"
is_clean "$repo" && pass "repo untouched" || fail "repo was modified"

# -----------------------------------------------------------------------------
printf '\n'
if [[ "$FAILURES" -eq 0 ]]; then
  printf '\033[32mAll agent-sync checks passed.\033[0m\n'
  exit 0
fi
printf '\033[31m%d check(s) failed.\033[0m\n' "$FAILURES"
exit 1
