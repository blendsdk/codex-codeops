# Scope control

Planning, preflight, and execution use strict scope by default. They may identify corrections
required for the requested behavior to be correct, safe, or feasible, but they do not turn optional
adjacent ideas into work.

## Explore optional additions

Use `--explore-scope` with `make-plan`, `preflight`, or `exec-plan` when you explicitly want optional
product additions proposed:

```text
Use preflight --explore-scope on the checkout requirements.
```

Each proposal receives a stable `SE-*` identifier and waits for one of three user decisions:

| Decision | Effect |
|---|---|
| `Keep` | Adds the proposal to confirmed scope and permits derived work |
| `Defer` | Preserves the idea as non-executable context |
| `Discard` | Records that the proposal must not enter the active scope |

Neither `--auto-design` nor acceptance of an audit finding can choose `Keep`. Scope expansion and
technical design are intentionally separate authority decisions.
