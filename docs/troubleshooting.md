# Troubleshooting

## Plugin is not listed

Run `codex plugin marketplace list` and confirm `codeops-marketplace` resolves. Refresh it with `codex plugin marketplace upgrade codeops-marketplace`, then inspect `codex plugin list`.

## Skills do not appear

Start a new Codex thread after installation or update. Confirm the installed cache contains `skills/*/SKILL.md` and that the plugin is enabled.

## Standards hook did not run

Open `/hooks`. Non-managed plugin hooks are skipped until their exact definitions are reviewed and trusted. A hook change invalidates its prior trust hash.

## Readiness says no traceability graph exists

Run `setup-codeops`, then create or migrate a feature and its `traceability.json`. A newly scaffolded empty portfolio is configured but cannot be implementation-ready.

## Generated agents are missing or stale

```bash
python3 /path/to/plugin/scripts/install_agents.py --project . --check
```

Re-run `setup-routing` to preview and regenerate selected marked agents. Hand-authored TOML agents are preserved.

## Migration refuses to run

Migration requires a Git repository and clean working tree because recoverability depends on Git history. Commit or stash unrelated work, review the dry-run again, then apply.
