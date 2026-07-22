#!/usr/bin/env bash
#
# codeops-roadmap-sync.sh — deterministic roadmap counter/cascade recomputation.
#
# CodeOps Artifact Schema: 1
#
# The roadmap skill owns stage JUDGMENT; this script owns the ARITHMETIC (the prose-vs-script
# division, same as codeops-migrate.sh). It recomputes, from disk:
#   - each roadmap's header `> **Progress**: D / T (P%)` — counting only top-level `RD-*` rows at
#     ✅ Done / total `RD-*` rows (`T-*` task rows and `↳ DEF-n` sub-rows are excluded);
#   - nested layout only: each feature's portfolio row `Progress` (`D/T RDs`) and rolled-up
#     `Status`, and the portfolio header `> **Features**: X / Y done`.
# Roll-up precedence: any ⛔ → ⛔; all RDs Done with an open `## Open follow-ons` row → 🔄; all RDs
# Done and none open → ✅; any 🔄 → 🔄; else ⬜.
# It rewrites a computed value only when the existing value is the engine's own computed shape (a
# trailing ` · …` / ` (…)` annotation is preserved verbatim); a hand-maintained value (e.g. `n/a`,
# free text) is left untouched and reported as informational HELD, and that row's Status is not
# re-rolled. It never infers or changes a Stage cell, never touches Notes or prose, and never
# executes repo data.
#
# Usage:
#   codeops-roadmap-sync.sh            # rewrite the computed values in place
#   codeops-roadmap-sync.sh --check    # report drift, change nothing; exit 1 on drift
#   codeops-roadmap-sync.sh --dry-run  # print the would-be updates, change nothing
# Exit: 0 = in sync / updated / only HELD; 1 = drift found (--check) or write failure; 2 = bad
#       usage; 3 = python3 unavailable. HELD (preserved hand-maintained values) is informational
#       and never sets a non-zero exit.

set -uo pipefail

MODE="write"
for arg in "$@"; do
  case "$arg" in
    --check)   MODE="check" ;;
    --dry-run) MODE="dry" ;;
    -h|--help) grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) printf 'ERROR: unknown argument: %s\n' "$arg" >&2; exit 2 ;;
  esac
done

command -v python3 >/dev/null 2>&1 || {
  printf 'ERROR: python3 is required for roadmap parsing.\n' >&2
  exit 3
}

# Layout detection — the canonical grep from _shared/layout-convention.md.
layout="flat"
if [[ -f codeops/.codeops.yml ]] && grep -Eq '^codeopsLayout:[[:space:]]*nested[[:space:]]*$' codeops/.codeops.yml; then
  layout="nested"
fi

today="$(date '+%Y-%m-%d')"

MODE="$MODE" LAYOUT="$layout" TODAY="$today" python3 - <<'PY'
import glob, os, re, sys

mode = os.environ["MODE"]          # write | check | dry
layout = os.environ["LAYOUT"]      # flat | nested
today = os.environ["TODAY"]

drift = []      # stale COMPUTED values — a real correction (--check exits 1; write applies it)
held = []       # preserved hand-maintained values — informational, never an error
changed = []    # files rewritten (write mode)

# Computed-value shapes. Group 1 is the token the engine owns and may rewrite; group 2 is a
# free-text annotation the engine must preserve verbatim. Patterns are linear — an anchored greedy
# tail with no nested quantifiers — so untrusted cell text cannot cause pathological backtracking.
FEATURE_PROGRESS = re.compile(r'^(\d+ / \d+ \(\d+%\))(.*)$')   # per-feature "> **Progress**:" value
PORTFOLIO_PROG   = re.compile(r'^(\d+/\d+ RDs)(.*)$')          # portfolio Progress cell
FEATURES_HDR     = re.compile(r'^(\d+ / \d+ done)(.*)$')       # portfolio "> **Features**:" value

def parse_rows(text):
    """Top-level tracker rows as (id, stage, status) — skips header/separator/`↳` sub-rows."""
    rows = []
    in_table = False
    for line in text.splitlines():
        if re.match(r'\|\s*ID\s*\|', line):
            in_table = True
            continue
        if in_table:
            if not line.startswith('|'):
                in_table = False
                continue
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not cells or set(cells[0]) <= {'-', ' '}:
                continue
            rid = cells[0]
            if rid.startswith('↳') or rid in ('—', '-', ''):
                continue
            stage = cells[4] if len(cells) > 4 else ''
            status = cells[5] if len(cells) > 5 else ''
            rows.append((rid, stage, status))
    return rows

def is_rd_row(rid):
    """A top-level requirement row. `T-*` tasks and any non-RD id never count toward the fraction."""
    return bool(re.match(r'RD-\d', rid))

def progress_of(text):
    """(done, total, pct, rows) — the fraction counts only `RD-*` rows; `rows` keeps every parsed
    top-level row (incl. `T-*`) for the roll-up's status scan."""
    rows = parse_rows(text)
    rd_rows = [r for r in rows if is_rd_row(r[0])]
    total = len(rd_rows)
    done = sum(1 for _, stage, status in rd_rows if '✅' in status or stage.startswith('Done'))
    pct = round(done / total * 100) if total else 0
    return done, total, pct, rows

def has_open_followon(text):
    """True iff an `## Open follow-ons` section holds a table whose last column header is `Status`
    and at least one data row's Status cell contains no ✅. A section whose table is not
    `Status`-last is ignored (fail-safe — no false hold). A pure parse — it never affects the RD
    fraction, only the roll-up."""
    in_sec = False
    valid = False                                    # a `Status`-last header row was seen
    for line in text.splitlines():
        if re.match(r'^##\s+Open follow-ons\s*$', line):
            in_sec = True
            valid = False
            continue
        if in_sec and line.startswith('## '):
            break                                    # the next section ends it
        if in_sec and line.startswith('|'):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if not cells or set(cells[-1]) <= {'-', ' '}:
                continue                             # separator row
            if cells[-1] == 'Status':
                valid = True                         # header row: last column is `Status`
                continue
            if not valid or not cells[-1]:
                continue                             # no `Status`-last header yet, or empty cell
            if '✅' not in cells[-1]:
                return True
    return False

def replace_header(text, key, new_line):
    """Unconditionally replace a `> **Key**: …` line — used for the computed Last Updated stamp.
    The replacement is a literal callable so data-derived text is never read as a regex template."""
    pat = re.compile(r'(?m)^> \*\*' + re.escape(key) + r'\*\*:.*$')
    if pat.search(text):
        return pat.sub(lambda _m: new_line, text, count=1)
    return text

def sub_computed_header(text, key, computed_token, regex, path):
    """Rewrite a computed header (`Progress` / `Features`) only when its value is the engine's own
    computed shape and the token is stale, preserving any trailing free-text suffix. A value that
    is not the computed shape is left untouched and reported HELD."""
    pat = re.compile(r'(?m)^> \*\*' + re.escape(key) + r'\*\*: (.*)$')
    m = pat.search(text)
    if not m:
        drift.append(f"{path}: header line '> **{key}**:' not found (malformed — skipped)")
        return text, False
    value = m.group(1)
    cm = regex.match(value)
    if not cm:
        held.append(f"{path}: {key} '{value}' (hand-maintained)")
        return text, False
    if cm.group(1) == computed_token:
        return text, False                           # in sync (suffix already preserved in place)
    drift.append(f"{path}: {key} token '{cm.group(1)}' — computed '{computed_token}'")
    new_line = f"> **{key}**: {computed_token}{cm.group(2)}"
    return pat.sub(lambda _m: new_line, text, count=1), True

def sync_feature_roadmap(path):
    """Sync one flat/per-feature roadmap header; return (done, total, rows, feat_open)."""
    text = open(path, encoding='utf-8').read()
    done, total, pct, rows = progress_of(text)
    feat_open = has_open_followon(text)
    token = f"{done} / {total} ({pct}%)"
    text2, did = sub_computed_header(text, 'Progress', token, FEATURE_PROGRESS, path)
    if did and mode == 'write':
        text2 = replace_header(text2, 'Last Updated', f"> **Last Updated**: {today}")
        try:
            open(path, 'w', encoding='utf-8').write(text2)
            changed.append(path)
        except OSError as e:
            print(f"ERROR: failed to write {path}: {e}", file=sys.stderr)
            sys.exit(1)
    return done, total, rows, feat_open

def roll_up(done, total, rows, feat_open):
    """Feature Status from its rows. `⛔` on any blocked row wins; otherwise all RDs Done holds at
    `🔄` when a follow-on is open, else `✅`; else `🔄` if any row is executing; else `⬜`."""
    statuses = [s for _, _, s in rows]
    if any('⛔' in s for s in statuses):
        return '⛔'
    if total and done == total and feat_open:
        return '🔄'
    if total and done == total:
        return '✅'
    if any('🔄' in s for s in statuses):
        return '🔄'
    return '⬜'

if layout == 'flat':
    path = 'plans/00-roadmap.md'
    if not os.path.isfile(path):
        print('codeops-roadmap-sync: no roadmap found (flat layout) — nothing to sync.')
        sys.exit(0)
    sync_feature_roadmap(path)
else:
    features = {}
    for path in sorted(glob.glob('codeops/features/*/00-roadmap.md')):
        feat = path.split('/')[2]
        features[feat] = sync_feature_roadmap(path)
    # Portfolio cascade.
    ppath = 'codeops/00-roadmap.md'
    if os.path.isfile(ppath):
        text = open(ppath, encoding='utf-8').read()
        lines = text.splitlines()
        out, in_features, feature_rows_total, feature_rows_done = [], False, 0, 0
        for line in lines:
            if line.startswith('## Features'):
                in_features = True
            elif line.startswith('## ') and in_features:
                in_features = False
            if in_features and line.startswith('|'):
                cells = [c.strip() for c in line.strip().strip('|').split('|')]
                feat = cells[0] if cells else ''
                if feat in features and len(cells) >= 6:
                    done, total, rows, feat_open = features[feat]
                    cm = PORTFOLIO_PROG.match(cells[3])
                    if not cm:
                        # Hand-maintained cell (n/a, free text): preserve it, do NOT re-roll this
                        # row's Status, and exclude it from the computed Features tally.
                        held.append(f"{ppath}: row '{feat}' Progress '{cells[3]}' (hand-maintained)")
                    else:
                        roll = roll_up(done, total, rows, feat_open)
                        new_token = f"{done}/{total} RDs"
                        if cm.group(1) != new_token or cells[4] != roll:
                            drift.append(f"{ppath}: row '{feat}' is '{cells[3]}'/'{cells[4]}' "
                                         f"— computed '{new_token}'/'{roll}'")
                            cells[3] = new_token + cm.group(2)
                            cells[4] = roll
                            cells[5] = today if mode == 'write' else cells[5]
                            line = '| ' + ' | '.join(cells) + ' |'
                        feature_rows_total += 1
                        feature_rows_done += 1 if roll == '✅' else 0
            out.append(line)
        text2 = '\n'.join(out) + ('\n' if text.endswith('\n') else '')
        feat_token = f"{feature_rows_done} / {feature_rows_total} done"
        text2, _ = sub_computed_header(text2, 'Features', feat_token, FEATURES_HDR, ppath)
        if mode == 'write' and text2 != text:
            text2 = replace_header(text2, 'Last Updated', f"> **Last Updated**: {today}")
            try:
                open(ppath, 'w', encoding='utf-8').write(text2)
                changed.append(ppath)
            except OSError as e:
                print(f"ERROR: failed to write {ppath}: {e}", file=sys.stderr)
                sys.exit(1)
    else:
        drift.append(f"{ppath}: portfolio roadmap missing in nested layout")

if held:
    print('codeops-roadmap-sync: preserved hand-maintained values:')
    for h in held:
        print(f'  HELD {h}')

if drift:
    print('codeops-roadmap-sync: drift detected:')
    for d in drift:
        print(f'  DRIFT {d}')
    if mode == 'check':
        sys.exit(1)
    if mode == 'dry':
        print('(dry-run: nothing written)')
        sys.exit(0)
    print(f'codeops-roadmap-sync: updated {len(changed)} file(s): ' + ', '.join(changed))
    sys.exit(0)
else:
    if not held:
        print('codeops-roadmap-sync: all counters in sync — nothing to do.')
    sys.exit(0)
PY
