# `exec-plan`

Use `exec-plan` to implement a finished CodeOps execution plan. It finds the next incomplete task,
establishes specification tests before production code, updates progress before verification, runs
the required checks, and applies the repository's quality loop.

```text
Use exec-plan for invoice-reconciliation.
```

## Commit modes

| Flag | Behavior |
|---|---|
| *(none)* or `--ask-commit` | Ask after each verified task |
| `--no-commit` | Never commit and never ask |
| `--auto-commit` | Commit and push each verified task through `git-commit` |

```text
Use exec-plan invoice-reconciliation --auto-commit.
```

`--auto-design` and `--explore-scope` may also be used. Auto-design can resolve eligible technical
findings but does not imply commit permission; choose the commit mode separately.

## Safety properties

- The plan is updated immediately when implementation state changes, before verification.
- Specification tests derive from requirements independently of the implementation.
- Critical and major review findings pause normal execution.
- Scope discoveries return to their authoritative artifact instead of becoming hidden assumptions.
- Pushes are normal, never forced; conflicts stop execution.

See [Execute a plan safely](/tutorials/execute-plan) for a complete example.
