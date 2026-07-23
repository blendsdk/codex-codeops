# Traceability contract

CodeOps stores one `traceability.json` in each feature directory. It is an index over authoritative Markdown artifacts and implementation evidence, not a replacement for them.

## Required chain

For every behavior delivered by a feature, the graph must establish:

```text
requirement
  → specification or invariant
  → acceptance criterion
  → specification test
  → execution task
  → implementation evidence
  → verification evidence
```

Decisions and resolved ambiguities link to every downstream node they affect. Findings link to the reviewed task, implementation, or verification node. Approved deferrals record their risk and link to the affected nodes.

## Status vocabulary

| Type | Expected statuses |
|---|---|
| ambiguity | `open`, `resolved`, `deferred-approved` |
| deferral | `proposed`, `approved`, `expired`, `resolved` |
| requirement/specification/criterion/invariant | `draft`, `approved`, `stale`, `superseded` |
| test | `planned`, `red-confirmed`, `passing`, `blocked`, `stale` |
| task | `pending`, `implemented`, `verified`, `blocked`, `stale` |
| implementation | `present`, `stale`, `superseded`, `reverted` |
| verification | `passing`, `failing`, `stale` |
| finding | `open`, `accepted`, `resolved` |

The validator rejects unknown structure and broken links. Readiness additionally requires zero open material ambiguities, zero unapproved deferrals, zero critical/major open findings, and complete forward coverage for the active gate.

When a high- or critical-risk ambiguity reopens, every linked downstream
requirement, specification, invariant, criterion, test, task, implementation,
and verification must be marked `stale` (or returned to another non-approved
work state). Readiness reports both the reopened ambiguity and any downstream
artifact that still falsely claims completion.

## One owner per fact

The graph stores identity, state, and relationships. Markdown owns semantic content. Generated roadmaps own neither: they summarize the graph and on-disk execution state.
