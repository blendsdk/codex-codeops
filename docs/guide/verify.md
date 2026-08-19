# Verify installation

After installing or updating CodeOps, start a new Codex thread. Plugin discovery and session hooks
run when the thread starts.

## Confirm the plugin

```bash
codex plugin list
```

The output should show `codeops@codeops-marketplace` as installed and enabled.

## Trust the hooks

Open `/hooks` in Codex. Inspect the CodeOps `SessionStart` and edit-warning hook definitions before
approving them. Codex asks again when a hook definition changes.

The session-start hook supplies the coding and output standards. The edit-warning hook protects the
CodeOps layout marker from accidental modification; it is a guardrail, not a security boundary.

## Confirm skill discovery

In a new thread, ask:

```text
Show the installed CodeOps skills and explain when I should use setup-codeops.
```

Codex should identify the namespaced CodeOps skills. If it does not, follow
[troubleshooting](/troubleshooting).

## Safe first exercise

From a clean Git repository, ask:

```text
Use setup-codeops --dry-run to preview the CodeOps layout for this repository.
Do not write any files.
```

This confirms skill execution and repository inspection without changing the project.
