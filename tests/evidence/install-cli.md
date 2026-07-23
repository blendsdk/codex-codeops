# Codex plugin release evidence

- Captured: 2026-07-23
- Host: Linux
- Codex CLI: `0.145.0`
- Plugin: `codeops@codeops-marketplace`, version `0.3.0`
- Evidence state: pre-publication package validation
- Source state: working tree for planned `v0.3.0`

Before the release commit, the exact working tree passed:

1. `python3 scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh` except for the release-evidence group that this record closes.
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

This pre-publication state is temporary. Task 3.1.4 remains open until the commit is pushed,
the public marketplace installs 0.3.0, this file is replaced with observed CLI lifecycle evidence,
all gates pass again, and annotated tag `v0.3.0` is created.
