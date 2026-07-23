# Readiness Engine: Dependency-Aware Readiness

> **Document**: 03-02-readiness-engine.md
> **Parent**: [Index](00-index.md)

## Overview

The readiness engine resolves a canonical target, expands any atomic group, derives the
gate-required owned evidence, follows only blocking upstream dependencies, and evaluates the
selected gate profile. It reports both membership and dependency paths so readiness is explainable.
(AR-1 through AR-7, AR-10, AR-11)

## Command Contract

```text
codeops_state.py readiness --root ROOT --gate GATE --target FEATURE/NODE
codeops_state.py readiness --root ROOT --gate GATE --feature FEATURE --target NODE
codeops_state.py status --root ROOT --target FEATURE/NODE
codeops_state.py transition --root ROOT --request TRANSITION.json
codeops_state.py transition-recover --root ROOT --request RECOVERY.json
```

`--feature` without `--target` retains schema-1 feature-wide behavior. Schema-2 target readiness
requires both target and gate, except workflow skills supply their known gate automatically.
`status --target` returns lifecycle state without treating ordinary not-ready state as a command
failure. `transition` is the only public mutation entry point; it delegates to the transaction
contract in `03-03`. Its versioned request contains operation ID, canonical target, expected
status/revision, requested status, gate, revision-source update, snapshot additions/removals, and
an optional stale reason. Unknown fields, missing preconditions, or stale expected state exit
nonzero without writing. JSON output returns operation ID, before/after hashes, committed target,
and post-write validation result.

`transition-recover` consumes a versioned request containing operation/journal ID, explicit
`roll-forward` or `rollback`, expected current/before/after hashes for every graph, proof metadata
that the recorded owner process is absent, and the expected stale-lock identity. It never chooses a
direction implicitly. Its output reports recovered members, lock/backup disposition, final hashes,
post-recovery validation, and one of `recovered`, `already-recovered`, `refused`, or
`recovery-required`. (AR-29)
(AR-4, AR-5, AR-9, AR-20)

## Closure Algorithm

1. Validate configuration and global canonical identity uniqueness.
2. Resolve target without filesystem inference.
3. Load and structurally validate the target graph.
4. Expand planning-group membership.
5. Add trace descendants required by the gate profile.
6. Traverse `depends-on` and `consumes-contract` upstream transitively.
7. Load and validate cross-feature graphs entered by that traversal.
8. Apply release-coupled expansion only for release gates.
9. Evaluate profile statuses, ambiguities, findings, deferrals, maturity, revisions, and evidence.
10. Emit deterministic closure, exclusions, dependency paths, diagnostics, and verdict.

`related`, downstream consumers, optional release members, and unrelated siblings are excluded.
(AR-2 through AR-4, AR-10, AR-11)

## Gate Profiles

The following table is normative. “Current” means non-stale revisions and matching validation
snapshots for every traversed blocking edge. Every gate also blocks on an open critical/high
ambiguity, unapproved deferral, or open critical/major finding connected through `affected-by`.
(AR-4, AR-15, AR-16)

| Gate | Valid targets | Required owned trace closure | Required state/evidence |
|---|---|---|---|
| `requirements` | requirement, requirement-set | `accepted-by`, `affected-by` | Target requirements and criteria `approved`; material ambiguities resolved/deferred-approved; decisions approved; blocking requirements current and approved |
| `specifications` | requirement, specification, invariant, contract, planning-group | `specified-by`, `accepted-by`, `affected-by` | Every selected specification/invariant/contract and criterion `approved`; interface ownership complete; blocking dependencies current; consumed contracts meet maturity |
| `plan` | requirement, task, planning-group, plan | required G1/G2 trace plus `affected-by` | Target requirements and blocking closure pass `requirements` and `specifications`; an existing plan is `approved`; a lightweight task is `pending` and has approved prerequisites; no implementation/test completion is required |
| `audit` | any graph-owned semantic node or aggregate | Requirement/set → `requirements`; specification/invariant/contract/group → `specifications`; plan → `execution`; pending task → `plan`; implemented/verified/blocked/stale task → `task-complete`; feature → `feature-acceptance`; release → `release`; audit-artifact → its persisted `auditStage` | The mapped profile's structural closure is evaluated and all deterministic blockers are reported; semantic preflight verdict remains owned by the report, not this gate |
| `execution` | plan | `specified-by`, `accepted-by`, `implemented-by`, `affected-by` | Plan/specifications/criteria `approved`; tasks may be `pending`; planned tests exist; revisions current; repository entry evidence attached |
| `task-complete` | task | `tested-by`, `implemented-by`, `verified-by`, `affected-by` | Task `verified`; required tests `passing`; implementation `present` or `verified`; verification `passing`; all snapshots current |
| `feature-acceptance` | feature | Every required member's persisted `memberGates` closure | Every member passes the gate named by `memberGates`; aggregate `approved`; all snapshots current |
| `release` | release | Required and release-coupled members plus their terminal trace closure | Required/coupled delivery evidence verified/passing; required contract maturity met; release `approved`; optional/excluded members ignored |

Target closure follows only `depends-on` and `consumes-contract` upstream. Trace relations are
followed only in the direction and set named above. `related` is never included.
`release-coupled` is included only for release. A superseded node never satisfies approval or
terminal delivery evidence; consumers must explicitly target the current replacement node through
an ordinary ownership or dependency relation. (AR-2, AR-3, AR-15)

### Verdict and exit semantics

- `readiness`: exit 0 only when the selected gate passes; exit 1 for blockers or structural errors.
- `status`: exit 0 for valid state even when `ready:false`; exit 1 only for structural/read errors.
- `transition` and `traceability-upgrade`: exit 0 only after committed write and post-write
  validation; exit 1 only when durable project state remains byte-identical; exit 2
  `recovery-required` when a write occurred and automatic restoration cannot be proven.
- `transition-recover`: exit 0 for `recovered` or hash-identical `already-recovered`; exit 1 for
  `refused`; exit 2 for `recovery-required` when state changed but automated restoration cannot
  safely complete.
- `validate`: portfolio-wide exit 0 only when every live graph is structurally valid.

Human and JSON results carry the same canonical blocker codes; text is presentation, JSON is the
stable integration contract. (AR-15, AR-20)

### Allowed lifecycle transitions

This matrix is normative. Every transition also requires matching expected status/revision,
structural validity, and the named gate where shown. Any transition not listed fails without a
write. (AR-19, AR-20)

For `draft → approved`, the governing gate evaluates the target in its proposed approved
after-state while every other closure member remains in current durable state. The write occurs
only if that projected gate passes. This is the only projected-state exception; it prevents
circular approval without hiding an unapproved dependency. All other transitions evaluate current
state plus their explicitly named evidence.

| Node family | Allowed transition | Required gate/evidence |
|---|---|---|
| requirement/specification/criterion/invariant/contract/aggregate/plan | `draft → approved` | Node's governing requirements/specifications/plan/acceptance gate passes |
| same content family | `approved → stale` | Revision mismatch, reopened affected-by node, or explicit stale reason |
| same content family | `stale → draft` | Explicit reopen decision |
| same content family | `stale → approved` | Governing gate rerun passes with new snapshots |
| same content family | `draft|approved|stale → superseded` | Explicit replacement identity exists and validates |
| test | `planned → red-confirmed → passing` | Red evidence, then green evidence |
| test | `passing → stale`; `planned|red-confirmed|passing → blocked` | Invalidation or recorded blocker |
| task | `pending → implemented → verified` | Update-before-verify; verification evidence for final step |
| task | `pending|implemented → blocked`; `implemented|verified → stale` | Recorded blocker or invalidation |
| implementation | `present → verified`; `present|verified → stale|reverted` | Verification, invalidation, or explicit rollback evidence |
| verification | `planned → passing|failing|blocked`; `passing → stale` | Attached command evidence or invalidation |
| ambiguity/finding/deferral/decision | Only transitions allowed by the status vocabulary and shared ambiguity/finding protocols | Explicit user ruling where those protocols require it |

## Diagnostics

JSON and human output include:

- selected gate and canonical target;
- schema version;
- ordered closure members with inclusion reason;
- blockers with complete shortest dependency paths;
- excluded out-of-scope diagnostics;
- planning-group and release expansions;
- required versus actual contract maturity;
- stale revision snapshot mismatches;
- final readiness verdict.

`status --target` additionally returns node status, derived lifecycle, last revision, stale
upstream snapshots, valid next transitions, and per-gate readiness summaries. Roadmap consumes
this output and never derives lifecycle predicates itself. (AR-20)

## Scoped Structural Policy

Portfolio `validate` remains global. Target readiness treats configuration failures, duplicate
canonical identities, the target graph, and every graph entered by closure as blocking. Other
invalid graphs are reported as out-of-scope diagnostics and do not change the target verdict.
(AR-10)

“Global” means every live CodeOps artifact graph, not every JSON file in the repository. Discovery
uses `codeops/codeops.json` artifact root when configured; otherwise it searches only the
conventional live roots `codeops/features/` and, for flat layout, the project-root
`traceability.json`. It excludes `tests/`, fixture trees, archives, VCS metadata, dependency
directories, agent configuration, and plans that merely describe examples. Supplying a fixture
directory as `--root` makes that directory the isolated project root, so fixture graphs remain
directly testable. (AR-24)

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Target type incompatible with gate | Fail and list accepted target types | AR-4, AR-5 |
| Cross-feature dependency enters invalid graph | Block and show entering dependency path | AR-10 |
| Unrelated graph is invalid | Report out-of-scope diagnostic; preserve target verdict | AR-10 |
| Schema-1 graph requested with target gate | Return actionable upgrade-required result | AR-9 |
| Required contract maturity missing | Block at consuming edge | AR-6 |

## Testing Requirements

Normative ownership is defined only by the ST ownership table in `07-testing-strategy.md` (AR-27).
