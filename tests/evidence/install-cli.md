# Codex plugin release evidence

- Captured: 2026-08-26
- Host: Linux
- Codex CLI: `0.149.1`
- Plugin: `codeops@codeops-marketplace`, version `1.0.1`
- Evidence state: pre-publication package validation
- Source state: working tree for planned `v1.0.1`

Before the release commit, the exact working tree passed:

1. `python scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

This state is temporary. Replace it with observed installation evidence after the release commit is
public and before publishing annotated tag `v1.0.1`.
