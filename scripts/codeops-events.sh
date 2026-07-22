#!/usr/bin/env bash
#
# codeops-events.sh — append-only, metadata-only telemetry for the CodeOps workflow.
#
# Subcommands:
#   emit <event> [key=value…] [--hash-text "<text>"] [--src hook] [--stdin]
#   stats [--since <Nd>] [--project <p>] [--by agent|lens|project|event]
#   gaps  [--since <Nd>]
#
# The utility is the sole reader and writer of ~/.claude/codeops-telemetry/events.jsonl.
# It parses data, never executes it, and it ALWAYS exits 0 — telemetry must never block
# work. Errors and refusals go to stderr only.
#
# Kill switches (checked in order, each turns the run into a silent no-op):
#   1. CODEOPS_TELEMETRY=0 in the environment
#   2. the current repo's CLAUDE.md quality block contains `telemetry: off`
#   3. jq is not on PATH (this one leaves a single stderr note)
#
# Emit validation is strict whole-line refusal: an unknown event type, an unknown key for
# that event, or an illegal value refuses the entire line (one stderr warning, nothing
# appended, still exit 0). The write gate protects the dataset: only enum/count/id/hash
# fields ever land in the file — never free text. Free text goes through --hash-text,
# which stores the first 8 hex of its SHA-256 and discards the text.
#
# CodeOps Skills Version: 3.12.0

set -uo pipefail

SELF="${BASH_SOURCE[0]}"

warn() { printf 'codeops-events: %s\n' "$1" >&2; }

# The version recorded in every event's envelope — read from this file's own stamp so the
# release sweep that rewrites the stamp comment updates both in one edit.
stamp_version() {
  local v
  v="$(grep -m1 -oE 'CodeOps Skills Version: [0-9][0-9.]*' "$SELF" 2>/dev/null | awk '{print $NF}')"
  printf '%s' "${v:-unknown}"
}

# ---------------------------------------------------------------------------
# Kill switches — global contract: every subcommand honors them.
# ---------------------------------------------------------------------------
if [[ "${CODEOPS_TELEMETRY:-}" == "0" ]]; then
  exit 0
fi

repo_toplevel="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -n "$repo_toplevel" && -f "$repo_toplevel/CLAUDE.md" ]]; then
  if sed -n '/CODEOPS-QUALITY:START/,/CODEOPS-QUALITY:END/p' "$repo_toplevel/CLAUDE.md" 2>/dev/null \
     | grep -qE '^[[:space:]]*telemetry:[[:space:]]*off[[:space:]]*(#.*)?$'; then
    exit 0
  fi
fi

if ! command -v jq >/dev/null 2>&1; then
  warn "jq not found on PATH — telemetry disabled"
  exit 0
fi

EVENTS_DIR="$HOME/.claude/codeops-telemetry"
EVENTS_FILE="$EVENTS_DIR/events.jsonl"

# ---------------------------------------------------------------------------
# Event catalog: allowed keys per event, value rules per key.
# Grow-only: add new events/keys here; never rename or repurpose existing ones.
# ---------------------------------------------------------------------------
LENS_ENUM="correctness maintainability standards security perf api-surface concurrency"
REVIEWER_AGENTS="phase-reviewer security-auditor preflight-auditor perf-auditor"

allowed_keys_for() {
  case "$1" in
    skill_invoked)                  echo "skill" ;;
    agent_completed)                echo "agent feature phase duration_s" ;;
    phase_started|phase_completed)  echo "feature phase tag mode" ;;
    task_completed)                 echo "feature phase task verify attempts files_changed" ;;
    blocker_reported)               echo "feature phase task category" ;;
    review_run)                     echo "agent feature phase lenses findings_critical findings_major findings_minor" ;;
    finding_decided)                echo "agent feature phase severity lens decision fix_applied hash" ;;
    commit_gate)                    echo "mode blocked_by_finding severity" ;;
    preflight_run)                  echo "artifact clusters findings_critical findings_major findings_minor thorough" ;;
    gate_summary)                   echo "gate rounds questions decisions deferrals feature" ;;
    *)                              return 1 ;;
  esac
}

in_list() { # in_list <needle> <space-separated list>
  local needle="$1" hay=" $2 "
  [[ "$hay" == *" $needle "* ]]
}

# validate_value <event> <key> <value> — 0 if legal, 1 (with warning) otherwise.
validate_value() {
  local event="$1" key="$2" value="$3" member
  case "$key" in
    mode)
      if [[ "$event" == "commit_gate" ]]; then
        in_list "$value" "ask-commit auto-commit no-commit" && return 0
      else
        in_list "$value" "inline dispatched" && return 0
      fi
      ;;
    verify)     in_list "$value" "pass fail" && return 0 ;;
    category)   in_list "$value" "insufficient_packet ambiguous_decision verify_failure environment" && return 0 ;;
    severity)   in_list "$value" "critical major minor" && return 0 ;;
    decision)   in_list "$value" "accepted rejected deferred" && return 0 ;;
    gate)       in_list "$value" "grill_me zero_ambiguity preflight_gate" && return 0 ;;
    lens)       in_list "$value" "$LENS_ENUM" && return 0 ;;
    lenses)
      [[ -n "$value" ]] || return 1
      local IFS=','
      for member in $value; do
        in_list "$member" "$LENS_ENUM" || return 1
      done
      return 0
      ;;
    duration_s|attempts|files_changed|rounds|questions|decisions|deferrals|clusters|findings_critical|findings_major|findings_minor)
      [[ "$value" =~ ^[0-9]+$ ]] && return 0 ;;
    fix_applied|blocked_by_finding|thorough)
      in_list "$value" "true false" && return 0 ;;
    hash)       [[ "$value" =~ ^[0-9a-f]{8}$ ]] && return 0 ;;
    *)          [[ -n "$value" && ! "$value" =~ [[:space:]] ]] && return 0 ;;
  esac
  return 1
}

json_type_of() { # int | bool | list | string
  case "$1" in
    duration_s|attempts|files_changed|rounds|questions|decisions|deferrals|clusters|findings_critical|findings_major|findings_minor)
      echo int ;;
    fix_applied|blocked_by_finding|thorough) echo bool ;;
    lenses) echo list ;;
    *) echo string ;;
  esac
}

sha256_8() {
  if command -v sha256sum >/dev/null 2>&1; then
    printf '%s' "$1" | sha256sum | awk '{print $1}' | cut -c1-8
  else
    printf '%s' "$1" | shasum -a 256 | awk '{print $1}' | cut -c1-8
  fi
}

current_project() {
  if [[ -n "$repo_toplevel" ]]; then basename "$repo_toplevel"; else printf 'unknown'; fi
}

# append_line <json> — flock-guarded append; on systems without flock (stock macOS) a
# plain append is used: a single line under PIPE_BUF is effectively atomic.
append_line() {
  mkdir -p "$EVENTS_DIR" 2>/dev/null || { warn "cannot create $EVENTS_DIR"; return; }
  if command -v flock >/dev/null 2>&1; then
    {
      flock -x 9
      printf '%s\n' "$1" >&9
    } 9>>"$EVENTS_FILE"
  else
    printf '%s\n' "$1" >>"$EVENTS_FILE"
  fi
}

# ---------------------------------------------------------------------------
# emit
# ---------------------------------------------------------------------------
cmd_emit() {
  local src="skill" use_stdin=0 hash_text="" hash_text_set=0 event=""
  local -a f_keys=() f_vals=()
  local arg key value

  while [[ $# -gt 0 ]]; do
    arg="$1"
    case "$arg" in
      --src)
        [[ $# -ge 2 ]] || { warn "--src needs a value — refused"; return; }
        src="$2"; shift 2; continue ;;
      --stdin)
        use_stdin=1; shift; continue ;;
      --hash-text)
        [[ $# -ge 2 ]] || { warn "--hash-text needs a value — refused"; return; }
        hash_text="$2"; hash_text_set=1; shift 2; continue ;;
      --*)
        warn "unknown option '$arg' — refused"; return ;;
      *=*)
        f_keys+=("${arg%%=*}"); f_vals+=("${arg#*=}"); shift; continue ;;
      *)
        if [[ -z "$event" ]]; then event="$arg"; shift; continue; fi
        warn "unexpected argument '$arg' — refused"; return ;;
    esac
  done

  if ! in_list "$src" "skill hook"; then
    warn "illegal --src '$src' — refused"; return
  fi

  if [[ "$use_stdin" -eq 1 ]]; then
    emit_from_stdin "$src"
    return
  fi

  if [[ -z "$event" ]]; then
    warn "no event type given — refused"; return
  fi
  local allowed
  if ! allowed="$(allowed_keys_for "$event")"; then
    warn "unknown event type '$event' — refused"; return
  fi

  if [[ "$hash_text_set" -eq 1 ]]; then
    if ! in_list "hash" "$allowed"; then
      warn "event '$event' does not take a hash — refused"; return
    fi
    f_keys+=("hash"); f_vals+=("$(sha256_8 "$hash_text")")
  fi

  local i
  if [[ "${#f_keys[@]}" -gt 0 ]]; then
    for i in "${!f_keys[@]}"; do
      key="${f_keys[$i]}"; value="${f_vals[$i]}"
      if ! in_list "$key" "$allowed"; then
        warn "unknown key '$key' for event '$event' — refused"; return
      fi
      if ! validate_value "$event" "$key" "$value"; then
        warn "illegal value '$value' for key '$key' — refused"; return
      fi
    done
  fi

  # The three findings counters travel together or not at all.
  local has_findings=0 want_findings=0 found=0
  for key in findings_critical findings_major findings_minor; do
    if in_list "$key" "$allowed"; then want_findings=1; fi
  done
  if [[ "$want_findings" -eq 1 && "${#f_keys[@]}" -gt 0 ]]; then
    for i in "${!f_keys[@]}"; do
      case "${f_keys[$i]}" in findings_critical|findings_major|findings_minor) found=$((found + 1)) ;; esac
    done
    if [[ "$found" -gt 0 && "$found" -ne 3 ]]; then
      warn "findings_critical/major/minor must be given together — refused"; return
    fi
    [[ "$found" -eq 3 ]] && has_findings=1
  fi

  B_KEYS=()
  B_VALS=()
  if [[ "${#f_keys[@]}" -gt 0 ]]; then
    B_KEYS=(${f_keys[@]+"${f_keys[@]}"})
    B_VALS=(${f_vals[@]+"${f_vals[@]}"})
  fi
  build_and_append "$event" "$src" "" "$has_findings"
}

# build_and_append <event> <src> <session> <has_findings> — fields come in via the
# B_KEYS/B_VALS pair (plain globals keep this runnable on stock macOS bash 3.2).
B_KEYS=()
B_VALS=()
build_and_append() {
  local event="$1" src="$2" session="$3" has_findings="$4"
  local ts json i key value jtype fc="" fm="" fn=""

  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  json="$(jq -cn \
    --arg ts "$ts" --arg codeops "$(stamp_version)" --arg project "$(current_project)" \
    --arg src "$src" --arg event "$event" \
    '{v:1, ts:$ts, codeops:$codeops, project:$project, src:$src, event:$event}')"
  if [[ -n "$session" ]]; then
    json="$(jq -c --arg s "$session" '. + {session:$s}' <<<"$json")"
  fi

  [[ "${#B_KEYS[@]}" -gt 0 ]] || { finish_line "$json" "$has_findings" "$fc" "$fm" "$fn"; return; }
  for i in "${!B_KEYS[@]}"; do
    key="${B_KEYS[$i]}"; value="${B_VALS[$i]}"
    case "$key" in
      findings_critical) fc="$value"; continue ;;
      findings_major)    fm="$value"; continue ;;
      findings_minor)    fn="$value"; continue ;;
    esac
    jtype="$(json_type_of "$key")"
    case "$jtype" in
      int|bool) json="$(jq -c --arg k "$key" --argjson x "$value" '. + {($k): $x}' <<<"$json")" ;;
      list)     json="$(jq -c --arg k "$key" --argjson x "$(jq -cn --arg s "$value" '$s | split(",")')" '. + {($k): $x}' <<<"$json")" ;;
      *)        json="$(jq -c --arg k "$key" --arg x "$value" '. + {($k): $x}' <<<"$json")" ;;
    esac
  done

  finish_line "$json" "$has_findings" "$fc" "$fm" "$fn"
}

# finish_line <json> <has_findings> <critical> <major> <minor>
finish_line() {
  local json="$1" has_findings="$2" fc="$3" fm="$4" fn="$5"
  if [[ "$has_findings" -eq 1 ]]; then
    json="$(jq -c --argjson c "$fc" --argjson m "$fm" --argjson n "$fn" \
      '. + {findings:{critical:$c, major:$m, minor:$n}}' <<<"$json")"
  fi
  append_line "$json"
}

# codeops_agent_from_subagent_type <subagent_type> — print the CodeOps agent name, or nothing.
#
# A dispatch belongs to CodeOps when the tool's subagent_type is "codeops:<name>", or a bare
# "<name>" matching a definition in the plugin's own agents/ directory. Resolving against that
# directory keeps a single source of truth — adding or renaming an agent needs no edit here — and
# it still attributes a project-local override in .claude/agents/, which arrives without the
# prefix. Anything else (Explore, general-purpose, a user's own agent) is not a CodeOps dispatch
# and yields nothing, so ordinary agent use never pollutes per-agent statistics.
codeops_agent_from_subagent_type() {
  local raw="$1" name agents_dir
  [[ -n "$raw" ]] || return 0
  name="${raw#codeops:}"
  # A plain agent name only — this value reaches a filesystem path, so anything containing a
  # separator or traversal is refused rather than canonicalized.
  [[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || return 0
  agents_dir="$(cd -- "$(dirname -- "$SELF")/../agents" 2>/dev/null && pwd)" || return 0
  [[ -f "$agents_dir/$name.md" ]] && printf '%s' "$name"
  return 0
}

# ---------------------------------------------------------------------------
# emit --stdin (hook mode) — reads one PostToolUse payload from stdin.
#
# Skill tool          → skill_invoked  (skill name from the tool input)
# Agent tool          → agent_completed; when line 1 of the prompt is a dispatch header
#                       of the form [codeops-dispatch agent=<a> feature=<f> phase=<p>]
#                       those fields are populated — absent or malformed headers still
#                       emit the event with the fields omitted, so the gap is measurable.
# Task tool           → same as Agent (legacy alias of the subagent tool).
# Anything else       → silently ignored (the hook matcher should not send it).
# ---------------------------------------------------------------------------
emit_from_stdin() {
  local src="$1" payload tool session ms first_line inner tokpair k v skill event="" dispatched_agent=""
  payload="$(cat 2>/dev/null || true)"
  if ! jq -e . >/dev/null 2>&1 <<<"$payload"; then
    warn "malformed hook payload JSON — refused"
    return
  fi
  tool="$(jq -r '.tool_name // ""' <<<"$payload")"
  session="$(jq -r '.session_id // ""' <<<"$payload")"
  ms="$(jq -r '.duration.elapsed_milliseconds // .tool_response.totalDurationMs // ""' <<<"$payload")"
  ms="${ms%%.*}"

  B_KEYS=()
  B_VALS=()
  case "$tool" in
    Skill)
      event="skill_invoked"
      skill="$(jq -r '.tool_input.skill // ""' <<<"$payload")"
      if ! validate_value "$event" "skill" "$skill"; then
        warn "hook payload lacks a usable skill name — refused"
        return
      fi
      B_KEYS+=("skill")
      B_VALS+=("$skill")
      ;;
    Agent|Task)
      event="agent_completed"
      # The tool's own subagent_type is what actually ran, so it outranks the prose header —
      # which only some dispatch paths require and which can go stale when copy-pasted.
      dispatched_agent="$(codeops_agent_from_subagent_type \
        "$(jq -r '.tool_input.subagent_type // ""' <<<"$payload")")"
      first_line="$(jq -r '.tool_input.prompt // "" | split("\n")[0]' <<<"$payload")"
      if [[ "$first_line" == "[codeops-dispatch "*"]" ]]; then
        inner="${first_line#\[codeops-dispatch }"
        inner="${inner%]}"
        for tokpair in $inner; do
          [[ "$tokpair" == *=* ]] || continue
          k="${tokpair%%=*}"
          v="${tokpair#*=}"
          case "$k" in
            agent)
              # Only a fallback: when subagent_type identified the agent, the header's claim is
              # ignored, since a copy-pasted header can name an agent that never ran.
              [[ -n "$dispatched_agent" ]] && continue
              if validate_value "$event" "$k" "$v"; then
                B_KEYS+=("$k")
                B_VALS+=("$v")
              fi
              ;;
            feature|phase)
              # Not derivable from the payload, so the header remains their sole source.
              if validate_value "$event" "$k" "$v"; then
                B_KEYS+=("$k")
                B_VALS+=("$v")
              fi
              ;;
          esac
        done
      fi
      if [[ -n "$dispatched_agent" ]]; then
        B_KEYS+=("agent")
        B_VALS+=("$dispatched_agent")
      fi
      if [[ -n "$ms" && "$ms" =~ ^[0-9]+$ ]]; then
        B_KEYS+=("duration_s")
        B_VALS+=("$((ms / 1000))")
      fi
      ;;
    *)
      return
      ;;
  esac

  build_and_append "$event" "$src" "$session" 0
}

# ---------------------------------------------------------------------------
# stats / gaps — the only readers of the events file. Both pre-aggregate so
# consumers relay a small table instead of re-reading raw events.
# ---------------------------------------------------------------------------

parse_since() { # "14d" or "14" → the day count, empty output if unusable
  local s="$1"
  s="${s%d}"
  [[ "$s" =~ ^[0-9]+$ ]] && printf '%s' "$s"
}

# read_events <since_days> <project> — filtered events, one JSON object per line.
# Corrupt lines are skipped rather than fatal.
read_events() {
  local since_days="$1" project="$2" cutoff=""
  [[ -f "$EVENTS_FILE" ]] || return 0
  if [[ -n "$since_days" ]]; then
    cutoff="$(date -u -d "$since_days days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
      || date -u -v -"${since_days}d" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || true)"
  fi
  jq -cR --arg cutoff "$cutoff" --arg project "$project" \
    'fromjson? // empty
     | select(($cutoff == "" or .ts >= $cutoff) and ($project == "" or .project == $project))' \
    "$EVENTS_FILE" 2>/dev/null || true
}

format_table() { # tab-separated rows → aligned columns
  awk -F'\t' '{ printf "%-24s", $1; for (i = 2; i <= NF; i++) printf " %9s", $i; printf "\n" }'
}

stats_by_agent() {
  jq -rs '
    def pct(a; r): if r == 0 then "n/a" else ((((a / r) * 100) + 0.5) | floor | tostring) + "%" end;
    . as $ev
    | ([ $ev[] | select(.event == "agent_completed" and .agent != null) | .agent ]
       + [ $ev[] | select(.event == "finding_decided" and .agent != null) | .agent ] | unique) as $agents
    | if ($agents | length) == 0 then "no agent activity in range"
      else
        (["agent", "runs", "avg_s", "ruled", "accepted", "acceptance"] | @tsv),
        ($agents[] as $a
         | [ $ev[] | select(.event == "agent_completed" and .agent == $a) ] as $ac
         | [ $ev[] | select(.event == "finding_decided" and .agent == $a) ] as $fd
         | ($fd | map(select(.decision == "accepted" or .decision == "rejected")) | length) as $ruled
         | ($fd | map(select(.decision == "accepted")) | length) as $acc
         | [ $ac[] | .duration_s // empty ] as $durs
         | [ $a, ($ac | length),
             (if ($durs | length) == 0 then "-" else ((($durs | add) / ($durs | length) + 0.5) | floor) end),
             $ruled, $acc, pct($acc; $ruled) ]
         | @tsv)
      end' | format_table
}

stats_by_lens() {
  jq -rs '
    def pct(a; r): if r == 0 then "n/a" else ((((a / r) * 100) + 0.5) | floor | tostring) + "%" end;
    . as $ev
    | ([ $ev[] | select(.event == "review_run") | (.lenses // [])[] ]
       + [ $ev[] | select(.event == "finding_decided" and .lens != null) | .lens ] | unique) as $ls
    | if ($ls | length) == 0 then "no lens activity in range"
      else
        (["lens", "reviews", "ruled", "accepted", "acceptance"] | @tsv),
        ($ls[] as $l
         | ([ $ev[] | select(.event == "review_run" and ((.lenses // []) | index($l)) != null) ] | length) as $runs
         | [ $ev[] | select(.event == "finding_decided" and .lens == $l) ] as $fd
         | ($fd | map(select(.decision == "accepted" or .decision == "rejected")) | length) as $ruled
         | ($fd | map(select(.decision == "accepted")) | length) as $acc
         | [ $l, $runs, $ruled, $acc, pct($acc; $ruled) ]
         | @tsv)
      end' | format_table
}

stats_by_event() {
  jq -rs '
    (["event", "count"] | @tsv),
    (group_by(.event) | sort_by(-length)[] | [ .[0].event, length ] | @tsv)' | format_table
}

stats_by_project() {
  jq -rs '
    (["project", "count"] | @tsv),
    (group_by(.project) | sort_by(-length)[] | [ .[0].project, length ] | @tsv)' | format_table
}

stats_overview() {
  jq -rs '
    . as $ev
    | (["events total", ($ev | length)] | @tsv),
      (["src skill", ([ $ev[] | select(.src == "skill") ] | length)] | @tsv),
      (["src hook", ([ $ev[] | select(.src == "hook") ] | length)] | @tsv),
      (["projects", ([ $ev[] | .project ] | unique | join(","))] | @tsv),
      "",
      (["event", "count"] | @tsv),
      ($ev | group_by(.event) | sort_by(-length)[] | [ .[0].event, length ] | @tsv)' | format_table
}

cmd_stats() {
  local since="" by="" project="" events
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --since)
        [[ $# -ge 2 ]] || { warn "--since needs a value"; return; }
        since="$(parse_since "$2" || true)"
        [[ -n "$since" ]] || { warn "unusable --since value '$2' (want e.g. 14d)"; return; }
        shift 2 ;;
      --project)
        [[ $# -ge 2 ]] || { warn "--project needs a value"; return; }
        project="$2"; shift 2 ;;
      --by)
        [[ $# -ge 2 ]] || { warn "--by needs a value"; return; }
        by="$2"
        in_list "$by" "agent lens project event" || { warn "unusable --by value '$by'"; return; }
        shift 2 ;;
      *) warn "unknown stats option '$1'"; return ;;
    esac
  done
  events="$(read_events "$since" "$project")"
  if [[ -z "$events" ]]; then
    printf 'no events recorded%s\n' "${since:+ in the last ${since}d}"
    return
  fi
  case "$by" in
    agent)   stats_by_agent   <<<"$events" ;;
    lens)    stats_by_lens    <<<"$events" ;;
    event)   stats_by_event   <<<"$events" ;;
    project) stats_by_project <<<"$events" ;;
    *)       stats_overview   <<<"$events" ;;
  esac | head -n 40
}

cmd_gaps() {
  local since="" events
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --since)
        [[ $# -ge 2 ]] || { warn "--since needs a value"; return; }
        since="$(parse_since "$2" || true)"
        [[ -n "$since" ]] || { warn "unusable --since value '$2' (want e.g. 14d)"; return; }
        shift 2 ;;
      *) warn "unknown gaps option '$1'"; return ;;
    esac
  done
  events="$(read_events "$since" "")"
  if [[ -z "$events" ]]; then
    printf 'no events recorded%s\n' "${since:+ in the last ${since}d}"
    return
  fi
  jq -rs --arg agents "$REVIEWER_AGENTS" '
    def key: "\(.project)|\(.feature // "?")|\(.phase // "?")";
    ($agents | split(" ")) as $rset
    | . as $ev
    | [ $ev[] | select(.event == "agent_completed")
              | select((.agent // "") as $a | ($rset | index($a)) != null) ] as $done
    | ([ $ev[] | select(.event == "review_run" or .event == "finding_decided") | key ] | unique) as $covered
    | ($done | length) as $total
    | ([ $done[] | select(key as $k | ($covered | index($k)) != null) ] | length) as $ok
    | if $total == 0 then "no reviewer/auditor completions in range"
      else
        ($total - $ok) as $gap
        | (((($gap / $total) * 100) + 0.5) | floor) as $pct
        | "reviewer/auditor completions: \($total)",
          "with downstream ruling:       \($ok)",
          "gaps:                         \($gap) (\($pct)%)"
      end' <<<"$events"
}

# ---------------------------------------------------------------------------
# Dispatch — every path ends in exit 0.
# ---------------------------------------------------------------------------
sub="${1:-}"
[[ $# -gt 0 ]] && shift
case "$sub" in
  emit)  cmd_emit "$@" ;;
  stats) cmd_stats "$@" ;;
  gaps)  cmd_gaps "$@" ;;
  "")    warn "usage: codeops-events.sh emit|stats|gaps …" ;;
  *)     warn "unknown subcommand '$sub'" ;;
esac
exit 0
