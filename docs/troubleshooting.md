# Troubleshooting

## Plugin is not listed

Run `codex plugin marketplace list` and confirm `codeops-marketplace` resolves. Refresh it with `codex plugin marketplace upgrade codeops-marketplace`, then inspect `codex plugin list`.

## Skills do not appear

Start a new Codex thread after installation or update. Confirm the installed cache contains `skills/*/SKILL.md` and that the plugin is enabled.

## Standards hook did not run

Open `/hooks`. Non-managed plugin hooks are skipped until their exact definitions are reviewed and trusted. A hook change invalidates its prior trust hash.

## Plan status reports missing metadata

Confirm the plan contains `00-index.md`, `99-execution-plan.md`, and one
`> **Implements**:` line with at least one RD identifier. An empty portfolio is configured but has
no plan status to report.

## A sibling blocks or advances unexpectedly

Confirm each plan declares only the RDs it implements and each task appears once in its execution
plan. Roadmap sync repairs derived rows; it must not mutate requirements or task checkboxes.

## A task is stuck after interruption

Read `99-execution-plan.md`. Resume the first `[~]` task and re-run its verification; otherwise
start the first `[ ]` task. For `[!]`, resolve the visible blocker before restoring the appropriate
task marker. Use Git history to inspect or recover interrupted edits.

## Generated agents are missing or stale

```bash
python3 /path/to/plugin/scripts/install_agents.py --project . --check
```

Re-run `setup-routing` to preview and regenerate selected marked agents. Hand-authored TOML agents are preserved.

## Migration refuses to run

Migration requires a Git repository and clean working tree because recoverability depends on Git history. Commit or stash unrelated work, review the dry-run again, then apply.
