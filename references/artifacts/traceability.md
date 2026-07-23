# Traceability contract

CodeOps schema 2 stores one `traceability.json` in each feature directory. It is an index over authoritative Markdown artifacts and implementation evidence, not a replacement for them.

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

Every workflow resolves a canonical graph target and supplies its matching gate:
`requirements`, `specifications`, `audit`, `plan`, `execution`, `task-complete`,
`feature-acceptance`, or `release`. For example:

```bash
codeops_state.py readiness --root . --gate plan --target billing/RD-03
```

Target closure supplies dependencies and blocker paths as read context; it never authorizes
editing or advancing siblings. Feature and release aggregates are explicit nodes. Schema 2 also
records semantic sources, deterministic revisions, and relationship snapshots so changed
upstream meaning makes downstream state stale. Lifecycle changes use public compare-and-swap
`transition` requests.

An exact transition request is a closed JSON object:

```json
{
  "schema": 1,
  "operationId": "unique-operation-id",
  "target": "feature/RD-01",
  "expected": {"status": "draft", "revision": "sha256:..."},
  "requested": {"status": "approved"},
  "gate": "requirements",
  "sourceUpdates": [],
  "validationAdditions": [],
  "validationRemovals": [],
  "staleReason": null,
  "evidence": {"summary": "durable evidence summary"}
}
```

Submit it with `codeops_state.py transition --root . --request <request.json>`. Use the gate
owned by the target type; the engine validates the projected portfolio before committing.

Schema 1 remains readable. Upgrade it with `traceability-upgrade`: generate a preview, provide
closed-form resolutions for ambiguous links, apply atomically, then validate. Do not hand-convert
graphs or delete recovery journals.

Node IDs are feature-local because RD and task sequences reset per feature. Links within one graph
use the local node ID. A deliberate cross-feature link uses `<feature>/<node-id>`; an unqualified
link never resolves against a sibling feature by coincidence.

When a high- or critical-risk ambiguity reopens, every linked downstream
requirement, specification, invariant, criterion, test, task, implementation,
and verification must be marked `stale` (or returned to another non-approved
work state). Readiness reports both the reopened ambiguity and any downstream
artifact that still falsely claims completion.

## One owner per fact

The graph stores identity, state, and relationships. Markdown owns semantic content. Generated roadmaps own neither: they summarize the graph and on-disk execution state.
