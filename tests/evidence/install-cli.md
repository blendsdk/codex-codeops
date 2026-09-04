# Codex plugin release evidence

- Captured: 2026-09-04
- Host: Linux
- Codex CLI: `0.153.2`
- Plugin: `codeops@codeops-marketplace`, version `1.2.0`
- Evidence state: observed installation from the published GitHub marketplace
- Repository source: release tag `v1.2.0`
- Installed source commit: `9b1dd8c`

Before the release commit, the exact working tree passed:

1. `python scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

After the release commit was public:

1. `codex plugin marketplace upgrade codeops-marketplace` completed successfully.
2. `codex plugin add codeops@codeops-marketplace` installed the plugin at version `1.2.0`.
3. `codex plugin list` reported `codeops@codeops-marketplace` as installed and enabled at `1.2.0`.
4. Plugin validation passed against the installed cache.
5. The installed cache contained the visible complexity stop packet and the plain international
   English response policy.
6. The annotated tag and public GitHub release both resolve to release commit `9b1dd8c`.
