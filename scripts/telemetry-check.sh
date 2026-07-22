#!/usr/bin/env bash
#
# telemetry-check.sh — specification-test suite for the telemetry utility.
#
# Drives scripts/codeops-events.sh entirely inside SANDBOX home directories (temp dirs
# standing in for the user's home, so the real ~/.claude is never touched) against the
# fixtures in scripts/fixtures/telemetry-events/. Each SPEC-N check pins one specified
# behavior: envelope auto-fill, strict whole-line refusal of invalid emits, hook-payload
# parsing, kill switches, aggregation (stats/gaps), content hashing, concurrent-append
# integrity, and sandbox containment. It is a specification test: written from the
# specification BEFORE the utility exists, so it is RED until scripts/codeops-events.sh
# lands and GREEN thereafter. A failing check means the utility is wrong, never the check.
#
# It NEVER mutates a committed fixture — fixtures are copied into temp dirs first, and
# every utility invocation runs with an overridden HOME inside the sandbox.
#
# CodeOps Skills Version: 3.12.0
#
# Usage:  ./scripts/telemetry-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

UTILITY="$REPO_ROOT/scripts/codeops-events.sh"
FIXTURES="$REPO_ROOT/scripts/fixtures/telemetry-events"
EVENTS_REL=".claude/codeops-telemetry/events.jsonl"

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

# Snapshot the REAL home's telemetry file up front — the containment check at the end
# asserts the suite never touched it.
REAL_EVENTS="$HOME/$EVENTS_REL"
real_events_state() { stat -c '%Y %s' "$REAL_EVENTS" 2>/dev/null || echo "absent"; }
REAL_BEFORE="$(real_events_state)"

SANDBOX="$(mktemp -d)"
TMP_DIRS+=("$SANDBOX")

# mk_home — fresh, empty sandbox home; echo its path.
mk_home() {
  local h
  h="$(mktemp -d)"
  TMP_DIRS+=("$h")
  printf '%s\n' "$h"
}

# A work repo named "acme" — emits run from here so the project field is derivable.
WORK_ROOT="$(mktemp -d)"
TMP_DIRS+=("$WORK_ROOT")
WORK="$WORK_ROOT/acme"
mkdir -p "$WORK"
git -C "$WORK" init -q

# run_util <home> <cwd> <args...> — run the utility with a sandbox home and controlled
# environment; sets OUT/ERR/RC. Extra env pairs go via the UTIL_ENV array. The telemetry
# env kill switch is cleared by default so only SPEC-7 exercises it.
UTIL_ENV=()
OUT=""
ERR=""
RC=0
run_util() {
  local home="$1" cwd="$2"
  shift 2
  if [[ ! -x "$UTILITY" ]]; then
    OUT=""
    ERR="utility missing or not executable"
    RC=127
    return
  fi
  OUT="$(cd "$cwd" && env -u CODEOPS_TELEMETRY ${UTIL_ENV[@]+"${UTIL_ENV[@]}"} HOME="$home" "$UTILITY" "$@" 2>"$SANDBOX/stderr.txt")"
  RC=$?
  ERR="$(cat "$SANDBOX/stderr.txt")"
}

count_lines() { if [[ -f "$1" ]]; then wc -l <"$1"; else echo 0; fi; }
jget() { jq -r "$1" <<<"$2" 2>/dev/null; }

# -----------------------------------------------------------------------------
# Utility presence — without it every check below is red (the pre-implementation state).
# -----------------------------------------------------------------------------
section "Utility: scripts/codeops-events.sh present and executable"
if [[ -x "$UTILITY" ]]; then
  pass "utility present and executable"
else
  fail "utility missing or not executable: $UTILITY"
fi

# -----------------------------------------------------------------------------
# SPEC-1 — a valid emit from inside a git repo appends exactly one JSON line with the
# envelope auto-filled: v=1, ts ISO-8601 UTC, codeops = the utility's own version stamp,
# project = repo basename, src defaults to skill; list/object fields land typed.
# -----------------------------------------------------------------------------
section "SPEC-1: valid emit — envelope auto-fill"
h1="$(mk_home)"
run_util "$h1" "$WORK" emit review_run agent=phase-reviewer feature=checkout phase=P1 \
  lenses=security findings_critical=1 findings_major=0 findings_minor=2
ev1="$h1/$EVENTS_REL"
if [[ "$RC" -eq 0 ]]; then pass "emit exited 0"; else fail "emit exited $RC"; fi
if [[ "$(count_lines "$ev1")" == "1" ]]; then
  pass "exactly one line appended"
else
  fail "expected exactly 1 line, found $(count_lines "$ev1")"
fi
line="$(tail -n1 "$ev1" 2>/dev/null || true)"
if jq -e . >/dev/null 2>&1 <<<"$line"; then pass "appended line is valid JSON"; else fail "appended line is not valid JSON"; fi
[[ "$(jget '.v' "$line")" == "1" ]] && pass "v == 1" || fail "v != 1"
ts="$(jget '.ts' "$line")"
if [[ "$ts" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
  pass "ts is ISO-8601 UTC ($ts)"
else
  fail "ts is not ISO-8601 UTC: '$ts'"
fi
if [[ -x "$UTILITY" ]]; then
  util_stamp="$(grep -oE 'CodeOps Skills Version: [0-9.]+' "$UTILITY" | awk '{print $NF}')"
  if [[ -n "$util_stamp" && "$(jget '.codeops' "$line")" == "$util_stamp" ]]; then
    pass "codeops == utility version stamp ($util_stamp)"
  else
    fail "codeops '"$(jget '.codeops' "$line")"' != utility stamp '$util_stamp'"
  fi
else
  fail "codeops stamp not checkable (utility missing)"
fi
[[ "$(jget '.project' "$line")" == "acme" ]] && pass "project == repo basename (acme)" || fail "project != acme"
[[ "$(jget '.src' "$line")" == "skill" ]] && pass "src defaults to skill" || fail "src != skill"
[[ "$(jget '.event' "$line")" == "review_run" ]] && pass "event == review_run" || fail "event != review_run"
[[ "$(jget '.lenses == ["security"]' "$line")" == "true" ]] && pass "lenses stored as a list" || fail "lenses not stored as [\"security\"]"
[[ "$(jget '.findings == {"critical":1,"major":0,"minor":2}' "$line")" == "true" ]] \
  && pass "findings stored as a typed object" || fail "findings object wrong"
[[ "$(jget 'has("session")' "$line")" == "false" ]] && pass "no session field on a skill-side emit" || fail "unexpected session field"

# -----------------------------------------------------------------------------
# SPEC-2 / SPEC-3 / SPEC-4 — strict whole-line refusal: unknown event type, illegal enum
# value, unknown key. Each: nothing appended, one stderr warning, exit 0.
# -----------------------------------------------------------------------------
section "SPEC-2/3/4: invalid emits are refused whole-line"
bad_lines=()
while IFS= read -r bline; do
  [[ -z "$bline" || "$bline" == \#* ]] && continue
  bad_lines+=("$bline")
done <"$FIXTURES/bad-emits.txt"
bad_labels=("SPEC-2 unknown event type" "SPEC-3 illegal enum value" "SPEC-4 unknown key")
for i in 0 1 2; do
  hbad="$(mk_home)"
  read -r -a bargs <<<"${bad_lines[$i]}"
  run_util "$hbad" "$WORK" emit "${bargs[@]}"
  evbad="$hbad/$EVENTS_REL"
  if [[ "$RC" -eq 0 && "$(count_lines "$evbad")" == "0" && -n "$ERR" ]]; then
    pass "${bad_labels[$i]}: refused (nothing appended, warned, exit 0)"
  else
    fail "${bad_labels[$i]}: rc=$RC lines=$(count_lines "$evbad") warn='${ERR:0:60}'"
  fi
done

# -----------------------------------------------------------------------------
# SPEC-5 — hook mode with a Skill-tool payload appends a skill_invoked line carrying
# src=hook, the skill name, and the session id from the payload.
# -----------------------------------------------------------------------------
section "SPEC-5: hook payload (Skill tool) → skill_invoked"
h5="$(mk_home)"
run_util "$h5" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/skill-invoked.json"
ev5="$h5/$EVENTS_REL"
if [[ "$RC" -eq 0 && "$(count_lines "$ev5")" == "1" ]]; then
  pass "one line appended, exit 0"
else
  fail "rc=$RC lines=$(count_lines "$ev5")"
fi
line="$(tail -n1 "$ev5" 2>/dev/null || true)"
[[ "$(jget '.event' "$line")" == "skill_invoked" ]] && pass "event == skill_invoked" || fail "event != skill_invoked"
[[ "$(jget '.src' "$line")" == "hook" ]] && pass "src == hook" || fail "src != hook"
[[ "$(jget '.skill' "$line")" == "exec_plan" ]] && pass "skill == exec_plan" || fail "skill != exec_plan"
[[ "$(jget '.session' "$line")" == "sess-fixture-01" ]] && pass "session from payload" || fail "session missing/wrong"
[[ "$(jget 'has("duration_s")' "$line")" == "false" ]] && pass "no duration on skill_invoked" || fail "unexpected duration_s"

# -----------------------------------------------------------------------------
# SPEC-6 — subagent-tool payloads → agent_completed. With a first-line dispatch header the
# agent/feature/phase fields are populated and duration_s comes from the payload's elapsed
# milliseconds; without a header the event is still appended with those fields omitted;
# the legacy Task tool name is accepted as an alias.
# -----------------------------------------------------------------------------
section "SPEC-6: hook payloads (subagent tool) → agent_completed"
h6="$(mk_home)"
ev6="$h6/$EVENTS_REL"
run_util "$h6" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-with-header.json"
rc_a=$RC
run_util "$h6" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-no-header.json"
rc_b=$RC
run_util "$h6" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-legacy-task.json"
rc_c=$RC
if [[ "$rc_a" -eq 0 && "$rc_b" -eq 0 && "$rc_c" -eq 0 && "$(count_lines "$ev6")" == "3" ]]; then
  pass "three lines appended, all exit 0"
else
  fail "rc=$rc_a/$rc_b/$rc_c lines=$(count_lines "$ev6")"
fi
l1="$(sed -n 1p "$ev6" 2>/dev/null || true)"
l2="$(sed -n 2p "$ev6" 2>/dev/null || true)"
l3="$(sed -n 3p "$ev6" 2>/dev/null || true)"
if [[ "$(jget '.event' "$l1")" == "agent_completed" && "$(jget '.agent' "$l1")" == "phase-reviewer" \
   && "$(jget '.feature' "$l1")" == "checkout" && "$(jget '.phase' "$l1")" == "P3" ]]; then
  pass "header parsed: agent/feature/phase populated"
else
  fail "header fields wrong: $(jget '{agent,feature,phase}' "$l1")"
fi
[[ "$(jget '.duration_s' "$l1")" == "154" ]] && pass "duration_s == 154 (from milliseconds)" || fail "duration_s != 154: $(jget '.duration_s' "$l1")"
[[ "$(jget '.session' "$l1")" == "sess-fixture-02" ]] && pass "session from payload" || fail "session missing/wrong"
if [[ "$(jget '.event' "$l2")" == "agent_completed" && "$(jget 'has("agent")' "$l2")" == "false" \
   && "$(jget 'has("feature")' "$l2")" == "false" && "$(jget 'has("phase")' "$l2")" == "false" ]]; then
  pass "no header → event kept, agent/feature/phase omitted"
else
  fail "headerless payload mishandled"
fi
[[ "$(jget '.duration_s' "$l2")" == "8" ]] && pass "headerless duration_s == 8" || fail "headerless duration_s wrong"
if [[ "$(jget '.event' "$l3")" == "agent_completed" && "$(jget '.agent' "$l3")" == "security-auditor" \
   && "$(jget '.phase' "$l3")" == "P2" && "$(jget '.duration_s' "$l3")" == "61" ]]; then
  pass "legacy Task tool name accepted as alias"
else
  fail "legacy Task payload mishandled"
fi

# -----------------------------------------------------------------------------
# SPEC-6B — agent attribution comes from the payload's subagent_type, not the prose header.
# A CodeOps dispatch is one whose subagent_type is "codeops:<name>" OR a bare "<name>" that
# matches a file in the plugin's own agents/ directory. Anything else is not a CodeOps dispatch
# and carries no agent field. The header remains the fallback source of agent when subagent_type
# is absent, and the sole source of feature/phase in every case.
# -----------------------------------------------------------------------------
section "SPEC-6B: agent attribution from subagent_type"
h6b="$(mk_home)"
ev6b="$h6b/$EVENTS_REL"
run_util "$h6b" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-bare-name.json"
rc_d=$RC
run_util "$h6b" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-unknown-type.json"
rc_e=$RC
run_util "$h6b" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-no-subagent-type.json"
rc_f=$RC
run_util "$h6b" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/agent-conflict.json"
rc_g=$RC
if [[ "$rc_d" -eq 0 && "$rc_e" -eq 0 && "$rc_f" -eq 0 && "$rc_g" -eq 0 && "$(count_lines "$ev6b")" == "4" ]]; then
  pass "four lines appended, all exit 0"
else
  fail "rc=$rc_d/$rc_e/$rc_f/$rc_g lines=$(count_lines "$ev6b")"
fi
m1="$(sed -n 1p "$ev6b" 2>/dev/null || true)"
m2="$(sed -n 2p "$ev6b" 2>/dev/null || true)"
m3="$(sed -n 3p "$ev6b" 2>/dev/null || true)"
m4="$(sed -n 4p "$ev6b" 2>/dev/null || true)"

# A bare name matching agents/codebase-scout.md is a CodeOps dispatch even with no header at all.
if [[ "$(jget '.event' "$m1")" == "agent_completed" && "$(jget '.agent' "$m1")" == "codebase-scout" ]]; then
  pass "bare subagent_type matching agents/ → attributed"
else
  fail "bare name not attributed: $(jget '.agent' "$m1")"
fi
# No header on that payload, so feature/phase stay absent — attribution must not invent them.
if [[ "$(jget 'has("feature")' "$m1")" == "false" && "$(jget 'has("phase")' "$m1")" == "false" ]]; then
  pass "bare name without header → feature/phase omitted"
else
  fail "feature/phase invented: $(jget '{feature,phase}' "$m1")"
fi
# general-purpose is not a CodeOps agent; the event is kept but must carry no agent field,
# otherwise ordinary agent use pollutes per-agent stats.
if [[ "$(jget '.event' "$m2")" == "agent_completed" && "$(jget 'has("agent")' "$m2")" == "false" ]]; then
  pass "unknown subagent_type → event kept, agent omitted"
else
  fail "non-CodeOps agent attributed: $(jget '.agent' "$m2")"
fi
# Absent subagent_type falls back to the header, so no dispatch that works today regresses.
if [[ "$(jget '.agent' "$m3")" == "perf-auditor" && "$(jget '.feature' "$m3")" == "billing" \
   && "$(jget '.phase' "$m3")" == "P7" ]]; then
  pass "no subagent_type → header fallback populates agent/feature/phase"
else
  fail "header fallback failed: $(jget '{agent,feature,phase}' "$m3")"
fi
# When the two disagree the payload wins: subagent_type is what the tool actually ran,
# the header is prose that can go stale.
if [[ "$(jget '.agent' "$m4")" == "security-auditor" ]]; then
  pass "subagent_type wins over a conflicting header agent"
else
  fail "conflict resolved wrongly: $(jget '.agent' "$m4")"
fi
# feature/phase still come from the header even when its agent field was overridden.
if [[ "$(jget '.feature' "$m4")" == "checkout" && "$(jget '.phase' "$m4")" == "P4" ]]; then
  pass "header still owns feature/phase on conflict"
else
  fail "feature/phase lost on conflict: $(jget '{feature,phase}' "$m4")"
fi

# -----------------------------------------------------------------------------
# SPEC-7 — the environment kill switch: a valid emit with the telemetry env var set to 0
# is a silent no-op (nothing written, exit 0).
# -----------------------------------------------------------------------------
section "SPEC-7: env kill switch"
h7="$(mk_home)"
UTIL_ENV=(CODEOPS_TELEMETRY=0)
run_util "$h7" "$WORK" emit skill_invoked skill=exec_plan
UTIL_ENV=()
if [[ "$RC" -eq 0 && ! -e "$h7/$EVENTS_REL" ]]; then
  pass "env kill switch → no-op, exit 0"
else
  fail "rc=$RC file_exists=$([[ -e "$h7/$EVENTS_REL" ]] && echo yes || echo no)"
fi

# -----------------------------------------------------------------------------
# SPEC-8 — the per-repo kill switch: an emit from a repo whose CLAUDE.md quality block
# turns telemetry off is a no-op (exit 0).
# -----------------------------------------------------------------------------
section "SPEC-8: per-repo kill switch (quality block)"
h8="$(mk_home)"
fake_root="$(mktemp -d)"
TMP_DIRS+=("$fake_root")
cp -R "$FIXTURES/fake-repo/." "$fake_root/"
git -C "$fake_root" init -q
run_util "$h8" "$fake_root" emit skill_invoked skill=exec_plan
if [[ "$RC" -eq 0 && ! -e "$h8/$EVENTS_REL" ]]; then
  pass "repo kill switch → no-op, exit 0"
else
  fail "rc=$RC file_exists=$([[ -e "$h8/$EVENTS_REL" ]] && echo yes || echo no)"
fi

# -----------------------------------------------------------------------------
# SPEC-9 — jq absent from PATH: a valid emit becomes a no-op with exactly one stderr note.
# A restricted PATH is built from symlinks to everything except jq.
# -----------------------------------------------------------------------------
section "SPEC-9: jq absent → no-op with one stderr note"
NOJQ="$SANDBOX/nojq-bin"
if [[ ! -d "$NOJQ" ]]; then
  mkdir -p "$NOJQ"
  IFS=: read -r -a path_dirs <<<"$PATH"
  for d in "${path_dirs[@]}"; do
    [[ -d "$d" ]] || continue
    for b in "$d"/*; do
      n="$(basename "$b")"
      [[ "$n" == "jq" ]] && continue
      [[ -e "$NOJQ/$n" ]] || ln -s "$b" "$NOJQ/$n" 2>/dev/null
    done
  done
fi
h9="$(mk_home)"
UTIL_ENV=(PATH="$NOJQ")
run_util "$h9" "$WORK" emit skill_invoked skill=exec_plan
UTIL_ENV=()
if [[ "$RC" -eq 0 && ! -e "$h9/$EVENTS_REL" ]]; then
  pass "no jq → no-op, exit 0"
else
  fail "rc=$RC file_exists=$([[ -e "$h9/$EVENTS_REL" ]] && echo yes || echo no)"
fi
if [[ "$RC" -eq 0 && "$(printf '%s' "$ERR" | grep -c .)" == "1" ]]; then
  pass "exactly one stderr note"
else
  fail "stderr note count wrong: '${ERR:0:80}'"
fi

# -----------------------------------------------------------------------------
# SPEC-10 — stats --by agent over the fixture events: correct per-agent counts, average
# duration, and acceptance rate (accepted / ruled, deferred excluded), within 40 lines.
# The fixture holds 4 phase-reviewer completions (durations 42/38/51/45 → avg 44) and
# 4 rulings (2 accepted, 1 rejected, 1 deferred → 2/3 = 67%), plus 1 scout completion.
# -----------------------------------------------------------------------------
section "SPEC-10: stats --by agent over fixture events"
h10="$(mk_home)"
mkdir -p "$h10/.claude/codeops-telemetry"
cp "$FIXTURES/valid-events.jsonl" "$h10/$EVENTS_REL"
run_util "$h10" "$WORK" stats --by agent
if [[ "$RC" -eq 0 ]]; then pass "stats exited 0"; else fail "stats exited $RC"; fi
if [[ -n "$OUT" && "$(printf '%s\n' "$OUT" | wc -l)" -le 40 ]]; then
  pass "output within 40 lines"
else
  fail "output empty or over 40 lines"
fi
rev_row="$(printf '%s\n' "$OUT" | grep 'phase-reviewer' || true)"
scout_row="$(printf '%s\n' "$OUT" | grep 'codebase-scout' || true)"
if [[ -n "$rev_row" ]] && grep -qw 4 <<<"$rev_row" && grep -qw 44 <<<"$rev_row" && grep -q '67%' <<<"$rev_row"; then
  pass "phase-reviewer row: 4 runs, avg 44s, 67% acceptance"
else
  fail "phase-reviewer row wrong: '${rev_row:-<missing>}'"
fi
if [[ -n "$scout_row" ]] && grep -qw 1 <<<"$scout_row"; then
  pass "codebase-scout row: 1 run"
else
  fail "codebase-scout row wrong: '${scout_row:-<missing>}'"
fi

# -----------------------------------------------------------------------------
# SPEC-11 — gaps over the fixture events: 4 reviewer/auditor completions, 3 with a
# downstream ruling in the same project+feature+phase → a 25% gap rate. The scout
# completion must not count toward the denominator.
# -----------------------------------------------------------------------------
section "SPEC-11: gaps over fixture events → 25%"
run_util "$h10" "$WORK" gaps
if [[ "$RC" -eq 0 ]]; then pass "gaps exited 0"; else fail "gaps exited $RC"; fi
if grep -q '25%' <<<"$OUT"; then
  pass "reports a 25% gap rate"
else
  fail "expected 25% in: '${OUT:0:120}'"
fi

# -----------------------------------------------------------------------------
# SPEC-12 — content hashing: the utility computes the hash itself from --hash-text,
# stores the first 8 hex of the digest, and the raw text lands nowhere in the file.
# -----------------------------------------------------------------------------
section "SPEC-12: --hash-text stores an 8-hex hash, never the text"
h12="$(mk_home)"
secret="SQL injection in login"
run_util "$h12" "$WORK" emit finding_decided agent=phase-reviewer feature=checkout phase=P1 \
  severity=major lens=security decision=accepted fix_applied=true --hash-text "$secret"
ev12="$h12/$EVENTS_REL"
if [[ "$RC" -eq 0 && "$(count_lines "$ev12")" == "1" ]]; then
  pass "emit accepted, one line"
else
  fail "rc=$RC lines=$(count_lines "$ev12")"
fi
line="$(tail -n1 "$ev12" 2>/dev/null || true)"
want_hash="$(printf '%s' "$secret" | sha256sum | awk '{print $1}' | cut -c1-8)"
got_hash="$(jget '.hash' "$line")"
if [[ "$got_hash" == "$want_hash" ]]; then
  pass "hash == first 8 hex of the digest ($want_hash)"
else
  fail "hash '$got_hash' != expected '$want_hash'"
fi
if [[ -f "$ev12" ]] && ! grep -qF "$secret" "$ev12"; then
  pass "raw text appears nowhere in the events file"
else
  fail "raw text leaked into the events file (or file missing)"
fi

# -----------------------------------------------------------------------------
# SPEC-13 — 50 concurrent emits land as 50 intact, parseable JSON lines (no interleaving).
# -----------------------------------------------------------------------------
section "SPEC-13: 50 concurrent emits — no interleaving"
h13="$(mk_home)"
ev13="$h13/$EVENTS_REL"
if [[ -x "$UTILITY" ]]; then
  for i in $(seq 1 50); do
    (cd "$WORK" && env -u CODEOPS_TELEMETRY HOME="$h13" "$UTILITY" emit task_completed \
      feature=checkout phase=P1 task="1.1.$i" verify=pass attempts=1 files_changed=1) >/dev/null 2>&1 &
  done
  wait
fi
if [[ "$(count_lines "$ev13")" == "50" ]]; then
  pass "50 lines present"
else
  fail "expected 50 lines, found $(count_lines "$ev13")"
fi
if [[ -f "$ev13" ]] && jq -e . "$ev13" >/dev/null 2>&1; then
  pass "every line parses as JSON (no interleaving)"
else
  fail "at least one corrupt/interleaved line"
fi

# -----------------------------------------------------------------------------
# SPEC-14 — the timestamp always comes from the system clock: a ts= argument is an
# unknown key (whole-line refusal), and an accepted emit carries a current ISO timestamp.
# -----------------------------------------------------------------------------
section "SPEC-14: ts is clock-derived, never caller-supplied"
h14="$(mk_home)"
run_util "$h14" "$WORK" emit phase_started feature=checkout phase=P1 tag=standard mode=inline \
  ts=2020-01-01T00:00:00Z
if [[ "$RC" -eq 0 && "$(count_lines "$h14/$EVENTS_REL")" == "0" && -n "$ERR" ]]; then
  pass "ts= argument refused as an unknown key"
else
  fail "ts= argument was not refused (rc=$RC lines=$(count_lines "$h14/$EVENTS_REL"))"
fi
run_util "$h14" "$WORK" emit phase_started feature=checkout phase=P1 tag=standard mode=inline
line="$(tail -n1 "$h14/$EVENTS_REL" 2>/dev/null || true)"
ts="$(jget '.ts' "$line")"
today="$(date -u +%Y-%m-%d)"
yesterday="$(date -u -d yesterday +%Y-%m-%d 2>/dev/null || echo "$today")"
if [[ "$ts" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]] \
   && { [[ "$ts" == "$today"* ]] || [[ "$ts" == "$yesterday"* ]]; }; then
  pass "accepted emit carries a current clock timestamp ($ts)"
else
  fail "timestamp not current/ISO: '$ts'"
fi

# -----------------------------------------------------------------------------
# SPEC-15 — malformed hook stdin: warn, refuse, exit 0.
# -----------------------------------------------------------------------------
section "SPEC-15: malformed hook stdin refused"
h15="$(mk_home)"
run_util "$h15" "$WORK" emit --src hook --stdin <"$FIXTURES/hook-payloads/malformed.json"
if [[ "$RC" -eq 0 && "$(count_lines "$h15/$EVENTS_REL")" == "0" && -n "$ERR" ]]; then
  pass "malformed stdin → warn, refuse, exit 0"
else
  fail "rc=$RC lines=$(count_lines "$h15/$EVENTS_REL") warn='${ERR:0:60}'"
fi

# =============================================================================
# Edge cases (implementation tests — internals + boundaries, written after green).
# =============================================================================

# -----------------------------------------------------------------------------
# Edge: stats over an empty or absent events file → friendly notice, exit 0.
# -----------------------------------------------------------------------------
section "Edge: stats with empty/absent events file"
he="$(mk_home)"
run_util "$he" "$WORK" stats
if [[ "$RC" -eq 0 ]] && grep -qi 'no events' <<<"$OUT"; then
  pass "absent file → 'no events' notice, exit 0"
else
  fail "absent file mishandled (rc=$RC out='${OUT:0:60}')"
fi
mkdir -p "$he/.claude/codeops-telemetry"
: >"$he/$EVENTS_REL"
run_util "$he" "$WORK" stats --by agent
if [[ "$RC" -eq 0 ]] && grep -qi 'no events' <<<"$OUT"; then
  pass "empty file → 'no events' notice, exit 0"
else
  fail "empty file mishandled (rc=$RC out='${OUT:0:60}')"
fi

# -----------------------------------------------------------------------------
# Edge: --since window filtering and refusal of an unusable --since value.
# -----------------------------------------------------------------------------
section "Edge: --since parsing"
hs="$(mk_home)"
mkdir -p "$hs/.claude/codeops-telemetry"
printf '{"v":1,"ts":"2000-01-01T00:00:00Z","codeops":"0.0.0","project":"acme","src":"hook","event":"skill_invoked","skill":"exec_plan"}\n' >"$hs/$EVENTS_REL"
run_util "$hs" "$WORK" emit task_completed feature=checkout phase=P1 task=1.1.1 verify=pass attempts=1 files_changed=1
run_util "$hs" "$WORK" stats --since 7d --by event
if [[ "$RC" -eq 0 ]] && grep -q 'task_completed' <<<"$OUT" && ! grep -q 'skill_invoked' <<<"$OUT"; then
  pass "--since 7d keeps the fresh event, drops the ancient one"
else
  fail "--since window filtering wrong (rc=$RC out='${OUT:0:80}')"
fi
run_util "$hs" "$WORK" stats --since banana
if [[ "$RC" -eq 0 && -z "$OUT" && -n "$ERR" ]]; then
  pass "unusable --since value → warn, no table, exit 0"
else
  fail "unusable --since value mishandled (rc=$RC)"
fi

# -----------------------------------------------------------------------------
# Edge: an oversized corrupt line in the events file is skipped, never fatal.
# -----------------------------------------------------------------------------
section "Edge: oversized corrupt line skipped by readers"
hb="$(mk_home)"
mkdir -p "$hb/.claude/codeops-telemetry"
{
  printf '{"v":1,"ts":"2026-07-18T09:00:00Z","codeops":"0.0.0","project":"acme","src":"skill","event":"phase_started","feature":"checkout","phase":"P1","tag":"standard","mode":"inline"}\n'
  head -c 100000 /dev/zero | tr '\0' 'x'
  printf '\n'
  printf '{"v":1,"ts":"2026-07-18T09:10:00Z","codeops":"0.0.0","project":"acme","src":"skill","event":"phase_completed","feature":"checkout","phase":"P1","tag":"standard","mode":"inline"}\n'
} >"$hb/$EVENTS_REL"
run_util "$hb" "$WORK" stats --by event
if [[ "$RC" -eq 0 ]] && grep -q 'phase_started' <<<"$OUT" && grep -q 'phase_completed' <<<"$OUT"; then
  pass "both valid events aggregated around a 100KB garbage line"
else
  fail "oversized corrupt line broke stats (rc=$RC out='${OUT:0:80}')"
fi

# -----------------------------------------------------------------------------
# Edge: emit from outside any git repository → project recorded as unknown.
# -----------------------------------------------------------------------------
section "Edge: emit outside a git repo → project=unknown"
hn="$(mk_home)"
nogit="$(mktemp -d)"
TMP_DIRS+=("$nogit")
run_util "$hn" "$nogit" emit skill_invoked skill=exec_plan
line="$(tail -n1 "$hn/$EVENTS_REL" 2>/dev/null || true)"
if [[ "$RC" -eq 0 && "$(jget '.project' "$line")" == "unknown" ]]; then
  pass "non-repo emit accepted with project=unknown"
else
  fail "non-repo emit mishandled (rc=$RC project='$(jget '.project' "$line")')"
fi

# -----------------------------------------------------------------------------
# SPEC-16 — containment meta-assertion: the whole run wrote nothing to the real home's
# telemetry file (every invocation above used a sandbox home).
# -----------------------------------------------------------------------------
section "SPEC-16: no writes outside the sandbox"
if [[ -x "$UTILITY" ]]; then
  REAL_AFTER="$(real_events_state)"
  if [[ "$REAL_BEFORE" == "$REAL_AFTER" ]]; then
    pass "real ~/$EVENTS_REL untouched ($REAL_AFTER)"
  else
    fail "real telemetry file changed during the suite: '$REAL_BEFORE' → '$REAL_AFTER'"
  fi
else
  fail "containment not demonstrable — utility missing, nothing ran"
fi

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Summary"
if [[ "$FAILURES" -eq 0 ]]; then
  printf '  \033[32mAll telemetry checks passed.\033[0m\n'
  exit 0
else
  printf '  \033[31m%d telemetry check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
