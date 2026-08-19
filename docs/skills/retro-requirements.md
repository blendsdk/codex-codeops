# `retro-requirements`

Use `retro-requirements` when an existing implementation is the primary evidence for what a system
does. It extracts observable behavior, contracts, data, integrations, security, operations, and
failure handling without mistaking implementation details for product requirements.

```text
Use retro-requirements to reconstruct this service's behavior.
```

## Controls

```text
Use retro-requirements --scope packages/billing.
Use retro-requirements --continue.
```

`--scope` limits archaeology to one module or package. `--continue` resumes the matching persisted
analysis.

## Confidence and triage

Every recovered behavior is classified by evidence confidence. Before requirements are finalized,
the bug-or-feature gate forces observed anomalies to be classified as intended behavior, defects,
or unresolved questions. A bug is never documented as a feature merely because the code currently
does it.

The reconstruction brief feeds `make-requirements`; it is evidence, not an automatically approved
requirements set.
