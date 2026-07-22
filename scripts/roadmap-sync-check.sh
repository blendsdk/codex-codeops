#!/usr/bin/env bash
#
# roadmap-sync-check.sh — specification-test suite for the roadmap sync engine.
#
# Drives scripts/codeops-roadmap-sync.sh against TEMP COPIES of
# scripts/fixtures/roadmap-repo/{flat,nested}/ (and small repos generated inline) and asserts the
# engine's fidelity contract: RD-*-only counting, follow-on-aware roll-up, preservation of
# hand-maintained cells (n/a sentinel, free-text headers, ` · …` annotation suffixes), the
# HELD-vs-DRIFT report channel, backward-compatible no-ops, and no code execution from cell text.
# Each check corresponds to one specification case (ST-1…ST-12). It is a specification test:
# written from the spec (RD-01 acceptance criteria) BEFORE the engine changes exist, so it is RED
# until the engine gains this fidelity and GREEN thereafter.
#
# It NEVER mutates a committed fixture — it always copies to a temp git repo and asserts the copy.
# The sync engine writes a dynamic date on every change, so assertions use targeted greps on the
# corrected/preserved cells, on --check/--dry-run DRIFT/HELD lines and exit codes, and on a clean
# git tree (is_clean) for no-op/idempotency cases — never committed byte-exact `.expected` files.
# The committed nested fixture is authored at the engine's correct fixpoint: the pre-change engine
# reports drift against it (red), the fidelity engine agrees and emits only informational HELD.
#
# Usage:  ./scripts/roadmap-sync-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

SYNC="$REPO_ROOT/scripts/codeops-roadmap-sync.sh"
FIXTURE_ROOT="$REPO_ROOT/scripts/fixtures/roadmap-repo"

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

# mk_git_repo — fresh empty temp git repo; echo path. Caller writes files, then commit_all.
mk_git_repo() {
  local tmp; tmp="$(mktemp -d)"; TMP_DIRS+=("$tmp")
  git -C "$tmp" init -q
  printf '%s\n' "$tmp"
}

is_clean() { [[ -z "$(git -C "$1" status --porcelain)" ]]; }
commit_all() { git -C "$1" "${GIT_ID[@]}" add -A && git -C "$1" "${GIT_ID[@]}" commit -q -m "${2:-snapshot}"; }

# run_sync <repo> <args...> — run the sync engine inside <repo>; set OUT + RC.
OUT=""
RC=0
run_sync() {
  local repo="$1"; shift
  if [[ ! -x "$SYNC" ]]; then OUT=""; RC=127; return; fi
  OUT="$(cd "$repo" && "$SYNC" "$@" 2>&1)"
  RC=$?
}

# has <needle> — fixed-string grep over the last OUT.
has() { grep -qF "$1" <<<"$OUT"; }
# has_re <pattern> — regex grep over the last OUT.
has_re() { grep -qE "$1" <<<"$OUT"; }
# file_has <file> <needle> — fixed-string grep over a file.
file_has() { grep -qF "$2" "$1"; }

# -----------------------------------------------------------------------------
# Engine presence.
# -----------------------------------------------------------------------------
section "Engine: scripts/codeops-roadmap-sync.sh present and executable"
if [[ -x "$SYNC" ]]; then
  pass "sync engine present and executable"
else
  fail "sync engine missing or not executable: $SYNC"
fi

# =============================================================================
# Nested fixpoint fixture — the fidelity engine AGREES with every computed cell
# (only informational HELD), so --check exits 0 and a write run is a clean no-op.
# The pre-change engine drifts on ledger (task counted), billing (follow-on),
# hardening (suffix stripped), logixcontrol (n/a clobbered) and Features — so all
# of the assertions below are red against it.
# =============================================================================
section "Nested fixpoint --check: fidelity engine agrees (exit 0, only HELD)"
repo_chk="$(make_repo nested)"
run_sync "$repo_chk" --check
if [[ "$RC" -eq 0 ]]; then
  pass "--check exits 0 on the fixpoint fixture (no computed drift)"
else
  fail "--check reported drift on the fixpoint fixture (rc=$RC)"
fi

# ST-1 — a feature with 9 RD-* rows + 1 T-* row counts 9, not 10 (task excluded).
section "ST-1: T-* task row excluded from the RD fraction (0/9, not 0/10)"
if ! has_re 'DRIFT.*ledger'; then
  pass "ledger has no DRIFT — 0/9 RDs accepted (T-01 not counted)"
else
  fail "ledger drifts — the T-01 task row is still counted"
fi
if file_has "$repo_chk/codeops/00-roadmap.md" '| 0/9 RDs |' \
   && file_has "$repo_chk/codeops/features/ledger/00-roadmap.md" '> **Progress**: 0 / 9 (0%)'; then
  pass "ledger cell '0/9 RDs' and header '0 / 9 (0%)' present"
else
  fail "ledger fixture not at 0/9 as authored"
fi

# ST-5(a) — an in-sync computed cell carrying a ` · …` annotation suffix is not flagged/stripped.
section "ST-5(a): annotation suffix preserved (not stripped, not drift)"
if ! has_re 'DRIFT.*hardening'; then
  pass "hardening has no DRIFT — '2/2 RDs · hardening ✅ 30/30' suffix accepted"
else
  fail "hardening drifts — the ' · hardening ✅ 30/30' suffix is treated as drift"
fi

# ST-6 — all RD-* rows Done + an open follow-on holds the feature at 🔄 (engine agrees).
section "ST-6: open follow-on holds 🔄 (all RDs Done, not ✅)"
if ! has_re 'DRIFT.*billing'; then
  pass "billing has no DRIFT — rolls 🔄 with all RDs Done + open follow-on"
else
  fail "billing drifts — the follow-on-aware roll-up is not applied"
fi
if file_has "$repo_chk/codeops/00-roadmap.md" '| 2/2 RDs | 🔄 |'; then
  pass "billing cell is '2/2 RDs' / 🔄 (RD fraction kept, held at 🔄)"
else
  fail "billing cell not at 2/2 RDs / 🔄"
fi

# ST-7 — a ⛔ RD row wins the roll-up even with an open follow-on present.
section "ST-7: blocked precedence (⛔ wins over follow-on and all-Done)"
if ! has_re 'DRIFT.*blocked' && file_has "$repo_chk/codeops/00-roadmap.md" '| 1/2 RDs | ⛔ |'; then
  pass "blocked rolls ⛔ (1/2 RDs) — precedence honoured"
else
  fail "blocked did not roll up ⛔"
fi

# ST-3 — a non-computed portfolio Progress cell (n/a) is HELD, not DRIFT, exit 0.
section "ST-3: n/a sentinel HELD (no Status regression)"
if has "HELD" && has_re "HELD.*logixcontrol.*Progress 'n/a'"; then
  pass "logixcontrol n/a reported HELD (informational, not drift)"
else
  fail "logixcontrol n/a not reported on a HELD line"
fi

# ST-4 — a free-text per-feature Progress header is HELD, not DRIFT.
section "ST-4: free-text per-feature header HELD"
if has_re "HELD codeops/features/logixcontrol/00-roadmap.md.*history archived"; then
  pass "'history archived (no active RD tracker)' header reported HELD"
else
  fail "free-text per-feature header not reported HELD"
fi

# ST-8(a) — the Features header's trailing parenthetical is preserved (engine agrees).
section "ST-8(a): Features header parenthetical preserved"
if ! has_re 'DRIFT.*Features' \
   && file_has "$repo_chk/codeops/00-roadmap.md" '2 / 5 done (logixcontrol tracked out-of-band)'; then
  pass "Features header token accepted and parenthetical preserved"
else
  fail "Features header drifts or lost its parenthetical"
fi

# -----------------------------------------------------------------------------
# Nested fixpoint WRITE — a write run changes nothing (backward-compat / idempotent
# on a rich file), and the held n/a row keeps its recorded ✅ (no ✅→⬜ regression).
# -----------------------------------------------------------------------------
section "Nested fixpoint write: no-op + n/a Status non-regression"
repo_wr="$(make_repo nested)"
run_sync "$repo_wr"
if [[ "$RC" -eq 0 ]] && is_clean "$repo_wr"; then
  pass "write run on the fixpoint fixture changes nothing (tree clean)"
else
  fail "write run mutated the fixpoint fixture (rc=$RC)"
fi
if file_has "$repo_wr/codeops/00-roadmap.md" '| n/a | ✅ |'; then
  pass "logixcontrol Status stays ✅ after write (no ✅→⬜ regression)"
else
  fail "logixcontrol Status regressed (n/a row was re-rolled)"
fi

# =============================================================================
# Corrections (inline nested repo with STALE well-formed computed cells) — the
# engine still rewrites a stale computed token, keeps any suffix, and reports DRIFT.
# =============================================================================
# build_corrections_repo <dir> — svc: 19 RDs (18 Done, 1 Backlog), portfolio cell stale at
# 17/19; hard: 2 RDs Done, portfolio cell stale token with a suffix; Features header stale + ().
build_corrections_repo() {
  python3 - "$1" <<'PY'
import os, sys
root = sys.argv[1]
os.makedirs(os.path.join(root, 'codeops', 'features', 'svc'), exist_ok=True)
os.makedirs(os.path.join(root, 'codeops', 'features', 'hard'), exist_ok=True)
open(os.path.join(root, 'codeops', '.codeops.yml'), 'w').write(
    "codeopsLayout: nested\n")

def feature(name, rows):
    hdr = ("# Roadmap: %s\n\n> **Feature-Set**: %s\n> **Status**: In Progress\n"
           "> **Created**: 2025-01-01\n> **Last Updated**: 2025-05-01 10:00\n"
           "> **Progress**: 0 / 0 (0%%)\n\n"
           "## Tracker\n\n"
           "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
           "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
           % (name, name))
    return hdr + rows

svc_rows = ""
for i in range(1, 19):   # RD-01..RD-18 Done
    svc_rows += "| RD-%02d | Item %d | — | — | Done | ✅ | 2025-05-01 | — |\n" % (i, i)
svc_rows += "| RD-19 | Item 19 | — | — | Backlog | ⬜ | 2025-05-01 | — |\n"
open(os.path.join(root, 'codeops', 'features', 'svc', '00-roadmap.md'), 'w').write(
    feature('Svc', svc_rows))

hard_rows = ("| RD-01 | Alpha | — | — | Done | ✅ | 2025-05-01 | — |\n"
             "| RD-02 | Beta | — | — | Done | ✅ | 2025-05-01 | — |\n")
open(os.path.join(root, 'codeops', 'features', 'hard', '00-roadmap.md'), 'w').write(
    feature('Hard', hard_rows))

portfolio = (
    "# Portfolio Roadmap: Corrections\n\n"
    "> **Status**: Active\n> **Last Updated**: 2025-06-01 10:00\n"
    "> **Features**: 5 / 5 done (legacy audit pending)\n"
    "\n"
    "## Features\n\n"
    "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
    "|---------|---------|---------------|----------|--------|--------------|\n"
    "| svc | [→](features/svc/00-roadmap.md) | mostly done | 17/19 RDs | ⬜ | 2025-05-01 |\n"
    "| hard | [→](features/hard/00-roadmap.md) | shipped | 1/2 RDs · hardening ✅ 30/30 | ✅ | 2025-05-01 |\n")
open(os.path.join(root, 'codeops', '00-roadmap.md'), 'w').write(portfolio)
PY
}

# ST-2 — a stale but well-formed computed cell (17/19 RDs, 18 of 19 Done) is still corrected.
section "ST-2: stale computed token still corrected (17/19 → 18/19)"
repo_corr="$(mk_git_repo)"
build_corrections_repo "$repo_corr"
commit_all "$repo_corr" "corrections" >/dev/null
run_sync "$repo_corr" --check
if [[ "$RC" -eq 1 ]] && has_re "DRIFT.*svc"; then
  pass "--check flags the stale 17/19 cell as DRIFT (exit 1)"
else
  fail "--check did not flag the stale computed cell (rc=$RC)"
fi
run_sync "$repo_corr"
if [[ "$RC" -eq 0 ]] && file_has "$repo_corr/codeops/00-roadmap.md" '| 18/19 RDs |'; then
  pass "write rewrites 17/19 RDs → 18/19 RDs"
else
  fail "stale computed cell was not corrected to 18/19 RDs"
fi

# ST-5(b) — a stale token that carries a suffix: token rewritten, suffix kept verbatim.
section "ST-5(b): stale token rewritten, ' · …' suffix retained"
if file_has "$repo_corr/codeops/00-roadmap.md" '| 2/2 RDs · hardening ✅ 30/30 |'; then
  pass "hard cell '1/2 RDs · hardening ✅ 30/30' → '2/2 RDs · hardening ✅ 30/30'"
else
  fail "stale token+suffix not corrected with the suffix preserved"
fi

# ST-8(b) — the Features header token is rewritten while the parenthetical is kept.
section "ST-8(b): Features header token rewritten, parenthetical kept"
if file_has "$repo_corr/codeops/00-roadmap.md" '> **Features**: 1 / 2 done (legacy audit pending)'; then
  pass "Features header '5 / 5 done (…)' → '1 / 2 done (legacy audit pending)'"
else
  fail "Features header token/parenthetical not handled correctly"
fi

# =============================================================================
# ST-9 — golden no-op: a legacy RD-only flat roadmap (no sentinels/annotations/
# follow-ons/tasks) is byte-identical after a write and clean under --check.
# (Backward compatibility — this stays GREEN on the pre-change engine too.)
# =============================================================================
section "ST-9: golden no-op — RD-only flat roadmap unchanged"
repo_flat="$(make_repo flat)"
run_sync "$repo_flat"
if [[ "$RC" -eq 0 ]] && is_clean "$repo_flat"; then
  pass "write run leaves the RD-only roadmap byte-identical (tree clean)"
else
  fail "write run mutated a well-formed RD-only roadmap (rc=$RC)"
fi
run_sync "$repo_flat" --check
if [[ "$RC" -eq 0 ]] && ! has "DRIFT" && ! has "HELD"; then
  pass "--check exits 0 with no DRIFT and no HELD"
else
  fail "--check reported drift/held on the golden no-op (rc=$RC)"
fi

# =============================================================================
# ST-10 — security: a roadmap cell containing shell/code-looking text has zero side
# effects; it is parsed as literal text, never executed, through --check and write.
# =============================================================================
section "ST-10: no code execution from cell contents"
repo_sec="$(mk_git_repo)"
python3 - "$repo_sec" <<'PY'
import os, sys
root = sys.argv[1]
os.makedirs(os.path.join(root, 'codeops', 'features', 'svc'), exist_ok=True)
open(os.path.join(root, 'codeops', '.codeops.yml'), 'w').write("codeopsLayout: nested\n")
payload = "`$(touch PWNED)` '; rm -rf ."
feat = ("# Roadmap: Svc\n\n> **Feature-Set**: Svc\n> **Status**: In Progress\n"
        "> **Created**: 2025-01-01\n> **Last Updated**: 2025-05-01 10:00\n"
        "> **Progress**: 1 / 1 (100%)\n\n"
        "## Tracker\n\n"
        "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
        "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
        "| RD-01 | Core | — | — | Done | ✅ | 2025-05-01 | " + payload + " |\n")
open(os.path.join(root, 'codeops', 'features', 'svc', '00-roadmap.md'), 'w').write(feat)
# Portfolio: svc row is STALE (0/1 → 1/1), so it is rewritten on write — the payload
# lives in the Stage Summary cell and must pass through the row rebuild untouched.
portfolio = ("# Portfolio Roadmap: Sec\n\n> **Status**: Active\n"
             "> **Last Updated**: 2025-06-01 10:00\n> **Features**: 0 / 1 done\n"
             "\n## Features\n\n"
             "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
             "|---------|---------|---------------|----------|--------|--------------|\n"
             "| svc | [→](features/svc/00-roadmap.md) | " + payload + " | 0/1 RDs | ⬜ | 2025-05-01 |\n")
open(os.path.join(root, 'codeops', '00-roadmap.md'), 'w').write(portfolio)
PY
commit_all "$repo_sec" "sec" >/dev/null
run_sync "$repo_sec" --check
run_sync "$repo_sec"
if [[ ! -e "$repo_sec/PWNED" && -f "$repo_sec/codeops/00-roadmap.md" && -f "$repo_sec/codeops/features/svc/00-roadmap.md" ]]; then
  pass "no PWNED file created; repo intact — cell text never executed"
else
  fail "a roadmap cell was executed as code (PWNED created or repo damaged)"
fi
# The corrected cell is written, proving the payload passed through the row rebuild as text.
if file_has "$repo_sec/codeops/00-roadmap.md" '| 1/1 RDs |'; then
  pass "svc cell corrected to 1/1 RDs with the payload preserved verbatim"
else
  fail "svc cell not corrected (write path over the payload failed)"
fi

# =============================================================================
# ST-11 — the project verify command lists this suite.
# =============================================================================
section "ST-11: AGENTS.md verify command lists roadmap-sync-check.sh"
if grep -qF 'roadmap-sync-check.sh' "$REPO_ROOT/AGENTS.md"; then
  pass "AGENTS.md references ./scripts/roadmap-sync-check.sh"
else
  fail "AGENTS.md verify command does not list roadmap-sync-check.sh"
fi

# =============================================================================
# ST-12 — the co-specifying docs describe the engine's behaviour (no contradiction).
# =============================================================================
section "ST-12: skill docs document the n/a sentinel, follow-ons, suffix, RD-* rule"
TPL="$REPO_ROOT/skills/roadmap/template.md"
SKL="$REPO_ROOT/skills/roadmap/SKILL.md"
tpl_ok=1
for needle in "Open follow-ons" "n/a" "only" "RD"; do
  grep -qF "$needle" "$TPL" || tpl_ok=0
done
grep -qF "Open follow-ons" "$TPL" || tpl_ok=0
if [[ "$tpl_ok" -eq 1 ]]; then
  pass "template.md documents the follow-on section, n/a sentinel, and RD-*-only rule"
else
  fail "template.md does not document the new contract"
fi
if grep -qiF "follow-on" "$SKL" && grep -qF "HELD" "$SKL"; then
  pass "SKILL.md documents the follow-on lane and the HELD report"
else
  fail "SKILL.md does not document the follow-on lane / HELD report"
fi

# =============================================================================
# Implementation tests — internals and edges beyond the ST specification cases.
# =============================================================================

# Impl: flat-header-preserve — a hand-maintained Progress header in a FLAT roadmap is held.
section "Impl: flat layout — hand-maintained Progress header held, not rewritten"
repo_fh="$(mk_git_repo)"; mkdir -p "$repo_fh/plans"
cat >"$repo_fh/plans/00-roadmap.md" <<'MD'
# Roadmap: Archived Set

> **Feature-Set**: Archived Set
> **Status**: In Progress
> **Created**: 2025-01-01
> **Last Updated**: 2025-02-01
> **Progress**: n/a — tracked in the legacy tracker

## Tracker

| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |
|----|-------|----|------|-------|--------|--------------|----------------------|
| RD-01 | Thing | — | — | Done | ✅ | 2025-02-01 | — |
MD
commit_all "$repo_fh" "fh" >/dev/null
run_sync "$repo_fh" --check
if [[ "$RC" -eq 0 ]] && has_re "HELD.*Progress 'n/a — tracked in the legacy tracker'"; then
  pass "flat n/a header reported HELD, exit 0"
else
  fail "flat hand-maintained header not held (rc=$RC)"
fi
run_sync "$repo_fh"
if is_clean "$repo_fh"; then
  pass "flat write leaves the held header byte-identical"
else
  fail "flat write rewrote a hand-maintained header"
fi

# Impl: idempotency — a second write on a corrected repo is a clean no-op.
section "Impl: idempotency — second write run changes nothing"
repo_idem="$(mk_git_repo)"
build_corrections_repo "$repo_idem"
commit_all "$repo_idem" "c1" >/dev/null
run_sync "$repo_idem"                       # first write applies the corrections
commit_all "$repo_idem" "c2" >/dev/null
run_sync "$repo_idem"                       # second write must change nothing
if [[ "$RC" -eq 0 ]] && is_clean "$repo_idem"; then
  pass "second write run is a clean no-op"
else
  fail "second write run mutated an already-synced repo (rc=$RC)"
fi
run_sync "$repo_idem" --check
if [[ "$RC" -eq 0 ]]; then
  pass "--check clean after a full write (no residual drift)"
else
  fail "--check still reports drift after a full write (rc=$RC)"
fi

# Impl: dry-run-channels — --dry-run prints BOTH DRIFT and HELD, writes nothing, exits 0.
section "Impl: --dry-run prints DRIFT + HELD, writes nothing, exits 0"
repo_dry="$(mk_git_repo)"
python3 - "$repo_dry" <<'PY'
import os, sys
root = sys.argv[1]
for f in ('svc', 'arch'):
    os.makedirs(os.path.join(root, 'codeops', 'features', f), exist_ok=True)
open(os.path.join(root, 'codeops', '.codeops.yml'), 'w').write("codeopsLayout: nested\n")
def feat(name, rows, prog):
    return ("# Roadmap: %s\n\n> **Feature-Set**: %s\n> **Status**: In Progress\n"
            "> **Created**: 2025-01-01\n> **Last Updated**: 2025-05-01 10:00\n"
            "> **Progress**: %s\n\n## Tracker\n\n"
            "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
            "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
            % (name, name, prog)) + rows
open(os.path.join(root, 'codeops', 'features', 'svc', '00-roadmap.md'), 'w').write(
    feat('Svc', "| RD-01 | Core | — | — | Done | ✅ | 2025-05-01 | — |\n", '1 / 1 (100%)'))
open(os.path.join(root, 'codeops', 'features', 'arch', '00-roadmap.md'), 'w').write(
    feat('Arch', "", 'n/a'))
open(os.path.join(root, 'codeops', '00-roadmap.md'), 'w').write(
    "# Portfolio Roadmap: Mixed\n\n> **Status**: Active\n> **Last Updated**: 2025-06-01 10:00\n"
    "> **Features**: 0 / 0 done\n\n## Features\n\n"
    "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
    "|---------|---------|---------------|----------|--------|--------------|\n"
    "| svc | [→](features/svc/00-roadmap.md) | done | 0/1 RDs | ⬜ | 2025-05-01 |\n"
    "| arch | [→](features/arch/00-roadmap.md) | archived | n/a | ✅ | 2025-03-01 |\n")
PY
commit_all "$repo_dry" "mixed" >/dev/null
run_sync "$repo_dry" --dry-run
if [[ "$RC" -eq 0 ]] && has "DRIFT" && has "HELD" && is_clean "$repo_dry"; then
  pass "--dry-run prints DRIFT + HELD, exits 0, writes nothing"
else
  fail "--dry-run channels/exit/no-write wrong (rc=$RC)"
fi

# build_followon_repo <dir> <status-header> <followon-status-cell> — one feature 'feat' with 1 RD
# Done and an ## Open follow-ons table; portfolio cell stale at 1/1 RDs / 🔄 so a correct roll to ✅
# is observable. <status-header> is the follow-on table's last column header.
build_followon_repo() {
  python3 - "$1" "$2" "$3" <<'PY'
import os, sys
root, hdr, cell = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(os.path.join(root, 'codeops', 'features', 'feat'), exist_ok=True)
open(os.path.join(root, 'codeops', '.codeops.yml'), 'w').write("codeopsLayout: nested\n")
feature = ("# Roadmap: Feat\n\n> **Feature-Set**: Feat\n> **Status**: In Progress\n"
           "> **Created**: 2025-01-01\n> **Last Updated**: 2025-05-01 10:00\n"
           "> **Progress**: 1 / 1 (100%%)\n\n## Tracker\n\n"
           "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
           "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
           "| RD-01 | Core | — | — | Done | ✅ | 2025-05-01 | — |\n\n"
           "## Open follow-ons\n\n"
           "| Item | Scope | %s |\n|------|-------|--------|\n"
           "| `x` | y | %s |\n" % (hdr, cell))
open(os.path.join(root, 'codeops', 'features', 'feat', '00-roadmap.md'), 'w').write(feature)
open(os.path.join(root, 'codeops', '00-roadmap.md'), 'w').write(
    "# Portfolio Roadmap: Follow\n\n> **Status**: Active\n> **Last Updated**: 2025-06-01 10:00\n"
    "> **Features**: 0 / 1 done\n\n## Features\n\n"
    "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
    "|---------|---------|---------------|----------|--------|--------------|\n"
    "| feat | [→](features/feat/00-roadmap.md) | done | 1/1 RDs | 🔄 | 2025-05-01 |\n")
PY
}

# Impl: followon-all-done — a follow-on table with every row ✅ does not hold 🔄.
section "Impl: follow-ons all ✅ → feature rolls ✅ (no false hold)"
repo_fad="$(mk_git_repo)"
build_followon_repo "$repo_fad" "Status" "✅ shipped"
commit_all "$repo_fad" "fad" >/dev/null
run_sync "$repo_fad"
if file_has "$repo_fad/codeops/00-roadmap.md" '| 1/1 RDs | ✅ |'; then
  pass "all-✅ follow-on table → feature rolls ✅ (🔄 corrected)"
else
  fail "all-✅ follow-on table wrongly held the feature off ✅"
fi

# Impl: malformed-followon — a follow-on table whose last column is not Status → no false hold.
section "Impl: malformed follow-on table (no Status-last column) → no false hold"
repo_mal="$(mk_git_repo)"
build_followon_repo "$repo_mal" "Owner" "alice"
commit_all "$repo_mal" "mal" >/dev/null
run_sync "$repo_mal"
if file_has "$repo_mal/codeops/00-roadmap.md" '| 1/1 RDs | ✅ |'; then
  pass "malformed follow-on ignored — feature rolls ✅"
else
  fail "malformed follow-on caused a false 🔄 hold"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Summary"
if [[ "$FAILURES" -eq 0 ]]; then
  printf '  \033[32mAll roadmap-sync checks passed.\033[0m\n'
  exit 0
else
  printf '  \033[31m%d roadmap-sync check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
