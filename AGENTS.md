# CodeOps for Codex

## Purpose

This repository develops the installable CodeOps plugin for Codex. CodeOps is a recursive specification-first workflow for complex systems: discover requirements, close material ambiguities, specify and plan, close plan ambiguities, prove readiness, execute, verify, review, and track durable project state.

## Repository rules

- Treat `plans/codex-port/` as the governing port program until the 1.0 gate passes.
- Preserve the Claude implementation at `../codeops`; read it as a behavioral oracle but never edit it from this repository.
- One fact has one authoritative owner. Reference it elsewhere instead of restating it.
- Do not weaken recursive ambiguity gates, specification-test independence, update-before-verify state, or project tracking.
- Use Codex-native names and paths in shipped files: `AGENTS.md`, `.codex/`, `PLUGIN_ROOT`, and `PLUGIN_DATA`.
- Keep host integration isolated from reusable workflow content.
- Use `apply_patch` for hand-authored edits. Mechanical imports and formatting may use deterministic bulk tools.
- Commit and push coherent, verified phases to `main`.

## Verification

Run:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

The validation entry point must remain deterministic and safe to run from the repository root.
