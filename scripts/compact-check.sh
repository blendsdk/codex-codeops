#!/usr/bin/env bash
#
# compact-check.sh — specification-test suite for the roadmap compact engine.
#
# Drives scripts/codeops-roadmap-compact.sh against TEMP COPIES of
# scripts/fixtures/bloated-repo/{flat,nested}/ and asserts the Notes-section removal, the
# byte-exact table/header preservation, the fat-cell flagging, the git-safety refusals, and
# idempotency. Each check corresponds to one specification case (ST-1…ST-9; edge rows added
# later). It is a specification test: written from the spec BEFORE the engine exists, so it is
# RED until codeops-roadmap-compact.sh lands and GREEN thereafter.
#
# It NEVER mutates a committed fixture — it always copies to a temp git repo and asserts the copy.
# The compact engine strips Notes but never rewrites a table cell; the `.expected` files are the
# engine's deterministic post-apply output (Notes gone, tables incl. any still-fat cell identical).
# The lean --check (ST-8) copy is built here by trimming the flagged cell (simulating the AI step).
#
# Usage:  ./scripts/compact-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

ENGINE="$REPO_ROOT/scripts/codeops-roadmap-compact.sh"
SYNC="$REPO_ROOT/scripts/codeops-roadmap-sync.sh"
FIXTURE_ROOT="$REPO_ROOT/scripts/fixtures/bloated-repo"

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

# make_repo <flat|nested> — copy that fixture into a fresh temp git repo (clean, committed).
make_repo() {
  local kind="$1" tmp
  tmp="$(mktemp -d)"
  TMP_DIRS+=("$tmp")
  cp -R "$FIXTURE_ROOT/$kind/." "$tmp/"
  git -C "$tmp" init -q
  git -C "$tmp" "${GIT_ID[@]}" add -A
  git -C "$tmp" "${GIT_ID[@]}" commit -q -m "fixture"
  printf '%s\n' "$tmp"
}

# make_repo_nogit <flat|nested> — copy the fixture into a temp dir that is NOT a git repo.
make_repo_nogit() {
  local kind="$1" tmp
  tmp="$(mktemp -d)"
  TMP_DIRS+=("$tmp")
  cp -R "$FIXTURE_ROOT/$kind/." "$tmp/"
  printf '%s\n' "$tmp"
}

is_clean() { [[ -z "$(git -C "$1" status --porcelain)" ]]; }
commit_all() { git -C "$1" "${GIT_ID[@]}" add -A && git -C "$1" "${GIT_ID[@]}" commit -q -m "${2:-snapshot}"; }

# run_engine <repo> <args...> — run the compact engine inside <repo>; set OUT + RC.
OUT=""
RC=0
run_engine() {
  local repo="$1"; shift
  if [[ ! -x "$ENGINE" ]]; then OUT=""; RC=127; return; fi
  OUT="$(cd "$repo" && "$ENGINE" "$@" 2>&1)"
  RC=$?
}

# assert_same <label> <fileA> <fileB> — byte-exact equality.
assert_same() {
  if diff -q "$2" "$3" >/dev/null 2>&1; then pass "$1"; else
    fail "$1 (files differ)"; diff "$2" "$3" | head -20 | sed 's/^/      /'
  fi
}

# -----------------------------------------------------------------------------
# Engine presence — without it every check below is red (the Phase 1 red state).
# -----------------------------------------------------------------------------
section "Engine: scripts/codeops-roadmap-compact.sh present and executable"
if [[ -x "$ENGINE" ]]; then
  pass "compact engine present and executable"
else
  fail "compact engine missing or not executable: $ENGINE"
fi

# -----------------------------------------------------------------------------
# ST-1 / ST-3 — apply on the bloated flat fixture (clean tree):
#   Notes removed; header + Tracker byte-identical to .expected; fat cell FLAGged, not rewritten.
# -----------------------------------------------------------------------------
section "ST-1 / ST-3: apply flat — strip Notes, preserve tables, flag fat cell"
repo="$(make_repo flat)"
run_engine "$repo"
if [[ "$RC" -eq 0 ]]; then pass "apply exited 0"; else fail "apply exited $RC"; fi
# ST-1: byte-exact preservation of the main roadmap and the archived roadmap.
assert_same "main roadmap == .expected (Notes gone, tables identical)" \
  "$repo/plans/00-roadmap.md" "$repo/plans/00-roadmap.md.expected"
assert_same "archive roadmap == .expected" \
  "$repo/plans/_archive/widget-v1/00-roadmap.md" "$repo/plans/_archive/widget-v1/00-roadmap.md.expected"
if ! grep -q '^## Notes' "$repo/plans/00-roadmap.md"; then
  pass "## Notes heading removed from the main roadmap"
else
  fail "## Notes heading still present in the main roadmap"
fi
# ST-3: the fat cell is FLAGged with its column name, and its text is left UNCHANGED by the engine.
if grep -qE 'FLAG plans/00-roadmap\.md:RD-02:Depends-on / Blocker \([0-9]+ chars\)' <<<"$OUT"; then
  pass "fat cell flagged: FLAG plans/00-roadmap.md:RD-02:Depends-on / Blocker (N chars)"
else
  fail "fat cell not flagged with the expected FLAG line"
fi
if grep -qF 'cascade resolution order after design changed the palette' "$repo/plans/00-roadmap.md"; then
  pass "engine left the fat cell text unchanged (flag only, no rewrite)"
else
  fail "engine altered the fat cell text (it must only flag, never rewrite)"
fi

# -----------------------------------------------------------------------------
# ST-2 — after apply, codeops-roadmap-sync.sh --check stays clean (tables/headers intact).
# -----------------------------------------------------------------------------
section "ST-2: sync --check clean after apply (counter surfaces untouched)"
sync_rc=0
if [[ -x "$SYNC" ]]; then
  (cd "$repo" && "$SYNC" --check) >/dev/null 2>&1 || sync_rc=$?
  if [[ "$sync_rc" -eq 0 ]]; then
    pass "codeops-roadmap-sync.sh --check exits 0 after compaction"
  else
    fail "sync --check reported drift after compaction (rc=$sync_rc)"
  fi
else
  fail "sync engine not found: $SYNC"
fi

# -----------------------------------------------------------------------------
# ST-6 — a second apply on the (committed) already-compacted repo is an idempotent no-op.
# The first apply left the tree dirty, so it must be committed before the second apply runs on a
# clean tree; the second finds no Notes to strip → "already lean", writes nothing.
# -----------------------------------------------------------------------------
section "ST-6: second apply is an idempotent no-op"
commit_all "$repo" "compacted"
run_engine "$repo"
if [[ "$RC" -eq 0 ]]; then pass "re-apply exited 0"; else fail "re-apply exited $RC"; fi
if grep -qi 'already lean' <<<"$OUT"; then
  pass "re-apply reports 'already lean — nothing to do'"
else
  fail "re-apply did not report the already-lean no-op"
fi
if is_clean "$repo"; then
  pass "re-apply changed nothing (tree clean)"
else
  fail "re-apply mutated an already-compacted repo"
fi

# -----------------------------------------------------------------------------
# ST-4 — apply refuses on a dirty tree (exit 1, "dirty"), modifying nothing.
# -----------------------------------------------------------------------------
section "ST-4: apply refuses on a dirty working tree"
repo_dirty="$(make_repo flat)"
printf '\nuncommitted edit\n' >>"$repo_dirty/plans/00-roadmap.md"
run_engine "$repo_dirty"
if [[ "$RC" -eq 1 ]] && grep -qi 'dirty' <<<"$OUT"; then
  pass "refused a dirty tree with a 'dirty' message (rc=1)"
else
  fail "did not refuse a dirty tree (rc=$RC)"
fi
if grep -q '^## Notes' "$repo_dirty/plans/00-roadmap.md"; then
  pass "no roadmap was modified on the dirty-tree refusal"
else
  fail "engine modified a roadmap despite the dirty-tree refusal"
fi

# -----------------------------------------------------------------------------
# ST-5 — apply refuses outside a git repository (exit 1), modifying nothing.
# -----------------------------------------------------------------------------
section "ST-5: apply refuses outside a git repository"
repo_nogit="$(make_repo_nogit flat)"
run_engine "$repo_nogit"
if [[ "$RC" -eq 1 ]] && grep -qi 'not inside a git repository' <<<"$OUT"; then
  pass "refused a non-git tree with a clear message (rc=1)"
else
  fail "did not refuse outside a git repo (rc=$RC)"
fi
if grep -q '^## Notes' "$repo_nogit/plans/00-roadmap.md"; then
  pass "no roadmap was modified outside a git repo"
else
  fail "engine modified a roadmap outside a git repo"
fi

# -----------------------------------------------------------------------------
# ST-7 — apply on the bloated NESTED fixture: Notes stripped from portfolio + feature + archive;
# all three tables byte-identical to their .expected.
# -----------------------------------------------------------------------------
section "ST-7: apply nested — portfolio + feature + archive all compacted"
repo_nested="$(make_repo nested)"
run_engine "$repo_nested"
if [[ "$RC" -eq 0 ]]; then pass "nested apply exited 0"; else fail "nested apply exited $RC"; fi
assert_same "portfolio == .expected" \
  "$repo_nested/codeops/00-roadmap.md" "$repo_nested/codeops/00-roadmap.md.expected"
assert_same "feature roadmap == .expected" \
  "$repo_nested/codeops/features/widgets/00-roadmap.md" "$repo_nested/codeops/features/widgets/00-roadmap.md.expected"
assert_same "nested archive == .expected" \
  "$repo_nested/codeops/_archive/legacy-ui/00-roadmap.md" "$repo_nested/codeops/_archive/legacy-ui/00-roadmap.md.expected"
nested_notes=0
for f in codeops/00-roadmap.md codeops/features/widgets/00-roadmap.md codeops/_archive/legacy-ui/00-roadmap.md; do
  grep -q '^## Notes' "$repo_nested/$f" && nested_notes=1
done
if [[ "$nested_notes" -eq 0 ]]; then
  pass "## Notes removed from all three nested roadmaps"
else
  fail "a nested roadmap still carries a ## Notes section"
fi
# The portfolio's fat Stage Summary cell is flagged (by its column name), not rewritten.
if grep -qE 'FLAG codeops/00-roadmap\.md:widgets:Stage Summary \([0-9]+ chars\)' <<<"$OUT"; then
  pass "portfolio fat cell flagged: FLAG codeops/00-roadmap.md:widgets:Stage Summary (N chars)"
else
  fail "portfolio Stage Summary fat cell not flagged"
fi

# -----------------------------------------------------------------------------
# ST-8 — --check reports drift on a bloated repo (exit 1, lists Notes + fat cell); on a fully-lean
# repo it exits 0. The lean repo is built by applying then trimming the flagged cell.
# -----------------------------------------------------------------------------
section "ST-8: --check drift detection (bloated → 1, lean → 0)"
repo_check="$(make_repo flat)"
run_engine "$repo_check" --check
if [[ "$RC" -eq 1 ]] && grep -qi 'notes' <<<"$OUT" && grep -q 'FLAG' <<<"$OUT"; then
  pass "--check on the bloated repo exits 1 and lists the Notes section + fat cell"
else
  fail "--check did not report drift on the bloated repo (rc=$RC)"
fi
# Build the fully-lean state: apply (strip Notes), then trim the one flagged cell (AI's job).
run_engine "$repo_check"
python3 - "$repo_check/plans/00-roadmap.md" <<'PY'
import re, sys
p = sys.argv[1]
t = open(p, encoding='utf-8').read()
# Trim RD-02's Depends-on/Blocker cell to a terse phrase (what the compact action would write).
t = re.sub(r'(\| RD-02 \| Theme tokens \|.*?\| 2025-05-15 \| )[^|]*( \|)',
           r'\1depends on RD-01\2', t)
open(p, 'w', encoding='utf-8').write(t)
PY
run_engine "$repo_check" --check
if [[ "$RC" -eq 0 ]]; then
  pass "--check on the fully-lean repo exits 0"
else
  fail "--check still reported drift on a lean repo (rc=$RC): $OUT"
fi

# -----------------------------------------------------------------------------
# ST-9 — --dry-run previews WOULD-STRIP + FLAG and changes nothing (exit 0).
# -----------------------------------------------------------------------------
section "ST-9: --dry-run previews and writes nothing"
repo_dry="$(make_repo flat)"
run_engine "$repo_dry" --dry-run
if [[ "$RC" -eq 0 ]]; then pass "--dry-run exited 0"; else fail "--dry-run exited $RC"; fi
if grep -q 'WOULD-STRIP' <<<"$OUT"; then
  pass "--dry-run prints WOULD-STRIP for the Notes section"
else
  fail "--dry-run did not print WOULD-STRIP"
fi
if grep -q 'FLAG' <<<"$OUT"; then
  pass "--dry-run prints FLAG for the fat cell"
else
  fail "--dry-run did not print FLAG"
fi
if is_clean "$repo_dry"; then
  pass "--dry-run wrote nothing (tree clean)"
else
  fail "--dry-run mutated the working tree"
fi

# =============================================================================
# Edge cases (implementation tests — internals + boundaries).
# =============================================================================

# mk_git_repo — fresh temp git repo; echo path. Caller writes files, then commit_all.
mk_git_repo() {
  local tmp; tmp="$(mktemp -d)"; TMP_DIRS+=("$tmp")
  git -C "$tmp" init -q
  printf '%s\n' "$tmp"
}

# -----------------------------------------------------------------------------
# Edge: a roadmap with NO ## Notes section and no fat cell → apply is a clean no-op.
# -----------------------------------------------------------------------------
section "Edge: roadmap with no ## Notes section → apply no-op"
repo_none="$(mk_git_repo)"; mkdir -p "$repo_none/plans"
cat >"$repo_none/plans/00-roadmap.md" <<'MD'
# Roadmap: Lean

> **Progress**: 0 / 1 (0%)

## Tracker

| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |
|----|-------|----|------|-------|--------|--------------|----------------------|
| RD-01 | Thing | — | — | Backlog | ⬜ | 2025-01-01 | — |
MD
commit_all "$repo_none" "lean" >/dev/null
run_engine "$repo_none"
if [[ "$RC" -eq 0 ]] && grep -qi 'already lean' <<<"$OUT" && is_clean "$repo_none"; then
  pass "no-Notes roadmap → already-lean no-op, tree clean"
else
  fail "no-Notes roadmap was not a clean no-op (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# Edge: a "## Notes"-like string inside a table cell must NOT be treated as a heading — only the
# real ## Notes section is removed; the cell mention survives verbatim.
# -----------------------------------------------------------------------------
section "Edge: '## Notes' text inside a cell is not a heading"
repo_word="$(mk_git_repo)"; mkdir -p "$repo_word/plans"
cat >"$repo_word/plans/00-roadmap.md" <<'MD'
# Roadmap: Wordy

> **Progress**: 0 / 1 (0%)

## Tracker

| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |
|----|-------|----|------|-------|--------|--------------|----------------------|
| RD-01 | Thing | — | — | Backlog | ⬜ | 2025-01-01 | documented under ## Notes |

## Notes

- 2025-01-01: this real section must be removed.
MD
commit_all "$repo_word" "wordy" >/dev/null
run_engine "$repo_word"
if [[ "$RC" -eq 0 ]] \
   && ! grep -q '^## Notes' "$repo_word/plans/00-roadmap.md" \
   && grep -qF 'documented under ## Notes' "$repo_word/plans/00-roadmap.md"; then
  pass "real ## Notes section removed; in-cell '## Notes' mention preserved"
else
  fail "heading-anchored removal mishandled the in-cell '## Notes' text (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# Edge: empty repo (no roadmap) → apply is a clean no-op, exit 0.
# -----------------------------------------------------------------------------
section "Edge: empty repo → apply no-op"
repo_empty="$(mk_git_repo)"
printf '# placeholder\n' >"$repo_empty/README.md"
commit_all "$repo_empty" "empty" >/dev/null
run_engine "$repo_empty"
if [[ "$RC" -eq 0 ]] && grep -qi 'nothing to do' <<<"$OUT" && is_clean "$repo_empty"; then
  pass "empty repo → already-lean no-op, tree clean"
else
  fail "empty repo was not a clean no-op (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# Edge: ## Notes is NOT the last section — heading-anchored removal stops at the next `## `, so a
# following ## Archived section survives byte-for-byte.
# -----------------------------------------------------------------------------
section "Edge: ## Notes not last — following ## Archived survives"
repo_mid="$(mk_git_repo)"; mkdir -p "$repo_mid/plans"
cat >"$repo_mid/plans/00-roadmap.md" <<'MD'
# Roadmap: Mid

> **Progress**: 0 / 1 (0%)

## Tracker

| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |
|----|-------|----|------|-------|--------|--------------|----------------------|
| RD-01 | Thing | — | — | Backlog | ⬜ | 2025-01-01 | — |

## Notes

- 2025-01-01: remove me but stop at the next heading.

## Archived

| ID | Title | Completed |
|----|-------|-----------|
| RD-00 | Legacy | 2024-01-01 |
MD
commit_all "$repo_mid" "mid" >/dev/null
run_engine "$repo_mid"
if [[ "$RC" -eq 0 ]] \
   && ! grep -q '^## Notes' "$repo_mid/plans/00-roadmap.md" \
   && grep -q '^## Archived' "$repo_mid/plans/00-roadmap.md" \
   && grep -qF '| RD-00 | Legacy | 2024-01-01 |' "$repo_mid/plans/00-roadmap.md"; then
  pass "## Notes removed; the following ## Archived section survived"
else
  fail "removal did not stop at the next heading (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# Edge: fat-cell threshold is > 200 — a 199-char cell is not flagged; a 201-char cell is.
# -----------------------------------------------------------------------------
section "Edge: fat-cell threshold (199 not flagged, 201 flagged)"
repo_thr="$(mk_git_repo)"; mkdir -p "$repo_thr/plans"
python3 - "$repo_thr/plans/00-roadmap.md" <<'PY'
import sys
p = sys.argv[1]
c199, c201 = 'x' * 199, 'x' * 201
out = (
    "# Roadmap: Threshold\n\n"
    "> **Progress**: 0 / 2 (0%)\n\n"
    "## Tracker\n\n"
    "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
    "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
    f"| RD-01 | Under | — | — | Backlog | ⬜ | 2025-01-01 | {c199} |\n"
    f"| RD-02 | Over  | — | — | Backlog | ⬜ | 2025-01-01 | {c201} |\n"
)
open(p, 'w', encoding='utf-8').write(out)
PY
commit_all "$repo_thr" "thr" >/dev/null
run_engine "$repo_thr" --check
if grep -q 'FLAG plans/00-roadmap.md:RD-02:' <<<"$OUT" && ! grep -q 'FLAG plans/00-roadmap.md:RD-01:' <<<"$OUT"; then
  pass "201-char cell flagged; 199-char cell not flagged (threshold > 200)"
else
  fail "fat-cell threshold wrong at the 200-char boundary"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Summary"
if [[ "$FAILURES" -eq 0 ]]; then
  printf '  \033[32mAll compact checks passed.\033[0m\n'
  exit 0
else
  printf '  \033[31m%d compact check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
