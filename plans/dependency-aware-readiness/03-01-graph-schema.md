# Graph Schema: Dependency-Aware Readiness

> **Document**: 03-01-graph-schema.md
> **Parent**: [Index](00-index.md)

## Overview

Schema 2 gives every persisted relationship one direction and one semantic purpose. It preserves
semantic content in Markdown while the graph owns identity, lifecycle state, relationships,
revision identity, and validation snapshots. (AR-2, AR-3, AR-5, AR-6)

## Canonical Identity

- A node's canonical identity is `<feature>/<node-id>`.
- `--feature <f> --target <id>` resolves to `<f>/<id>`.
- `--target <feature>/<id>` is self-contained.
- Bare targets without `--feature` fail.
- Filenames and directory names never substitute for node identity. (AR-5)

## Node Model

Schema 2 retains schema-1 semantic node types and adds:

- `contract`: a versioned interface or invariant consumed across work items.
- `planning-group`: an atomic design/planning unit for a legitimate dependency cycle.
- `plan`: a gateable implementation plan.
- `requirement-set`: an explicit aggregate whose members are requirements.
- `feature`: an explicit feature-acceptance aggregate; it is distinct from the graph namespace.
- `audit-artifact`: an auditable graph-owned artifact. A graphless ad-hoc path has semantic
  preflight only and no deterministic readiness claim.
- `release`: an explicit delivery target.

Every semantic node carries a deterministic `revision`, a non-empty `semanticSources` array, and zero or more
`validations`. Only `contract` carries `maturity`. Aggregate/group nodes carry explicit `members`;
feature aggregates also carry `memberGates`, audit artifacts carry `auditStage`, and release
membership is split into `required`, `optional`, and `excluded`. (AR-6, AR-8, AR-17, AR-18)

### Normative node fields

```json
{
  "id": "RD-001",
  "type": "requirement",
  "title": "Capture supplier invoice",
  "status": "approved",
  "path": "requirements/RD-01.md",
  "semanticSources": [{
    "path": "requirements/RD-01.md",
    "selector": {"kind": "heading", "value": "RD-01"},
    "normalization": "utf8-lf-trim-trailing-v1",
    "digest": "sha256"
  }],
  "revision": "sha256:<64-lowercase-hex>",
  "edges": [{"relation": "depends-on", "target": "identity/RD-IAM-004"}],
  "validations": [{
    "upstream": "identity/RD-IAM-004",
    "relation": "depends-on",
    "revision": "sha256:<64-lowercase-hex>",
    "gate": "plan",
    "validatedAt": "RFC3339 UTC timestamp"
  }]
}
```

Allowed `selector.kind` values are `whole-file` and `heading`. A heading selector matches exactly
one normalized Markdown ATX heading and owns content until the next heading of equal or higher
level. Missing or duplicate matches are structural errors. Paths are project-relative and cannot
escape the root. Schema 2 uses SHA-256 over UTF-8 text after BOM removal, CRLF/CR→LF conversion,
removal of trailing horizontal whitespace per line, exactly one terminal LF, and concatenation in
lexicographically sorted `(path, selector.kind, selector.value)` order. The algorithm and
normalization names are persisted so later versions cannot reinterpret old revisions. (AR-18)

Validation snapshots are ordered by `(upstream, relation, gate)`. Duplicate keys are invalid.
A moved/missing source is a blocker until the source descriptor and revision are explicitly
revalidated. (AR-18)

### Normative status vocabulary

| Node type | Allowed statuses |
|---|---|
| requirement, specification, criterion, invariant, contract | `draft`, `approved`, `stale`, `superseded` |
| requirement-set, feature, planning-group, plan, audit-artifact, release | `draft`, `approved`, `stale`, `superseded` |
| ambiguity | `open`, `resolved`, `deferred-approved`, `superseded` |
| decision | `approved`, `stale`, `superseded` |
| deferral | `proposed`, `approved`, `expired`, `resolved`, `rejected` |
| test | `planned`, `red-confirmed`, `passing`, `blocked`, `stale`, `superseded` |
| task | `pending`, `implemented`, `verified`, `blocked`, `stale`, `superseded` |
| implementation | `present`, `verified`, `stale`, `superseded`, `reverted` |
| verification | `planned`, `passing`, `failing`, `blocked`, `stale`, `superseded` |
| finding | `open`, `accepted`, `resolved`, `superseded` |

## Edge Model

Each edge is stored once as `{"relation": RELATION, "target": CANONICAL_ID}`. Only
`consumes-contract` also requires `requiredMaturity`. Its meaning is always
`source --relation--> target`. (AR-2)

### Trace Relations

| Relation | Allowed direction | Purpose |
|---|---|---|
| `specified-by` | requirement → specification/invariant | Owning specification |
| `accepted-by` | requirement/specification → criterion | Acceptance obligation |
| `tested-by` | criterion → test | Specification-test evidence |
| `implemented-by` | specification/criterion/plan → task/implementation | Delivery ownership |
| `verified-by` | criterion/task/implementation → verification | Verification evidence |
| `affected-by` | downstream node → ambiguity/decision/finding | Material decision or finding impact |

Trace descendants are included only when required by the selected gate profile. (AR-3, AR-4)

### Dependency Relations

| Relation | Traversal |
|---|---|
| `depends-on` | Upstream for readiness and invalidation |
| `consumes-contract` | Upstream; edge requires `requiredMaturity` |
| `related` | Context only; never readiness or invalidation |
| `release-coupled` | Symmetric release closure only |

`blocks` and `provides-contract` are derived inverse views and cannot be persisted. Duplicate,
inverse, self, contradictory, illegal source/target, and unresolved relationships fail schema-2
validation. (AR-2)

The normative source/target matrix is:

| Relation | Source | Target |
|---|---|---|
| `specified-by` | requirement | specification or invariant |
| `accepted-by` | requirement, specification, invariant, contract | criterion |
| `tested-by` | criterion | test |
| `implemented-by` | specification, criterion, plan | task or implementation |
| `verified-by` | criterion, task, implementation | verification |
| `affected-by` | any semantic/delivery node | ambiguity, decision, or finding |
| `depends-on` | any gateable node | any gateable node except itself |
| `consumes-contract` | requirement, specification, plan, task, feature, release | contract |
| `related` | any node | any other node |
| `release-coupled` | feature, requirement, contract, release | feature, requirement, contract, release |

## Planning Groups

A planning-group node declares stable canonical member identities. The validator contracts each
group into one vertex before dependency-cycle analysis. Targeting any member expands atomically to
all members; members must support the selected gate. Cross-group blocking cycles fail with a
deterministic cycle path. (AR-7)

Requirement-set and feature aggregates use the same explicit canonical-member array but do not
contract dependency cycles. Membership arrays are sorted, unique, non-empty, and may cross feature
graphs only through fully qualified identities. An item may belong to multiple releases but to at
most one planning group per gate. A feature's `memberGates` is a closed map from every member ID to
one of `task-complete`, `feature-acceptance`, or `release`; missing/extra entries are invalid.
An audit artifact's `auditStage` is one of the normative gates other than `audit` and selects its
exact deterministic closure. (AR-7, AR-17)

## Release Nodes

A release declares required, optional, and excluded canonical members. No identity can appear in
conflicting membership sets. Release-coupled edges expand required membership atomically; optional
members do not block unless explicitly promoted to required. (AR-11)

Release nodes live in a normal graph whose `feature` namespace is conventionally `_releases`;
their canonical identity is `_releases/RELEASE-*`. This avoids a second portfolio file format.

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Bare or ambiguous target | Fail without guessing and show accepted canonical forms | AR-5 |
| Illegal edge direction/type | Structural error naming source, relation, and target | AR-2, AR-3 |
| Persisted inverse relationship | Reject with the canonical relation to store | AR-2 |
| Insufficient contract maturity | Readiness blocker with required and actual maturity | AR-6 |
| Dependency cycle outside group | Structural error with deterministic cycle path | AR-7 |
| Conflicting release membership | Structural error before closure evaluation | AR-11 |

## Testing Requirements

Normative ownership is defined only by the ST ownership table in `07-testing-strategy.md` (AR-27).
