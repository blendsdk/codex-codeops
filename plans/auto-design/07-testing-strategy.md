# Testing Strategy: Auto Design

> **Document**: 07-testing-strategy.md
> **Parent**: [Index](00-index.md)

## Specification Test Cases

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-1 | Run each supported skill without `--auto-design` | Existing explicit-user-decision contract remains present and active | R1; AR-9 |
| ST-2 | Run a supported skill with `--auto-design` | It activates the shared policy and excludes the flag from target/path resolution | R1; AR-4 |
| ST-3 | Eligible compiler architecture ambiguity | CodeOps selects one option using the complete quality rubric and durable provenance | R2–R3; AR-1–AR-3, AR-8 |
| ST-4 | Product-priority, legal, spending, deployment, or destructive choice | CodeOps escalates and does not claim delegated authority | R4; AR-5–AR-6 |
| ST-5 | Auto-design combined with default exec commit mode | Commit behavior remains ask-commit; no permission is inferred | R4; AR-5 |
| ST-6 | Material evidence remains unavailable after research/challenge | One bounded escalation replaces guessing or endless iteration | R4; AR-10 |
| ST-7 | Later implementation evidence invalidates an automatic decision | Owning AR reopens, downstream state becomes stale, and gates rerun | R3, R5; AR-11 |
| ST-8 | Nested supported workflow is explicitly invoked from an active chain | Mode propagates for that chain but is not persisted globally | R6; AR-9 |
| ST-9 | Auto-design decision record is inspected | Authority, objective, evidence, alternatives, counterargument, confidence, and reopen triggers exist | R3; AR-7–AR-8 |
| ST-10 | Full repository verification | All five required commands pass | AC5 |

## Test Files

- `tests/conformance/test_auto_design_spec.py`: ST-1–ST-9 policy and integration contracts.
- `tests/conformance/test_auto_design_impl.py`: hostile argument, permission-coupling, link, and
  drift checks.

Specification tests are written before policy and skill integration, confirmed red, then held
immutable. Implementation tests follow the implementation.
