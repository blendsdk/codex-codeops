# Execute a plan safely

This tutorial assumes `make-plan` produced a complete `99-execution-plan.md` and preflight has no
unresolved critical or major findings.

## 1. Choose authority deliberately

Commit behavior and technical-decision authority are separate:

| Desired behavior | Invocation |
|---|---|
| Ask before each commit | `Use exec-plan for FEATURE.` |
| Never commit | `Use exec-plan FEATURE --no-commit.` |
| Commit and push verified tasks | `Use exec-plan FEATURE --auto-commit.` |
| Delegate eligible technical decisions | Add `--auto-design` separately |

For autonomous verified checkpoints:

```text
Use exec-plan for invoice-reconciliation with --auto-design and --auto-commit.
```

This does not authorize deployment, credentials, destructive operations, product-scope choices, or
risk acceptance.

## 2. Watch task state

Execution uses four task markers:

| Marker | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | Implemented; verification pending |
| `[x]` | Verification passed |
| `[!]` | Blocked, with a visible reason |

The executor writes `[~]` before verification. A failure therefore leaves honest resumable state
instead of an apparently untouched task. Only a passing verification permits `[x]`.

## 3. Preserve the specification oracle

Specification tests come from requirements and acceptance criteria before production changes.
Implementation tests may then cover internal edge cases. If a specification test fails after the
implementation changes, fix the implementation or reopen the authoritative requirement—do not
weaken the oracle to match the code.

## 4. Handle discoveries upstream

When implementation reveals an undefined contract, stop the affected task, record the ambiguity in
the governing artifact, update dependent specifications and plan steps, and rerun the affected
gate. Do not bury the choice in a code comment or local workaround.

## 5. Resume

A later invocation resumes the first `[~]` task, otherwise the first `[ ]` task. Inspect the Git
diff and plan state before continuing so external changes cannot be mistaken for verified work.
