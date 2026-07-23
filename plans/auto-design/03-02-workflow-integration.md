# Workflow Integration: Auto Design

> **Document**: 03-02-workflow-integration.md
> **Parent**: [Index](00-index.md)

## Shared invocation contract

Each supported skill parses `--auto-design` as an option, removes it from artifact/path arguments,
announces activation, reads `_shared/auto-design.md`, and carries the mode into nested lifecycle
handoffs. Without the token, existing user-decision rules remain exact. (AR-4, AR-9)

## Workflow behavior

| Workflow | Auto-design behavior |
|---|---|
| make-requirements | Resolve eligible technical requirement ambiguities; escalate product policy |
| make-plan | Resolve eligible architecture/design ARs before opening the gate |
| preflight | Choose and, when already authorized to fix, apply the strongest eligible remediation |
| exec-plan | Resolve runtime technical ambiguities, update upstream artifacts/state, and re-gate |

Preflight remains review-only unless the user also authorized fixes. Exec-plan commit modes remain
independent. No workflow treats design delegation as file, Git, deployment, or external-action
permission. (AR-5)

## Failure handling

Conflicting governing constraints, unavailable material evidence, low confidence after bounded
research/challenge, or reserved authority produce one focused escalation containing the decision,
why CodeOps cannot safely own it, the strongest recommendation available, and the minimum user
input required. The workflow does not fall back to arbitrary guessing. (AR-10)
