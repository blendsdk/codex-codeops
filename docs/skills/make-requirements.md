# `make-requirements`

Use `make-requirements` to turn a rough idea into formal, numbered requirement documents. The skill
acts as a domain consultant: it expands the seed, applies relevant domain lenses, challenges edge
cases, and closes material ambiguity before finalization.

```text
Use make-requirements for a multi-currency ledger.
```

## Modes

| Request | Behavior |
|---|---|
| `make-requirements` | Full discovery for a new requirement set |
| `make-requirements --continue` | Resume persisted discovery notes |
| “add a requirement” | Add one requirement to an existing set |
| “review requirements” | Audit the health and coverage of an existing set |

Add `--auto-design` to delegate eligible technical choices. Product scope, acceptance behavior,
risk, credentials, and external actions still require the user.

## Outputs

The full workflow produces a requirements index, numbered RDs, and an ambiguity register in the
resolved CodeOps layout. Requirements own what the system must do; later plans reference them
rather than silently redefining them.
