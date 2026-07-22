# Fresh Scaffold

> Read this when `setup-codeops` detects **neither** a marker nor a flat layout — a repo with no
> CodeOps artifacts yet. Resolve paths via [_shared/layout-convention.md](../../_shared/layout-convention.md).

## What to create

Create **exactly** this minimal skeleton — nothing more (FR-6, AR #12):

```
codeops/
├── .codeops.yml          # the layout marker (schema below)
├── 00-roadmap.md         # empty portfolio roadmap (0 features)
└── features/             # empty; per-feature dirs are created LAZILY on first RD/plan/task
```

Do **not** create `_maintenance/`, any `features/<name>/`, or any requirements/plans dirs up
front. Those appear lazily when the first RD, plan, or task is authored (AR #5).

## Steps

1. Confirm the repo is a git repo (suggest `git init` if not).
2. Create `codeops/features/` (the empty features dir).
3. Write `codeops/.codeops.yml` (the marker — `setup-codeops` is its sole writer).
4. Write `codeops/00-roadmap.md` (empty portfolio — see the portfolio template in the `roadmap`
   skill; seed it with zero features and an empty Archived section).
5. Report what was created and what to do next (`make-requirements` / `make-plan` for the first
   feature; the feature folder is created lazily then).

## `codeops/.codeops.yml` (write verbatim)

```yaml
# CodeOps layout marker. Presence of this file opts the repo into the nested layout.
# Sole writer: the setup-codeops skill. Schema: _shared/layout-convention.md
codeopsLayout: nested
layoutVersion: "3.0.0"
integrationBranch: <the repo's integration branch — resolve; see the note below>
conventions:
  rdIdScope: per-feature
  taskIdPrefix: "T"
  maintenanceFeature: _maintenance
  archiveDir: codeops/_archive
```

Resolve `integrationBranch` to the repo's default branch — `git symbolic-ref refs/remotes/origin/HEAD`
(strip `origin/`), else the current branch, else `main`/`master`. It names the branch where features
integrate and derived files (the portfolio roadmap, `AGENTS.md`) are regenerated, so parallel feature
worktrees don't collide on them. The key is **optional** — every consumer auto-detects the same
default when it is absent — so this line is a convenience/pin, not a requirement.

## Notes

- The marker is what flips the repo into nested layout — write it **last** so a half-finished
  scaffold never looks "set up".
- Scaffolding is intentionally simple, so it lives in skill prose; only the *migration* path
  needs the deterministic engine. For migration, see [migration.md](migration.md).
