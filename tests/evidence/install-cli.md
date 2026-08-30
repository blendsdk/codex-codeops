# Codex plugin release evidence

- Captured: 2026-08-30
- Host: Linux
- Codex CLI: `0.151.0`
- Plugin: `codeops@codeops-marketplace`, version `1.1.0`
- Evidence state: observed installation from the published GitHub marketplace
- Repository source: release tag `v1.1.0`
- Installed source commit: `5803db4`

Before the release commit, the exact working tree passed:

1. `python scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

After the release commit was public:

1. `codex plugin marketplace upgrade codeops-marketplace` completed successfully.
2. `codex plugin add codeops@codeops-marketplace` installed the plugin at version `1.1.0`.
3. `codex plugin list` reported `codeops@codeops-marketplace` as installed and enabled at `1.1.0`.
4. Plugin validation passed against the installed cache, and its progress command rendered the
   governing plan as `Progress: [█████████░] 60/61 tasks (98%)`.
