# `grill-me`

Use `grill-me` to eliminate ambiguity before requirements or planning begins. It maps the major
decision branches, resolves dependencies first, and walks one material decision at a time until the
design has explicit constraints, assumptions, risks, and exclusions.

```text
Use grill-me to interrogate my design for a multi-tenant approval service.
```

## What happens

1. Codex maps a design tree for behavior, data, interfaces, security, operations, and constraints.
2. Each branch is expanded until its consequential leaves are concrete.
3. Cross-branch dependencies are reconciled.
4. Codex presents a shared-understanding summary for confirmation.

Long interviews persist progress in a topic-specific notes file. Resume the matching session with:

```text
Use grill-me --continue.
```

Completion means zero material ambiguity remains; it does not create requirements or an
implementation plan. Follow with `make-requirements` or `make-plan` as appropriate.
