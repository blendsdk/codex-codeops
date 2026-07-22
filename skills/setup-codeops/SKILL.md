---
name: setup-codeops
description: >-
  Sets up the CodeOps nested codeops/ layout in the current git repo — scaffolds a fresh skeleton or auto-migrates an existing flat-layout repo (requirements/ + plans/) into it. Use when the user says "setup-codeops", "/setup-codeops", "set up codeops", "initialize codeops", "migrate to the nested layout", "convert my plans/requirements to codeops/", or "scaffold the codeops structure". Detects repo state and dispatches: a marker (codeops/.codeops.yml) already present → no-op status report; a flat layout → migration (deterministic preview via scripts/codeops-migrate.sh, one confirmation, then git mv); neither → minimal fresh scaffold. Supports --dry-run (preview only) and --yes (apply without the prompt). Migration is git-mv-only, refuses a dirty tree, rejects path-traversal slugs, and is idempotent. setup-codeops is the SOLE writer of the layout marker.
---

# CodeOps Layout Setup (`setup-codeops`)

> **CodeOps Artifact Schema**: 1

Set up the CodeOps **nested `codeops/` layout** for the git repo the user is currently in. Run as
`/codeops:setup-codeops` or the typeable alias `/setup-codeops`. This is the one skill that
**creates and owns the layout marker** `codeops/.codeops.yml`; every other skill only reads it.

Resolve all paths and the marker schema via **[_shared/layout-convention.md](../../_shared/layout-convention.md)** —
it is the single source of truth for the layout. Do not re-encode paths here.

## Scope

- **Per-repo only.** One git repo at a time; no cross-repo or portfolio-of-projects work.
- This skill sets up the *structure*. It never authors requirements, plans, or roadmaps — that is
  `make-requirements` / `make-plan` / `roadmap`, which then resolve paths via the convention doc.

## Dispatch — detect repo state, then branch

Run inside the repo and detect, in this order:

```
1. codeops/.codeops.yml present
       → already set up. NO-OP for the layout: print a short status report (layout = nested, where
         things live). BUT if the marker is **missing `integrationBranch`**, BACKFILL it — add that
         one line (resolved to the repo's integration branch: `origin/HEAD`, else the current branch,
         else `main`/`master`) without touching any other key; if it is already present, leave it.
         Never re-scaffold or re-migrate. (Idempotent — a marker that is present and complete → no
         change; this is the existing-project entry point for parallel-agents support.)
2. Flat layout detected (requirements/  OR  plans/00-roadmap.md  OR  any plans/<dir>/)
       → MIGRATE. Follow migration.md: run the engine --dry-run, render the preview, take ONE
         confirmation, then apply. The engine (scripts/codeops-migrate.sh) owns the algorithm.
3. Neither
       → fresh SCAFFOLD. Follow scaffold.md: create the minimal codeops/ skeleton.
```

If the repo is **not a git repo**, refuse with a clear message (migration needs `git mv`; even a
fresh scaffold should live in version control) and suggest `git init` first.

## Flags

| Flag | Effect |
|------|--------|
| *(none)* | Interactive: scaffold creates the skeleton; migration previews then asks for one confirmation before applying. |
| `--dry-run` | Preview only — compute and show what would happen; change **nothing**. For migration, pass straight through to the engine. |
| `--yes` | Apply without the confirmation prompt (unattended). For migration, the engine applies directly. |

## The migration engine (delegation — do not re-implement)

All migration path arithmetic, the slug derivation, the hazard scan, the dirty-tree refusal, the
path-traversal slug guard, idempotency, and the `git mv` apply live in the deterministic helper
**`scripts/codeops-migrate.sh`** (see [migration.md](migration.md)). This skill **delegates** to it
so there is one source of truth and no prose-vs-script drift:

- Preview: `scripts/codeops-migrate.sh --dry-run`
- Apply:   `scripts/codeops-migrate.sh --yes`

Never re-derive the move map in prose — read it from the engine's output and present it.

## Reference files

- [scaffold.md](scaffold.md) — the minimal fresh-repo skeleton.
- [migration.md](migration.md) — the flat→nested migration UX (invoke the engine, preview, confirm, report).
- [_shared/layout-convention.md](../../_shared/layout-convention.md) — the layout/path/ID/marker source of truth.

## Grounded Options & Recommendations

When a migration surfaces choices (e.g. an ambiguous slug source, or warnings the user must act
on), present only **genuinely viable** options, second-guessed and grounded in what the engine
actually reported, and lead with a recommendation. The user decides; never apply a migration
without an explicit confirmation (or `--yes`). For consequential choices, apply the
recommendation-hardening protocol (`_shared/recommendation-hardening.md`).
