# Codex plugin release evidence

- Captured: 2026-08-26
- Host: Linux
- Codex CLI: `0.149.1`
- Plugin: `codeops@codeops-marketplace`, version `1.0.1`
- Evidence state: observed installation from the published GitHub marketplace
- Repository source: release tag `v1.0.1`
- Installed source commit: `3b6afa5`

Before the release commit, the exact working tree passed:

1. `python scripts/validate_plugin.py .`
2. `./scripts/validate-codex.sh`
3. `./scripts/docs-check.sh`
4. `./scripts/migration-check.sh`
5. `./scripts/roadmap-sync-check.sh`
6. `./scripts/compact-check.sh`

After the release commit was public:

1. `codex plugin marketplace upgrade codeops-marketplace` completed successfully.
2. `codex plugin add codeops@codeops-marketplace` installed the plugin at version `1.0.1`.
3. `codex plugin list` reported `codeops@codeops-marketplace` as installed and enabled at `1.0.1`.
4. Plugin validation passed against the installed cache, and the installed compact standards and
   planning checklist contained the minimum-sufficient-design contract.
