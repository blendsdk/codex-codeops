#!/usr/bin/env bash
#
# docs-check.sh — specification-test suite for the docs website (plans/docs-website).
#
# Each check maps to a spec test case (ST-n) in plans/docs-website/07-testing-strategy.md.
# It asserts the STRUCTURE of the VitePress docs site, its config, the gitignore entries, and
# the deploy workflow — independently of the page prose. It never executes repo data as code;
# it only reads and pattern-matches files (mirrors scripts/validate.sh's policy).
#
# Usage:  ./scripts/docs-check.sh
# Exit:   0 = all checks pass (green); non-zero = at least one check failed (red).

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CONFIG="docs/.vitepress/config.ts"
GITIGNORE=".gitignore"
BASE_PATH="/claude-codeops/"

# The 11 skills that MUST each have a docs page (ST-4).
SKILLS=(make_plan exec_plan make_requirements retro_requirements grill_me preflight techdocs roadmap upgrade_plan setup_routing setup_codeops)
# Required pages per section (ST-4b).
GUIDE_PAGES=(introduction install verify update concepts quality-profile telemetry)
TUTORIAL_PAGES=(index first-plan full-pipeline reverse-engineer)
REFERENCE_PAGES=(standards repo-map agents troubleshooting)
# The five mandatory headings on every skill page (impl check — see 03-02).
SKILL_HEADINGS=("## What it does" "## When to use it" "## Trigger phrases" "## Worked example" "## Related skills")

WORKFLOW=".github/workflows/docs.yml"
# Least-privilege permissions the Pages deploy needs — and nothing more (ST-6).
WORKFLOW_PERMS=("contents: read" "pages: write" "id-token: write")

FAILURES=0

pass() { printf '  \033[32mPASS\033[0m %s\n' "$1"; }
fail() {
  printf '  \033[31mFAIL\033[0m %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}
section() { printf '\n\033[1m%s\033[0m\n' "$1"; }

# file_has <file> <fixed-string> — true if the file exists and contains the literal substring.
file_has() {
  local f="$1" needle="$2"
  [[ -f "$f" ]] && grep -qF -- "$needle" "$f"
}

# -----------------------------------------------------------------------------
# ST-3 — VitePress config sets the GitHub Pages base path
# -----------------------------------------------------------------------------
section "ST-3: VitePress base path is \"$BASE_PATH\""
if [[ -f "$CONFIG" ]]; then
  # Accept single or double quotes around the base value.
  if grep -Eq "base:[[:space:]]*['\"]${BASE_PATH}['\"]" "$CONFIG"; then
    pass "$CONFIG declares base: '$BASE_PATH'"
  else
    fail "$CONFIG does not declare base: '$BASE_PATH'"
  fi
else
  fail "$CONFIG is missing"
fi

# -----------------------------------------------------------------------------
# ST-9 — Node / VitePress build artifacts are git-ignored
# -----------------------------------------------------------------------------
section "ST-9: build artifacts are git-ignored"
for entry in "node_modules/" "docs/.vitepress/dist" "docs/.vitepress/cache"; do
  if file_has "$GITIGNORE" "$entry"; then
    pass "$GITIGNORE ignores $entry"
  else
    fail "$GITIGNORE does not ignore $entry"
  fi
done

# -----------------------------------------------------------------------------
# ST-4 — every skill has a page + a Commands page; each skill page has the 5 headings
# -----------------------------------------------------------------------------
section "ST-4: per-skill pages exist with the required structure"
for s in "${SKILLS[@]}"; do
  page="docs/skills/${s}.md"
  if [[ -f "$page" ]]; then
    missing=""
    for h in "${SKILL_HEADINGS[@]}"; do
      grep -qF -- "$h" "$page" || missing+=" \"$h\""
    done
    if [[ -z "$missing" ]]; then
      pass "$page exists with all 5 sections"
    else
      fail "$page is missing section(s):$missing"
    fi
  else
    fail "$page is missing"
  fi
done
for extra in "docs/skills/index.md" "docs/skills/commands.md"; do
  if [[ -f "$extra" ]]; then
    pass "$extra exists"
  else
    fail "$extra is missing"
  fi
done

# -----------------------------------------------------------------------------
# ST-4b — all Guide, Tutorial, and Reference pages exist
# -----------------------------------------------------------------------------
section "ST-4b: Guide / Tutorial / Reference pages exist"
for g in "${GUIDE_PAGES[@]}"; do
  if [[ -f "docs/guide/${g}.md" ]]; then pass "docs/guide/${g}.md exists"; else fail "docs/guide/${g}.md is missing"; fi
done
for t in "${TUTORIAL_PAGES[@]}"; do
  if [[ -f "docs/tutorials/${t}.md" ]]; then pass "docs/tutorials/${t}.md exists"; else fail "docs/tutorials/${t}.md is missing"; fi
done
for r in "${REFERENCE_PAGES[@]}"; do
  if [[ -f "docs/reference/${r}.md" ]]; then pass "docs/reference/${r}.md exists"; else fail "docs/reference/${r}.md is missing"; fi
done
if [[ -f "docs/index.md" ]]; then pass "docs/index.md (home) exists"; else fail "docs/index.md (home) is missing"; fi

# -----------------------------------------------------------------------------
# ST-6 — deploy workflow exists with least-privilege perms, Node 20, only actions/*,
#        and a Pages concurrency group
# -----------------------------------------------------------------------------
section "ST-6: deploy workflow is well-formed and least-privilege"
if [[ -f "$WORKFLOW" ]]; then
  pass "$WORKFLOW exists"

  for perm in "${WORKFLOW_PERMS[@]}"; do
    if grep -qF -- "$perm" "$WORKFLOW"; then
      pass "permission present: $perm"
    else
      fail "permission missing: $perm"
    fi
  done

  # No blanket write-all permission.
  if grep -Eq 'permissions:[[:space:]]*write-all' "$WORKFLOW"; then
    fail "workflow grants permissions: write-all (must be least-privilege)"
  else
    pass "no blanket write-all permission"
  fi

  # Node 20.
  if grep -Eq 'node-version:[[:space:]]*["'\'']?20' "$WORKFLOW"; then
    pass "pins Node 20"
  else
    fail "does not pin Node 20"
  fi

  # Every `uses:` must reference an official actions/* action (no third-party actions).
  non_official="$(grep -E '^\s*-?\s*uses:' "$WORKFLOW" | grep -vE 'uses:\s*actions/' || true)"
  if [[ -z "$non_official" ]]; then
    pass "all actions are official actions/* "
  else
    fail "non-official action(s) referenced:"$'\n'"$non_official"
  fi

  # Pages concurrency group.
  if grep -Eq 'group:[[:space:]]*pages' "$WORKFLOW"; then
    pass "declares a Pages concurrency group"
  else
    fail "no 'group: pages' concurrency declaration"
  fi
else
  fail "$WORKFLOW is missing"
fi

# =============================================================================
# CodeOps v3-hardening docs checks (plans/codeops-v3-hardening/07-testing-strategy.md)
# Count-claim drift for docs prose is covered by validate.sh ST-32.
# =============================================================================

# -----------------------------------------------------------------------------
# ST-H20 — CHANGES.md is a live changelog: it must carry an entry header for every
# release since 3.0.0 (the changelog froze at the v2 era — v3-hardening AR #21).
# -----------------------------------------------------------------------------
section "ST-H20: CHANGES.md carries 3.0.0 / 3.1.0 / 3.2.0 / 3.3.0 / 3.3.1 / 3.3.2 entries"
for v in "3.0.0" "3.1.0" "3.2.0" "3.3.0" "3.3.1" "3.3.2"; do
  if grep -qE "^#+ .*${v//./\\.}" CHANGES.md 2>/dev/null; then
    pass "CHANGES.md has an entry header for $v"
  else
    fail "CHANGES.md has no entry header for $v (frozen changelog — AR #21)"
  fi
done

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------
section "Summary"
if [[ "$FAILURES" -eq 0 ]]; then
  printf '  \033[32mAll docs checks passed.\033[0m\n'
  exit 0
else
  printf '  \033[31m%d docs check(s) failed.\033[0m\n' "$FAILURES"
  exit 1
fi
