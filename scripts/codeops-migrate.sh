#!/usr/bin/env bash
#
# codeops-migrate.sh — deterministic flat→nested CodeOps migration engine.
#
# This is the single, unit-testable source of truth for the migration ALGORITHM (see
# plans/codeops-v2-layout/03-02-setup-codeops.md, PF-003). The setup_codeops skill owns the
# conversational UX (preview, confirmation, reporting) and DELEGATES the path arithmetic and the
# git mv apply to this script — so there is no prose-vs-script drift. scripts/migration-check.sh
# asserts this engine's move map, warnings, refusals, and idempotency against a fixture copy.
#
# It computes the move map from a flat-layout repo (today: one flat repo == one feature-set), scans
# for hazards (plans absent from the roadmap; links pointing out of the planning tree), refuses to
# run on a non-git or dirty tree, rejects/normalizes path-traversal slugs, is idempotent (a marker
# means "already migrated"), and applies via `git mv` (history preserved), writing the marker and
# the seeded portfolio roadmap LAST so an interrupted run never leaves a false "migrated" marker.
#
# Security: never executes repo data; the feature slug is sanitized so it can never escape
# codeops/features/. All mutation requires an explicit --yes; absent that, it only previews.
#
# Usage:
#   codeops-migrate.sh --dry-run     # compute + print the move map + warnings; change nothing
#   codeops-migrate.sh --yes         # apply the migration via git mv (no interactive prompt)
#   codeops-migrate.sh               # same as --dry-run (safe default; never mutates without --yes)
# Exit: 0 = success / no-op; 1 = refusal (not a git repo, dirty tree); 2 = bad usage.

set -uo pipefail

DRY=0
YES=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --yes)     YES=1 ;;
    -h|--help)
      grep -E '^# ' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$arg" >&2
      exit 2 ;;
  esac
done

# Apply only on an explicit --yes that is not paired with --dry-run (preview always wins).
APPLY=0
if [[ "$YES" -eq 1 && "$DRY" -eq 0 ]]; then
  APPLY=1
fi

HAVE_PY3=0
command -v python3 >/dev/null 2>&1 && HAVE_PY3=1

# slugify <text> — lowercase, collapse every non-alphanumeric run to a single '-', trim '-'.
# This sanitizes the feature slug so it can never contain '/', '..', or be absolute (Security).
slugify() {
  if [[ "$HAVE_PY3" -eq 1 ]]; then
    python3 - "$1" <<'PY'
import re, sys
s = re.sub(r'[^a-z0-9]+', '-', sys.argv[1].lower()).strip('-')
print(s)
PY
  else
    printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
  fi
}

# -----------------------------------------------------------------------------
# Preconditions: must be a git repo; idempotent if already migrated; refuse if dirty.
# -----------------------------------------------------------------------------
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  printf 'ERROR: not inside a git repository (git is required for git mv).\n' >&2
  exit 1
}
cd "$ROOT"

if [[ -f codeops/.codeops.yml ]]; then
  printf 'codeops-migrate: already migrated (codeops/.codeops.yml present) — nothing to do (no-op).\n'
  exit 0
fi

# Is there any flat-layout content to migrate at all?
shopt -s nullglob
plan_dirs=(plans/*/)
has_flat=0
[[ -d requirements ]] && has_flat=1
[[ -f plans/00-roadmap.md ]] && has_flat=1
[[ ${#plan_dirs[@]} -gt 0 ]] && has_flat=1
if [[ "$has_flat" -eq 0 ]]; then
  printf 'codeops-migrate: no flat-layout artifacts found; nothing to migrate.\n'
  printf '  (For a fresh repo use the setup_codeops scaffold to create the codeops/ skeleton.)\n'
  exit 0
fi

# Migration must run on a clean tree so the whole move lands as one reviewable commit.
if [[ -n "$(git status --porcelain)" ]]; then
  printf 'ERROR: working tree is dirty — migration must run on a clean tree so it lands as a\n' >&2
  printf '       single reviewable commit. Commit or stash your changes first, then re-run.\n' >&2
  exit 1
fi

# A non-directory named `codeops` makes every apply step impossible — refuse up front with a
# clear message instead of failing step-by-step (AR #18).
if [[ -e codeops && ! -d codeops ]]; then
  printf 'ERROR: `codeops` exists but is not a directory — the nested layout cannot be created.\n' >&2
  printf '       Move or remove it, then re-run.\n' >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Derive the feature slug (roadmap header → else repo dir name), then sanitize.
# -----------------------------------------------------------------------------
slug=""
slug_src=""
if [[ -f plans/00-roadmap.md ]]; then
  header="$(grep -E '^> \*\*Feature-Set\*\*:' plans/00-roadmap.md | head -1 | sed -E 's/^> \*\*Feature-Set\*\*:[[:space:]]*//')"
  if [[ -n "$header" ]]; then
    slug="$(slugify "$header")"
    slug_src="roadmap-header"
  fi
fi
if [[ -z "$slug" ]]; then
  slug="$(slugify "$(basename "$ROOT")")"
  slug_src="dir-name"
fi
# Final safety net: a slug must be a single safe path component.
if [[ -z "$slug" || "$slug" == *"/"* || "$slug" == *".."* ]]; then
  printf 'ERROR: could not derive a safe feature slug (got: %q).\n' "$slug" >&2
  exit 1
fi

# -----------------------------------------------------------------------------
# Compute the move map (no file changes here).
# -----------------------------------------------------------------------------
moves=()   # each entry: "src|dst"
[[ -d requirements ]] && moves+=("requirements/|codeops/features/$slug/requirements/")
for d in plans/*/; do
  name="$(basename "$d")"
  [[ "$name" == "_archive" ]] && continue
  moves+=("plans/$name/|codeops/features/$slug/plans/$name/")
done
[[ -f plans/00-roadmap.md ]] && moves+=("plans/00-roadmap.md|codeops/features/$slug/00-roadmap.md")
if [[ -d plans/_archive ]]; then
  for a in plans/_archive/*/; do
    aname="$(basename "$a")"
    moves+=("plans/_archive/$aname/|codeops/_archive/$aname/")
  done
  # Loose FILES directly under plans/_archive/ move too — leaving them behind would strand a
  # residual plans/ tree after the marker is written (AR #18).
  for af in plans/_archive/*; do
    [[ -f "$af" ]] || continue
    moves+=("$af|codeops/_archive/$(basename "$af")")
  done
fi

# -----------------------------------------------------------------------------
# Hazard scan → warnings (never block; the user resolves these by hand after the move).
# -----------------------------------------------------------------------------
warnings=()
# (a) plan folders on disk but not referenced in the roadmap.
if [[ -f plans/00-roadmap.md ]]; then
  for d in plans/*/; do
    name="$(basename "$d")"
    [[ "$name" == "_archive" ]] && continue
    if ! grep -qF "$name" plans/00-roadmap.md; then
      warnings+=("plan-not-in-roadmap: plans/$name/ is on disk but not referenced in the roadmap")
    fi
  done
fi
# (a2) loose files directly under plans/ that are NOT the roadmap and NOT inside a plan dir.
#      The move map only relocates plan dirs + plans/00-roadmap.md, so these would otherwise be
#      left behind in a surviving plans/ after the marker is written — a half-migrated state. We
#      cannot guess a feature target for a stray file, so we surface it (never silently orphan it).
for f in plans/*; do
  [[ -f "$f" ]] || continue
  [[ "$(basename "$f")" == "00-roadmap.md" ]] && continue
  warnings+=("loose-file-not-migrated: $f is directly under plans/ and is left in place (move it by hand)")
done
# (a3) loose files directly under plans/_archive/ ARE migrated (into codeops/_archive/), but get
#      surfaced so the user knows an unusual artifact was found and relocated.
if [[ -d plans/_archive ]]; then
  for af in plans/_archive/*; do
    [[ -f "$af" ]] || continue
    warnings+=("archive-loose-file: $af is a loose file under plans/_archive/ — it will be moved to codeops/_archive/$(basename "$af")")
  done
fi
# (b) relative links in plan docs that point OUT of the planning tree (into source, etc.).
#     A structure-preserving move keeps intra-codeops links valid; only out-of-tree links can
#     break, so we surface them as warnings rather than silently rewriting them (AR #16).
if [[ "$HAVE_PY3" -eq 1 && -d plans ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && warnings+=("$line")
  done < <(python3 - "$ROOT" <<'PY'
import os, re, sys
root = sys.argv[1]
plans = os.path.join(root, "plans")
link_re = re.compile(r'\]\(([^)]+)\)')
inside = ("plans" + os.sep, "requirements" + os.sep)
for dirpath, _dirs, files in os.walk(plans):
    for fn in files:
        if not fn.endswith(".md"):
            continue
        fp = os.path.join(dirpath, fn)
        rel = os.path.relpath(fp, root)
        try:
            text = open(fp, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in link_re.finditer(text):
            tgt = m.group(1).strip()
            if tgt.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not tgt.startswith(".."):
                continue
            norm = os.path.normpath(os.path.join(os.path.dirname(rel), tgt))
            if not (norm.startswith(inside) or norm in ("plans", "requirements")):
                print(f"source-relative-link: {rel} -> {tgt}")
PY
  )
fi

# -----------------------------------------------------------------------------
# Print the preview (always — dry-run, default, and as the apply log).
# -----------------------------------------------------------------------------
if [[ "$APPLY" -eq 1 ]]; then
  printf 'codeops-migrate: applying flat → nested migration (git mv)\n'
else
  printf 'codeops-migrate: dry-run preview (no changes will be made)\n'
fi
printf 'SLUG: %s (source: %s)\n' "$slug" "$slug_src"
for m in "${moves[@]}"; do
  printf 'MOVE %s -> %s\n' "${m%%|*}" "${m##*|}"
done
printf 'CREATE codeops/.codeops.yml\n'
printf 'CREATE codeops/codeops.json\n'
printf 'CREATE codeops/00-roadmap.md\n'
for w in "${warnings[@]:-}"; do
  [[ -n "$w" ]] && printf 'WARN %s\n' "$w"
done

if [[ "$APPLY" -ne 1 ]]; then
  [[ "$DRY" -eq 0 ]] && printf '\n(preview only; re-run with --yes to apply)\n'
  exit 0
fi

# -----------------------------------------------------------------------------
# Apply: git mv each mapping, then write the marker + seeded portfolio LAST.
#
# Every step is failure-checked (AR #18): the FIRST failed step aborts the apply with a
# non-zero exit, the marker is NEVER written after a failure (so the idempotency guard can
# never brick a retry on a half-migrated tree), and the report names the failing step.
# `set -e` is deliberately not relied on — explicit checks avoid its conditional/subshell
# pitfalls and give a named failure.
# -----------------------------------------------------------------------------
fail_apply() {
  printf '\ncodeops-migrate: FAILED at step: %s\n' "$1" >&2
  printf '  The migration did NOT complete and NO layout marker was written.\n' >&2
  printf '  Inspect with "git status"; undo any partial moves with "git reset --hard",\n' >&2
  printf '  fix the cause, then re-run.\n' >&2
  exit 1
}
step() {
  local desc="$1"; shift
  "$@" || fail_apply "$desc"
}

step "mkdir codeops/features/$slug/plans" mkdir -p "codeops/features/$slug/plans"
[[ -d plans/_archive ]] && step "mkdir codeops/_archive" mkdir -p codeops/_archive

[[ -d requirements ]] && step "git mv requirements" git mv requirements "codeops/features/$slug/requirements"
for d in plans/*/; do
  name="$(basename "$d")"
  [[ "$name" == "_archive" ]] && continue
  step "git mv plans/$name" git mv "plans/$name" "codeops/features/$slug/plans/$name"
done
[[ -f plans/00-roadmap.md ]] && step "git mv plans/00-roadmap.md" git mv plans/00-roadmap.md "codeops/features/$slug/00-roadmap.md"
if [[ -d plans/_archive ]]; then
  for a in plans/_archive/*/; do
    [[ -d "$a" ]] || continue
    aname="$(basename "$a")"
    step "git mv plans/_archive/$aname" git mv "plans/_archive/$aname" "codeops/_archive/$aname"
  done
  for af in plans/_archive/*; do
    [[ -f "$af" ]] || continue
    step "git mv $af" git mv "$af" "codeops/_archive/$(basename "$af")"
  done
fi
# Remove the now-empty flat directories left behind by the moves.
find plans requirements -type d -empty -delete 2>/dev/null || true

# Marker — written LAST, and only after every move step succeeded, so neither an interrupted
# nor a FAILED run can leave a false "already migrated" flag.
# integrationBranch names where features integrate and derived files (portfolio roadmap, CLAUDE.md)
# regenerate — so parallel feature worktrees don't collide. Resolve the repo default: origin/HEAD,
# else the current branch, else main. Consumers auto-detect the same default when the key is absent.
integration_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##')"
[[ -n "$integration_branch" ]] || integration_branch="$(git symbolic-ref --quiet --short HEAD 2>/dev/null)"
[[ -n "$integration_branch" ]] || integration_branch="main"
cat > codeops/codeops.json <<'JSON' || fail_apply "write codeops/codeops.json"
{
  "schema": 1,
  "mode": "strict",
  "artifacts": {"layout": "nested", "root": "codeops"},
  "quality": {
    "independentReview": true,
    "minimumReviewers": 1,
    "stopOnMajorFinding": true
  },
  "metrics": {"enabled": false}
}
JSON
cat > codeops/.codeops.yml <<YML || fail_apply "write codeops/.codeops.yml"
# CodeOps layout marker. Presence of this file opts the repo into the nested layout.
# Sole writer: the setup_codeops skill (via codeops-migrate.sh). Schema: _shared/layout-convention.md
codeopsLayout: nested
layoutVersion: "3.0.0"
integrationBranch: ${integration_branch}
conventions:
  rdIdScope: per-feature
  taskIdPrefix: "T"
  maintenanceFeature: _maintenance
  archiveDir: codeops/_archive
YML

# Seeded portfolio roadmap — one row for the migrated feature. The roadmap skill refines the
# stage/progress on the next /update_roadmap; this is a valid starting point.
today="$(date '+%Y-%m-%d')"
cat > codeops/00-roadmap.md <<PORTFOLIO || fail_apply "write codeops/00-roadmap.md"
# Portfolio Roadmap: $(basename "$ROOT")

> **Status**: Active
> **Last Updated**: $today
> **Features**: 0 / 1 done
> **CodeOps Skills Version**: 3.12.0

## Legend

⬜ Backlog · 🔄 In progress · ✅ Done · ⛔ Blocked · ⏸️ Deferred · 📦 Archived

## Features

| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |
|---------|---------|---------------|----------|--------|--------------|
| $slug | [→](features/$slug/00-roadmap.md) | migrated from flat layout | — | 🔄 | $today |

## Archived

| Feature | Roadmap | Completed | Last Updated |
|---------|---------|-----------|--------------|
| — | — | — | — |
PORTFOLIO

printf '\ncodeops-migrate: applied. Review with "git status" / "git diff --staged" and commit.\n'
printf '  %d warning(s) above may need a manual follow-up (e.g. source-relative links).\n' "${#warnings[@]}"
exit 0
