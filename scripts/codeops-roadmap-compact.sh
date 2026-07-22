#!/usr/bin/env bash
#
# codeops-roadmap-compact.sh — deterministic roadmap slimming engine.
#
# CodeOps Skills Version: 3.12.0
#
# The roadmap skill's `compact` action owns the JUDGMENT (rewriting a verbose table cell down to a
# terse phrase); this script owns the MECHANICAL, testable, safety-critical half (the same
# prose-vs-script division as codeops-roadmap-sync.sh / codeops-migrate.sh). For every roadmap in
# the repo it:
#   - removes the `## Notes` running-log section (heading-anchored: from the `## Notes` line through
#     the line before the next `## ` heading, or EOF) — the one destructive op;
#   - flags oversized Tracker/Features table cells to stdout as a worklist for the `compact` action.
# It NEVER rewrites a table cell, never touches a header line or the Tracker/Features tables, and
# never executes repo data. Because deleting the Notes log is only reversible through git, apply
# refuses to run on a non-git or dirty tree (mirrors codeops-migrate.sh) so a clean, recoverable
# commit always precedes any mutation.
#
# Usage:
#   codeops-roadmap-compact.sh            # apply: strip Notes sections in place; print flagged cells
#   codeops-roadmap-compact.sh --dry-run  # preview strips + flags; change nothing
#   codeops-roadmap-compact.sh --check    # report only; exit 1 if any roadmap still carries a
#                                         #   `## Notes` section or an oversized cell
#   codeops-roadmap-compact.sh -h|--help  # this usage
# Exit: 0 = success / clean / no-op; 1 = refusal (not a git repo, or dirty tree) OR drift found
#       under --check; 2 = bad usage; 3 = python3 unavailable.

set -uo pipefail

MODE="apply"
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

# -----------------------------------------------------------------------------
# Git safety. Apply DELETES the Notes log, so it must run on a clean, recoverable tree (mirrors
# codeops-migrate.sh:67-99). --check / --dry-run write nothing, so they may report on any tree.
# All modes operate from the git root when there is one, so relative roadmap paths are stable.
# -----------------------------------------------------------------------------
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [[ "$MODE" == "apply" ]]; then
  if [[ -z "$ROOT" ]]; then
    printf 'ERROR: not inside a git repository — compact deletes the Notes log, which is only\n' >&2
    printf '       recoverable via git. Run it inside the repository.\n' >&2
    exit 1
  fi
  cd "$ROOT" || { printf 'ERROR: cannot enter repo root %s\n' "$ROOT" >&2; exit 1; }
  if [[ -n "$(git status --porcelain)" ]]; then
    printf 'ERROR: working tree is dirty — compact must run on a clean tree so the removed notes\n' >&2
    printf '       stay recoverable via git. Commit or stash your changes first, then re-run.\n' >&2
    exit 1
  fi
else
  [[ -n "$ROOT" ]] && cd "$ROOT"
fi

# Layout detection — the canonical grep from _shared/layout-convention.md.
layout="flat"
if [[ -f codeops/.codeops.yml ]] && grep -Eq '^codeopsLayout:[[:space:]]*nested[[:space:]]*$' codeops/.codeops.yml; then
  layout="nested"
fi

MODE="$MODE" LAYOUT="$layout" python3 - <<'PY'
import glob, os, re, sys

mode = os.environ["MODE"]       # apply | check | dry
layout = os.environ["LAYOUT"]   # flat | nested

# ---------------------------------------------------------------------------
# Roadmap discovery (current repo only; every 00-roadmap.md incl. _archive/).
# ---------------------------------------------------------------------------
def discover():
    paths = []
    if layout == "flat":
        if os.path.isfile("plans/00-roadmap.md"):
            paths.append("plans/00-roadmap.md")
        paths += sorted(glob.glob("plans/_archive/*/00-roadmap.md"))
    else:
        if os.path.isfile("codeops/00-roadmap.md"):
            paths.append("codeops/00-roadmap.md")
        paths += sorted(glob.glob("codeops/features/*/00-roadmap.md"))
        paths += sorted(glob.glob("codeops/_archive/*/00-roadmap.md"))
    return paths

# ---------------------------------------------------------------------------
# Notes-section removal (heading-anchored). Removes the block from a `## Notes` heading through the
# line before the next `## ` heading (or EOF). Every other line — headers, `## Tracker`,
# `## Features`, `## Archived` — is left byte-for-byte unchanged. When something was removed the
# trailing blank run at EOF is collapsed to a single newline so the file stays a clean POSIX text
# file. Returns (new_text, removed_bool, removed_block_text).
# ---------------------------------------------------------------------------
NOTES_HEADING = re.compile(r'^##[ \t]+Notes[ \t]*$')
ANY_H2 = re.compile(r'^##[ \t]')

def strip_notes(text):
    lines = text.splitlines(keepends=True)
    out, removed_block = [], []
    i, n, removed = 0, len(lines), False
    while i < n:
        bare = lines[i].rstrip('\r\n')
        if NOTES_HEADING.match(bare):
            removed = True
            removed_block.append(lines[i]); i += 1
            while i < n and not ANY_H2.match(lines[i].rstrip('\r\n')):
                removed_block.append(lines[i]); i += 1
        else:
            out.append(lines[i]); i += 1
    result = "".join(out)
    if removed:
        result = result.rstrip('\n') + '\n'
    return result, removed, "".join(removed_block)

# ---------------------------------------------------------------------------
# Fat-cell flagging (report only — the engine never rewrites a cell). Parses every pipe table
# (a header row immediately followed by a `---` separator), then flags any DATA-row cell — skipping
# the first (id/feature) column — whose trimmed content is oversized: > 200 chars, or an embedded
# line break, or more than one sentence (>= 2 mid-cell `. ` / `; ` breaks). The column name comes
# from the table's own header row, so the check is layout- and rename-agnostic.
# ---------------------------------------------------------------------------
SEP_CELL = re.compile(r'^:?-{1,}:?$')
SENTENCE_BREAK = re.compile(r'[.;] ')

def split_cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def is_separator(line):
    if not line.lstrip().startswith('|'):
        return False
    cells = split_cells(line)
    return bool(cells) and all(SEP_CELL.match(c) for c in cells if c)

def cell_is_fat(cell):
    if len(cell) > 200:
        return True
    if '<br' in cell.lower() or '\n' in cell:
        return True
    if len(SENTENCE_BREAK.findall(cell)) >= 2:
        return True
    return False

def flag_cells(text, path):
    flags = []
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        if line.lstrip().startswith('|') and i + 1 < n and is_separator(lines[i + 1]):
            header = split_cells(line)
            j = i + 2
            while j < n and lines[j].lstrip().startswith('|'):
                if not is_separator(lines[j]):
                    cells = split_cells(lines[j])
                    row_id = cells[0] if cells else ''
                    for c in range(1, len(cells)):
                        if cell_is_fat(cells[c]):
                            col = header[c] if c < len(header) else f'col{c}'
                            flags.append(f"FLAG {path}:{row_id}:{col} ({len(cells[c])} chars)")
                j += 1
            i = j
        else:
            i += 1
    return flags

# ---------------------------------------------------------------------------
# Drive the roadmaps per mode.
# ---------------------------------------------------------------------------
roadmaps = discover()
stripped = 0
flag_count = 0
drift = 0

for path in roadmaps:
    try:
        text = open(path, encoding='utf-8').read()
    except OSError as e:
        print(f"WARN: cannot read {path}: {e}", file=sys.stderr)
        continue
    new_text, removed, block = strip_notes(text)
    flags = flag_cells(new_text, path)

    if mode == 'apply':
        if removed:
            try:
                open(path, 'w', encoding='utf-8').write(new_text)
            except OSError as e:
                print(f"ERROR: failed to write {path}: {e}", file=sys.stderr)
                sys.exit(1)
            print(f"STRIP {path}: ## Notes ({len(block.encode('utf-8'))} bytes)")
            stripped += 1
        for f in flags:
            print(f)
            flag_count += 1
    elif mode == 'dry':
        if removed:
            print(f"WOULD-STRIP {path}: ## Notes ({len(block.encode('utf-8'))} bytes)")
        for f in flags:
            print(f)
    else:  # check
        if removed:
            print(f"NOTES {path}: ## Notes section present")
            drift += 1
        for f in flags:
            print(f)
            drift += 1

if mode == 'apply':
    if stripped:
        tail = f"; {flag_count} cell(s) flagged for trimming (see FLAG lines above)." if flag_count else "."
        print(f"compact: stripped the Notes log from {stripped} roadmap(s){tail}")
    else:
        print("compact: all roadmaps already lean — nothing to do.")
    sys.exit(0)
elif mode == 'dry':
    print("(dry-run: nothing written)")
    sys.exit(0)
else:  # check
    if drift:
        print(f"compact: {drift} issue(s) found — run the roadmap compact action to slim these.")
        sys.exit(1)
    print("compact: all roadmaps already lean.")
    sys.exit(0)
PY
