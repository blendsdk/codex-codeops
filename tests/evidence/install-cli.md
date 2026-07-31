# Codex plugin release evidence

- Captured: 2026-07-31
- Host: Linux
- Codex CLI: `0.146.0`
- Plugin: `codeops@codeops-marketplace`, version `0.4.0`
- Evidence state: pre-publication package validation
- Source state: working tree for planned `v0.4.0`

Before the release commit, the exact working tree passed:

1. `python3 scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

This state is temporary. It must be replaced with observed installation evidence after the release
commit is public and before annotated tag `v0.4.0` is published.
