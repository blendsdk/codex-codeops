# Workflow Integration: Dependency-Aware Readiness

> **Document**: 03-04-workflow-integration.md
> **Parent**: [Index](00-index.md)

## Overview

Lifecycle skills identify the artifact being advanced and invoke the deterministic engine with the
matching canonical target and gate. They use closure artifacts as context but do not silently
expand the authorized modification set. (AR-1, AR-4, AR-10, AR-12)

## Workflow Mapping

| Workflow | Target and gate |
|---|---|
| make-requirements | Selected RD or explicit requirement-set target with `requirements` |
| specification completion | Selected requirement/specification/group with `specifications` |
| preflight | Exact graph-owned artifact with `audit`; graphless ad-hoc artifacts receive semantic audit only |
| make-plan | Selected RD/task/group with `plan` |
| exec-plan entry | Selected plan with `execution` |
| exec-plan task completion | Selected task with `task-complete` |
| roadmap | Per-target `status` rollup; siblings never advance implicitly |
| feature acceptance | Explicit feature aggregate with `feature-acceptance` |
| release | Explicit release node with `release` |
| upgrade-plan | Schema inspection, preview, resolution, apply, validate |

Skills obtain target identity from traceability, never from directory guesses. Context discovered
through closure may be read. Any semantic modification outside the declared target/modification
set requires explicit user approval. (AR-5, AR-10, AR-12)

## Rollout Order

1. Land schema-2 validation and target engine behind explicit schema/gate arguments.
2. Land upgrade preview/apply support and documentation.
3. Update artifact creation templates and references to emit schema 2.
4. Update make-requirements, specification completion, preflight, make-plan, and exec-plan.
5. Update roadmap aggregation, feature acceptance, and release guidance.
6. Retain schema-1 paths until a separately approved removal policy exists. (AR-9, AR-12)

Schema-1 characterization is the first specification-test task before step 1 and runs unchanged
after every phase. (AR-22)

## Roadmap Semantics

Roadmaps derive per-target states and aggregate them. Advancing RD-01 cannot change RD-02. Feature
and portfolio rows summarize children without becoming authoritative state. A release row reports
only declared release membership. (AR-1, AR-10, AR-11)

## Documentation

Update traceability reference, concepts, tutorial, migration guide, and troubleshooting with:

- target and gate selection;
- relation authoring and derived inverse views;
- contract maturity and planning groups;
- closure and diagnostic interpretation;
- schema-1 compatibility and schema-2 upgrade;
- explicit feature/release aggregation.

## Governing Port Program

This plan is corrective work discovered through the real complex-project pilot owned by
`plans/codex-port/99-execution-plan.md` task 6.8. Completion of this plan does not itself complete
6.8. Final closeout must retain the triggering evidence, rerun the affected milestone using the
new target-scoped gates, record the result, and only then update 6.8 and the governing progress
counter. A failed rerun leaves 6.8 open. (AR-26)

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Skill cannot resolve exact target | Ask; never guess or broaden to feature | AR-5, AR-12 |
| Closure exposes upstream defect | Report owner and request exact modification expansion | AR-10, AR-12 |
| Narrow preflight sees sibling issue | Record contextual finding without modifying sibling | AR-10, AR-12 |
| Roadmap conflicts with graph | Repair derived view; do not mutate authoritative state silently | AR-12 |

## Testing Requirements

Normative ownership is defined only by the ST ownership table in `07-testing-strategy.md` (AR-27).
