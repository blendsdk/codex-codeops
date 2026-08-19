# `make-plan`

Use `make-plan` after the relevant requirements and product boundaries are known. It studies the
actual repository, closes planning ambiguities, and produces the specifications, testing strategy,
and task-by-task execution plan that `exec-plan` consumes.

```text
Use make-plan for the invoice-reconciliation feature.
```

## Shared controls

```text
Use make-plan --auto-design for invoice-reconciliation.
Use make-plan --explore-scope for invoice-reconciliation.
```

`--auto-design` resolves eligible technical choices with recorded evidence. `--explore-scope`
proposes optional additions for explicit `Keep`, `Defer`, or `Discard` decisions. Neither flag
grants implementation or commit authority.

## Outputs and gate

A full plan includes current-state analysis, component specifications, architecture decisions,
testing strategy, an ambiguity register, and `99-execution-plan.md`. Small isolated tasks may use a
mini-plan, but they retain the same scope, documentation, verification, and progress guarantees.

The plan is complete only when every material choice is resolved or explicitly deferred with risk,
the scope is exact, and every task has a concrete verification command.
