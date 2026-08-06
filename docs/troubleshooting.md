# Troubleshooting

## Plugin is not listed

Run `codex plugin marketplace list` and confirm `codeops-marketplace` resolves. Refresh it with `codex plugin marketplace upgrade codeops-marketplace`, then inspect `codex plugin list`.

## Skills do not appear

Start a new Codex thread after installation or update. Confirm the installed cache contains `skills/*/SKILL.md` and that the plugin is enabled.

## Standards hook did not run

Open `/hooks`. Non-managed plugin hooks are skipped until their exact definitions are reviewed and trusted. A hook change invalidates its prior trust hash.

## Readiness says no traceability graph exists

Run `setup-codeops`, then create or migrate a feature and its `traceability.json`. A newly scaffolded empty portfolio is configured but cannot be implementation-ready.

## A sibling blocks or advances unexpectedly

Confirm the command includes both `--target` and `--gate`. The reported closure may name sibling
or upstream context, but only the selected target may transition. Roadmap sync repairs derived
rows; it must not mutate authoritative graph state.

## Upgrade or transition requires recovery

Do not delete the journal, backup, or lock metadata. Create a recovery request with the recorded
operation ID and an explicit `roll-forward` or `rollback` action, then run:

```powershell
$python = & "$env:PLUGIN_ROOT\scripts\codeops-windows-preflight.ps1" -ResolvePython
& $python "$env:PLUGIN_ROOT\scripts\codeops_state.py" transition-recover --root . `
  --request recovery-request.json
```

Inspect the durable images before choosing the action. A second apply is safe only after recovery
completes.

## Generated agents are missing or stale

```powershell
$python = & "$env:PLUGIN_ROOT\scripts\codeops-windows-preflight.ps1" -ResolvePython
& $python "$env:PLUGIN_ROOT\scripts\install_agents.py" --project . --check
```

Re-run `setup-routing` to preview and regenerate selected marked agents. Hand-authored TOML agents are preserved.

## Migration refuses to run

Migration requires a Git repository and clean working tree because recoverability depends on Git history. Commit or stash unrelated work, review the dry-run again, then apply.

## Native Windows pre-certification fails

Run the native verifier from a PowerShell session in a fixed local NTFS checkout:

```powershell
& .\scripts\codeops-verify.ps1 all
```

Use neither WSL nor Git Bash. If the bootstrap cannot resolve Python, install Python 3.10 or newer
and make `py -3` or `python` available. A successful developer run is useful diagnostic evidence,
but Windows remains unsupported until the retained CI, CLI, and desktop certification records for
the exact release candidate pass validation.
