#!/usr/bin/env bash
#
# migration-check.sh — specification-test suite for the flat→nested migration engine.
#
# Drives scripts/codeops-migrate.sh against a TEMP COPY of scripts/fixtures/flat-repo/ and
# asserts the computed move map, the hazard warnings, the security refusals, and idempotency.
# Each check maps to a SPEC-* case in plans/codeops-v2-layout/07-testing-strategy.md
# (SPEC-7…SPEC-15). It is a specification test: written from the spec BEFORE the engine exists,
# so it is RED until scripts/codeops-migrate.sh lands (Phase 3) and GREEN thereafter.
#
# It NEVER mutates the committed fixture — it always copies to a temp git repo and asserts the
# copy. The dry-run must change nothing; the apply check runs on its own throwaway repo.
#
# Usage:  ./scripts/migration-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENGINE="$REPO_ROOT/scripts/codeops-migrate.sh"
FIXTURE="$REPO_ROOT/scripts/fixtures/flat-repo"
SLUG="billing-platform"   # expected slug derived from the roadmap header "Billing Platform"

FAILURES=0

pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# Temp dirs created during the run, cleaned up on exit.
TMP_DIRS=()
cleanup() {
  for d in "${TMP_DIRS[@]:-}"; do
    [[ -n "$d" && -d "$d" ]] && rm -rf "$d"
  done
}
trap cleanup EXIT

# make_repo — copy the fixture into a fresh temp git repo (clean, committed) and echo its path.
# Migration requires a clean git repo (git mv + dirty-tree refusal), so the test provides one.
make_repo() {
  local tmp
  tmp="$(mktemp -d)"
  TMP_DIRS+=("$tmp")
  cp -R "$FIXTURE/." "$tmp/"
  git -C "$tmp" init -q
  git -C "$tmp" -c user.email=test@example.com -c user.name=test add -A
  git -C "$tmp" -c user.email=test@example.com -c user.name=test commit -q -m "fixture"
  printf '%s\n' "$tmp"
}

# is_clean <dir> — true if the git working tree has no uncommitted changes.
is_clean() {
  [[ -z "$(git -C "$1" status --porcelain)" ]]
}

# -----------------------------------------------------------------------------
# Engine presence — without it every check below is red (the Phase 1 red state).
# -----------------------------------------------------------------------------
section "Engine: scripts/codeops-migrate.sh present and executable"
if [[ -x "$ENGINE" ]]; then
  pass "migration engine present and executable"
else
  fail "migration engine missing or not executable: $ENGINE"
  # Continue so the full set of expected-red checks is reported, but each engine call
  # below will fail fast.
fi

# run_engine <repo> <args...> — run the engine inside <repo>, capture stdout+stderr and exit code.
# Sets globals OUT (combined output) and RC (exit code). Safe to call when the engine is absent.
OUT=""
RC=0
run_engine() {
  local repo="$1"; shift
  if [[ ! -x "$ENGINE" ]]; then
    OUT=""
    RC=127
    return
  fi
  OUT="$(cd "$repo" && "$ENGINE" "$@" 2>&1)"
  RC=$?
}

# -----------------------------------------------------------------------------
# SPEC-7 — dry-run move map + portfolio seed, with ZERO file changes
# SPEC-9 — plans/_archive/<set>/ routes to codeops/_archive/<set>/
# -----------------------------------------------------------------------------
section "SPEC-7 / SPEC-9: dry-run move map (zero changes)"
repo="$(make_repo)"
run_engine "$repo" --dry-run
expected_moves=(
  "MOVE requirements/ -> codeops/features/$SLUG/requirements/"
  "MOVE plans/invoicing/ -> codeops/features/$SLUG/plans/invoicing/"
  "MOVE plans/legacy/ -> codeops/features/$SLUG/plans/legacy/"
  "MOVE plans/00-roadmap.md -> codeops/features/$SLUG/00-roadmap.md"
  "MOVE plans/_archive/billing-v1/ -> codeops/_archive/billing-v1/"
  "CREATE codeops/.codeops.yml"
  "CREATE codeops/codeops.json"
  "CREATE codeops/00-roadmap.md"
)
for line in "${expected_moves[@]}"; do
  if grep -qF -- "$line" <<<"$OUT"; then
    pass "move map: $line"
  else
    fail "move map missing line: $line"
  fi
done
if grep -qiE 'SLUG:[[:space:]]*'"$SLUG"'[[:space:]]+\(source:[[:space:]]*roadmap' <<<"$OUT"; then
  pass "slug derived from roadmap header → $SLUG"
else
  fail "slug line not found / not sourced from roadmap header (expected $SLUG)"
fi
if is_clean "$repo"; then
  pass "dry-run made zero changes (tree clean)"
else
  fail "dry-run mutated the working tree (must change nothing)"
fi

# -----------------------------------------------------------------------------
# SPEC-10 — plan folder on disk not in the roadmap is migrated AND warned
# SPEC-11 — source-relative link surfaced as a warning, not rewritten
# -----------------------------------------------------------------------------
section "SPEC-10 / SPEC-11: hazard warnings"
if grep -qiE 'WARN.*plans/legacy/?' <<<"$OUT"; then
  pass "warns: plans/legacy not listed in the roadmap"
else
  fail "no warning for the plan folder absent from the roadmap (plans/legacy)"
fi
if grep -qiE 'WARN.*03-old\.md.*\.\./\.\./src/pay\.ts' <<<"$OUT"; then
  pass "warns: source-relative link in plans/legacy/03-old.md"
else
  fail "no warning for the source-relative link (../../src/pay.ts)"
fi

# -----------------------------------------------------------------------------
# Regression: a loose file directly under plans/ (not 00-roadmap.md, not in a plan dir) must be
# surfaced, never silently orphaned. The move map only relocates plan dirs + plans/00-roadmap.md.
# -----------------------------------------------------------------------------
section "Regression: loose file under plans/ is warned (not silently left behind)"
repo_loose="$(make_repo)"
printf '# stray\n' >"$repo_loose/plans/NOTES.md"
git -C "$repo_loose" -c user.email=test@example.com -c user.name=test add -A
git -C "$repo_loose" -c user.email=test@example.com -c user.name=test commit -q -m "loose file"
run_engine "$repo_loose" --dry-run
if grep -qiE 'WARN.*plans/NOTES\.md' <<<"$OUT"; then
  pass "warns: plans/NOTES.md is a loose file that won't be migrated"
else
  fail "no warning for the loose file plans/NOTES.md (would be silently orphaned)"
fi

# -----------------------------------------------------------------------------
# SPEC-8 — no roadmap → slug falls back to the repo/dir name; preview states the source
# -----------------------------------------------------------------------------
section "SPEC-8: slug fallback when no roadmap header"
repo_noroadmap="$(make_repo)"
# Remove the roadmap so the slug must fall back to the directory name.
git -C "$repo_noroadmap" -c user.email=test@example.com -c user.name=test rm -q "plans/00-roadmap.md"
git -C "$repo_noroadmap" -c user.email=test@example.com -c user.name=test commit -q -m "drop roadmap"
run_engine "$repo_noroadmap" --dry-run
# The spec slugifies the fallback dir name too (03-02 step 1), and the temp dir's mktemp name is
# not slug-safe, so assert the SPEC essence: the slug is sourced from the dir name and is a single
# safe path component — not that it equals the raw, un-slugified basename.
noroad_slug="$(grep -iE '^SLUG:' <<<"$OUT" | head -1 | sed -E 's/^SLUG:[[:space:]]*//; s/[[:space:]].*$//')"
if grep -qiE 'SLUG:.*\(source:[[:space:]]*(dir|repo)' <<<"$OUT" \
   && [[ -n "$noroad_slug" && "$noroad_slug" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  pass "slug falls back to a safe dir-name slug ($noroad_slug) with stated source"
else
  fail "no dir-name slug fallback / source not stated when roadmap absent (slug='$noroad_slug')"
fi

# -----------------------------------------------------------------------------
# SPEC-12 — dirty working tree → refuse, no changes
# -----------------------------------------------------------------------------
section "SPEC-12: dirty working tree refusal"
repo_dirty="$(make_repo)"
printf 'uncommitted\n' >>"$repo_dirty/requirements/RD-01-invoicing.md"
run_engine "$repo_dirty" --dry-run
if [[ "$RC" -ne 0 ]] && grep -qiE 'dirty|uncommitted|clean' <<<"$OUT"; then
  pass "refuses on a dirty tree with a clear message (rc=$RC)"
else
  fail "did not refuse on a dirty tree (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# SPEC-14 — feature slug resolving to ../absolute/separators → rejected/normalized
# -----------------------------------------------------------------------------
section "SPEC-14: path-traversal slug is rejected or normalized"
repo_evil="$(make_repo)"
# Inject a hostile Feature-Set header; the engine must not let it escape codeops/.
python3 - "$repo_evil/plans/00-roadmap.md" <<'PY'
import re, sys
p = sys.argv[1]
text = open(p).read()
text = re.sub(r'(?m)^> \*\*Feature-Set\*\*:.*$', '> **Feature-Set**: ../../etc/evil', text)
open(p, "w").write(text)
PY
git -C "$repo_evil" -c user.email=test@example.com -c user.name=test commit -aq -m "hostile slug"
run_engine "$repo_evil" --dry-run
# Accept either refusal (non-zero) or normalization to a safe slug with no separators / "..".
evil_slug="$(grep -iE '^SLUG:' <<<"$OUT" | head -1 | sed -E 's/^SLUG:[[:space:]]*//; s/[[:space:]].*$//')"
if [[ "$RC" -ne 0 ]]; then
  pass "rejected the path-traversal slug (rc=$RC)"
elif [[ -n "$evil_slug" && "$evil_slug" =~ ^[a-z0-9][a-z0-9-]*$ ]]; then
  pass "normalized the hostile header to a safe slug ($evil_slug)"
else
  fail "path-traversal slug neither rejected nor normalized (slug='$evil_slug', rc=$RC)"
fi

# -----------------------------------------------------------------------------
# SPEC-15 — apply (non-dry-run) on a temp copy: nested tree, git history, marker last
# SPEC-13 — re-run after migration is an idempotent no-op
# -----------------------------------------------------------------------------
section "SPEC-15 / SPEC-13: apply round-trip + idempotent re-run"
repo_apply="$(make_repo)"
run_engine "$repo_apply" --yes
if [[ "$RC" -eq 0 ]]; then
  pass "apply completed (rc=0)"
else
  fail "apply failed (rc=$RC)"
fi
# Nested tree exists where expected.
apply_ok=1
for path in \
  "codeops/.codeops.yml" \
  "codeops/00-roadmap.md" \
  "codeops/features/$SLUG/00-roadmap.md" \
  "codeops/features/$SLUG/requirements/RD-01-invoicing.md" \
  "codeops/features/$SLUG/plans/invoicing/99-execution-plan.md" \
  "codeops/_archive/billing-v1/00-index.md"; do
  if [[ ! -e "$repo_apply/$path" ]]; then
    fail "apply: expected path missing → $path"
    apply_ok=0
  fi
done
[[ "$apply_ok" -eq 1 ]] && pass "apply produced the expected nested tree"
# The emitted marker carries integrationBranch (FR-4 — parallel-agents onboarding).
if grep -qE '^integrationBranch:[[:space:]]*\S' "$repo_apply/codeops/.codeops.yml" 2>/dev/null; then
  pass "apply: marker carries integrationBranch"
else
  fail "apply: marker missing integrationBranch (FR-4)"
fi
# The seeded portfolio must ship lean — no `## Notes` running log (the migration status lives in
# the feature row's Stage Summary, not a Notes log).
if grep -q '^## Notes' "$repo_apply/codeops/00-roadmap.md"; then
  fail "seeded portfolio still carries a ## Notes running log (must ship lean)"
else
  pass "seeded portfolio ships lean (no ## Notes section)"
fi
# Old flat dirs are gone (moved, not copied).
if [[ ! -e "$repo_apply/requirements" && ! -e "$repo_apply/plans" ]]; then
  pass "apply removed the old flat requirements/ and plans/ trees"
else
  fail "apply left flat requirements/ or plans/ behind (should be git mv, not copy)"
fi
# git mv preserves history: the moved RD is tracked at its new path.
if git -C "$repo_apply" ls-files --error-unmatch "codeops/features/$SLUG/requirements/RD-01-invoicing.md" >/dev/null 2>&1; then
  pass "git tracks the moved file at its new path (history preserved)"
else
  fail "moved file is not git-tracked at its new path"
fi
# Idempotent re-run: marker present → no-op, exit 0, no changes.
git -C "$repo_apply" -c user.email=test@example.com -c user.name=test add -A >/dev/null 2>&1
git -C "$repo_apply" -c user.email=test@example.com -c user.name=test commit -q -m "migrated" >/dev/null 2>&1
run_engine "$repo_apply" --yes
if [[ "$RC" -eq 0 ]] && grep -qiE 'already|no-op|nothing to' <<<"$OUT" && is_clean "$repo_apply"; then
  pass "re-run is an idempotent no-op (rc=0, tree clean)"
else
  fail "re-run was not an idempotent no-op (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# ST-H1 — apply-path failure handling (plans/codeops-v3-hardening/07-testing-strategy.md).
# A tracked regular FILE named `codeops` makes every apply step impossible. The engine must
# refuse/abort with a non-zero exit, must NOT print the success line, must NOT write the marker,
# and must leave the tree restorable. Spec: 03-01-migration-engine.md (AR #18).
# -----------------------------------------------------------------------------
section "ST-H1: apply failure → non-zero exit, no marker, no false 'applied'"
repo_blocked="$(make_repo)"
printf 'not a directory\n' >"$repo_blocked/codeops"
git -C "$repo_blocked" -c user.email=test@example.com -c user.name=test add -A
git -C "$repo_blocked" -c user.email=test@example.com -c user.name=test commit -q -m "blocking file"
run_engine "$repo_blocked" --yes
if [[ "$RC" -ne 0 ]]; then
  pass "apply exits non-zero when it cannot proceed (rc=$RC)"
else
  fail "apply exited 0 despite a blocking 'codeops' file (must be non-zero)"
fi
if ! grep -qiE 'applied\.' <<<"$OUT"; then
  pass "no false 'applied.' success line"
else
  fail "printed 'applied.' although the migration could not succeed"
fi
if grep -qiE 'FAILED|refus|cannot|not a directory' <<<"$OUT"; then
  pass "failure output names the problem"
else
  fail "failure output does not explain what went wrong"
fi
if [[ ! -f "$repo_blocked/codeops/.codeops.yml" ]] \
   && ! git -C "$repo_blocked" ls-files --error-unmatch "codeops/.codeops.yml" >/dev/null 2>&1; then
  pass "no layout marker written on failure"
else
  fail "layout marker exists after a failed apply (bricks retry via the idempotency guard)"
fi

portfolio_end_line="$(grep -n '^PORTFOLIO$' "$ENGINE" | tail -1 | cut -d: -f1)"
marker_line="$(grep -n '^cat > codeops/\.codeops\.yml' "$ENGINE" | tail -1 | cut -d: -f1)"
success_line="$(grep -n "^printf.*codeops-migrate: applied" "$ENGINE" | tail -1 | cut -d: -f1)"
if [[ -n "$portfolio_end_line" && -n "$marker_line" && -n "$success_line" \
   && "$portfolio_end_line" -lt "$marker_line" && "$marker_line" -lt "$success_line" ]]; then
  pass "layout marker is written after required artifacts and before success"
else
  fail "layout marker is not the final commit point after required artifacts"
fi

# -----------------------------------------------------------------------------
# ST-H2 — loose FILE under plans/_archive/ must be warned in dry-run and relocated on apply,
# never silently orphaned in a residual plans/ tree. Spec: 03-01-migration-engine.md (AR #18).
# -----------------------------------------------------------------------------
section "ST-H2: loose file under plans/_archive/ (warned + relocated)"
repo_archloose="$(make_repo)"
printf '# archive readme\n' >"$repo_archloose/plans/_archive/README.md"
git -C "$repo_archloose" -c user.email=test@example.com -c user.name=test add -A
git -C "$repo_archloose" -c user.email=test@example.com -c user.name=test commit -q -m "archive loose file"
run_engine "$repo_archloose" --dry-run
if grep -qiE 'WARN.*plans/_archive/README\.md' <<<"$OUT"; then
  pass "dry-run warns about plans/_archive/README.md"
else
  fail "dry-run does not warn about the loose archive file"
fi
run_engine "$repo_archloose" --yes
if [[ "$RC" -eq 0 && -f "$repo_archloose/codeops/_archive/README.md" ]]; then
  pass "apply relocated the loose archive file to codeops/_archive/"
else
  fail "apply did not relocate plans/_archive/README.md (rc=$RC)"
fi
if [[ ! -e "$repo_archloose/plans" ]]; then
  pass "no residual plans/ tree after apply"
else
  fail "residual plans/ tree left behind after apply (silent half-migration)"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Summary"
if [[ "$FAILURES" -eq 0 ]]; then
  printf '  \033[32mAll migration checks passed.\033[0m\n'
  exit 0
else
  printf '  \033[31m%d migration check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
