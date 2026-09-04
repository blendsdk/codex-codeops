# Codex plugin release evidence

- Captured: 2026-09-04
- Host: Linux
- Codex CLI: `0.153.2`
- Plugin: `codeops@codeops-marketplace`, version `1.2.0`
- Evidence state: pre-publication package validation
- Source state: working tree for planned `v1.2.0`

The exact working tree passed:

1. `python scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

Published-install evidence will replace this pre-publication state after the release commit and tag
are available from the marketplace.
