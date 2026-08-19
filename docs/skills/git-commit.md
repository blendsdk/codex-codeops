# `git-commit`

Use `git-commit` to turn a coherent, verified working-tree change into a guarded Conventional
Commit. Ask explicitly for a push when you also want the commit sent to the remote.

```text
Use git-commit to verify and commit these changes.
Use git-commit in push mode for these changes.
```

## Protocol

The skill inspects tracked and untracked files, rejects likely secrets or unrelated output, runs
the repository's authoritative verification command, stages explicit paths, reviews the complete
staged diff, and writes a detailed commit message.

It never bypasses hooks, force-pushes, silently resolves rebase conflicts, or treats commit
permission as push permission. If verification fails, no commit is created. If a hook modifies
files, the changed files are inspected and only relevant changes are restaged before one retry.
