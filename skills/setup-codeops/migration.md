# Flat → Nested Migration (UX)

> Read this when `setup-codeops` detects an existing **flat layout** (a `requirements/` dir, a
> `plans/00-roadmap.md`, or any `plans/<dir>/`). Resolve paths via
> [_shared/layout-convention.md](../../_shared/layout-convention.md).

## Division of labour (PF-003 — do not blur this)

- **`scripts/codeops-migrate.sh`** owns the *algorithm*: slug derivation + sanitization, the move
  map, the hazard scan, the dirty-tree refusal, the path-traversal slug guard, idempotency, and
  the `git mv` apply. It is deterministic and unit-tested (`scripts/migration-check.sh`).
- **This skill** owns the *UX*: run the engine in dry-run, render its preview, take **one**
  confirmation, then invoke the engine to apply, and report the result. **Never re-implement the
  path arithmetic in prose** — read the move map from the engine and present it.

## Flow

1. **Preview.** Run:
   ```
   scripts/codeops-migrate.sh --dry-run
   ```
   The engine prints the `SLUG:` line (with its source), the `MOVE`/`CREATE` map, and any `WARN`
   lines. If it exits non-zero, surface its message and stop:
   - *not a git repo* → suggest `git init`.
   - *dirty working tree* → ask the user to commit or stash first, then re-run.
   - *already migrated* (marker present) → report the no-op; nothing to do.

2. **Render the preview** to the user, faithfully reflecting the engine output: the feature slug
   and where it came from (roadmap header vs. repo/dir name), a count and summary of the moves,
   the created control files (`codeops/codeops.json`, `codeops/.codeops.yml`, and
   `codeops/00-roadmap.md`), and every warning.

3. **Confirm (once).** Ask a single yes/no: apply this migration with `git mv`? Skip this prompt
   only when the user passed `--yes`.

4. **Apply.** On confirmation, run:
   ```
   scripts/codeops-migrate.sh --yes
   ```
   The engine `git mv`s every mapping (history preserved; intra-`codeops` relative links stay
   valid because the whole tree shifts by one prefix) and writes the marker + seeded portfolio
   roadmap **last**.

5. **Report.** Summarize what moved and restate the warnings as **manual follow-ups** — most
   importantly any **source-relative links** (e.g. a plan doc linking into `src/`), which the
   engine surfaces but never rewrites. Remind the user to review `git status` / `git diff
   --staged` and commit (the migration is staged as one reviewable change).

## Preview shape (illustrative)

```
setup-codeops — migration preview (flat → nested)
  Feature slug:  billing-platform   (source: roadmap header "Billing Platform")
  Move:          requirements/, plans/invoicing/, plans/legacy/, plans/00-roadmap.md,
                 plans/_archive/billing-v1/
  Create:        codeops/.codeops.yml, codeops/00-roadmap.md (portfolio, 1 feature)
  ⚠ Warnings:
    - plans/legacy/ is on disk but not in the roadmap (still migrated)
    - plans/legacy/03-old.md links ../../src/pay.ts (source-relative; verify after move)
  Apply with git mv? [y/N]
```

## Edge cases (all handled by the engine — surface, don't re-derive)

| Case | Engine behaviour | What you tell the user |
|------|------------------|------------------------|
| No roadmap to read the slug from | Falls back to the repo/dir name, states the source | "Slug taken from the directory name; rename later if you want a different feature name." |
| Plans on disk not in the roadmap | Migrated under the feature **and** listed as a warning | List them so the user knows they were included. |
| Loose file directly under `plans/` (not `00-roadmap.md`, not in a plan dir) | Left in place **and** warned (`loose-file-not-migrated`) — no feature target to guess | Tell the user to move it by hand; it is not auto-relocated. |
| Relative link into source | Surfaced as a warning, never rewritten | Flag each for manual fixing after the move. |
| Dirty working tree | Refuses (non-zero), no changes | Ask to commit/stash, then re-run. |
| Re-run after migration | No-op (marker present) | Report "already migrated". |
| Hostile/odd Feature-Set header | Slug sanitized to a safe path component | Show the resulting slug; it can never escape `codeops/features/`. |
