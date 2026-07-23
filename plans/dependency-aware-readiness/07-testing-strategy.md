# Testing Strategy: Dependency-Aware Readiness

> **Document**: 07-testing-strategy.md
> **Parent**: [Index](00-index.md)

## Testing Overview

The state engine is safety-critical workflow logic. Every specified graph and CLI behavior receives
a black-box conformance test before implementation. Internal traversal, parsing, ordering, and
atomic-write paths receive implementation tests after the specification suite is green.

## 🚨 Specification Test Cases

> Expectations below come only from `01-requirements.md`, the `03-*` specifications, and resolved
> AR decisions. They are immutable oracles: implementation must change when it disagrees.

### Schema and Identity

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-1 | Valid schema-2 graph with directed typed edges | Validation succeeds and preserves one canonical edge per relationship | R1; 03-01 §Edge Model |
| ST-2 | Persist `blocks`, `provides-contract`, a redundant inverse, or illegal source/target pair | Validation fails and identifies the canonical relationship form | R1; AR-2; 03-01 §Error Handling |
| ST-3 | `--target accounting/RD-001` | Target resolves to that canonical node | R2; 03-01 §Canonical Identity |
| ST-4 | `--feature accounting --target RD-001` | Target resolves to `accounting/RD-001` | R2; AR-5 |
| ST-5 | Bare `--target RD-001` without feature | Command fails without guessing | R2; AR-5 |
| ST-6 | Target type is incompatible with requested gate | Command fails and lists allowed target types | R4; 03-02 §Error Handling |
| ST-7 | Duplicate canonical feature/node identity | Every readiness mode fails because target resolution is untrustworthy | R10; AR-10 |
| ST-8 | Contextual `related` edge | It is visible in derived status but absent from readiness and invalidation traversal | R3; AR-2 |

### Target Closure and Gate Profiles

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-9 | ERP feature: approved RD-01, draft unrelated RD-02, plan gate targets RD-01 | Gate succeeds and reports RD-02 excluded | R3, AC1 |
| ST-10 | RD-01 depends on draft RD-IAM-04 | Plan gate fails with target → dependency path | R3, AC2 |
| ST-11 | Draft payment-run RD consumes a contract provided by approved invoice RD | Invoice RD plan gate succeeds; downstream consumer is excluded | R3, AC3 |
| ST-12 | Same target evaluated under requirements and execution gates | Each gate includes only its profile-required trace evidence and returns its own verdict | R4; 03-02 §Gate Profiles |
| ST-13 | Cross-feature dependency enters an invalid graph | Gate blocks and reports the entering dependency path | R10; AR-10 |
| ST-14 | Unrelated feature graph is malformed | Target verdict is unchanged; malformed graph appears as out-of-scope diagnostic | R10; AR-10 |

### Contracts, Groups, and Releases

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-15 | Consumer requires stable contract; provider is provisional | Readiness blocks with required and actual maturity | R5; AR-6 |
| ST-16 | Consumer requires provisional contract; provider is stable | Maturity check passes | R5; AR-6 |
| ST-17 | Target one member of compiler frontend planning group | Closure atomically includes every group member | R6; AR-7 |
| ST-18 | Blocking dependency cycle remains after group contraction | Validation fails with deterministic cycle path | R6; AR-7 |
| ST-19 | Release has required, optional, and excluded members | Only required members block the release | R11; AR-11 |
| ST-20 | Required release member is release-coupled to another member | Coupled member enters release closure atomically | R11; AR-11 |

### Revisions and Migration

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-21 | Approved upstream node revision matches dependent snapshot | No stale blocker is emitted | R7; AR-8 |
| ST-22 | Upstream semantic revision changes after dependent validation | Affected dependent and its applicable downstream closure become stale | R7; AC5 |
| ST-23 | Upstream node is connected only by `related` | Revision change does not invalidate the related node | R7; AR-8 |
| ST-24 | Release-coupled member revision changes | Release evidence becomes stale; build/plan readiness does not | R7; AR-8 |
| ST-25 | Run schema-1 validation/readiness/status on legitimate isolated live and fixture roots | Existing semantics, exit codes, and human/JSON outcomes remain unchanged | R8; AC6; AR-28 |
| ST-26 | Request typed target readiness on schema 1 | Command returns an actionable explicit-upgrade requirement | R8, R16 |
| ST-27 | Preview and apply a legacy graph containing ambiguous links | Preview writes nothing; apply stops until every ambiguity is resolved; resolved apply preserves IDs, statuses, paths, evidence, and risk and is idempotent | R9; 03-03 §Upgrade Protocol |

### Workflow Integration

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-28 | make-requirements advances one RD | It invokes requirements gate for that RD, not every sibling | R12; AR-12 |
| ST-29 | Preflight audits one RD | Deterministic evidence uses exact target; sibling issue cannot expand modification scope | R12; AR-12 |
| ST-30 | make-plan targets an approved RD | It invokes plan gate for that RD and its closure | R12; AR-12 |
| ST-31 | exec-plan enters a plan then completes one task | It invokes execution gate for plan and task-complete gate for task | R12; AR-12 |
| ST-32 | Roadmap refresh after RD-01 advances | RD-01 changes; sibling RD stages remain unchanged | R12; AC7 |
| ST-33 | Feature acceptance with an incomplete required child | Aggregate gate remains blocked while independent child planning remains available | R12; AC8 |
| ST-34 | Full repository verification | All five confirmed commands complete successfully | R14; AC9; AR-14 |

### Corrective Preflight Cases

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-35 | Approved requirement with a draft owning specification | `requirements` may pass but `specifications` and `plan` gates fail independently | R15; AR-15, AR-16 |
| ST-36 | `status --target accounting/RD-001 --json` on valid but not-ready state | Exit 0; JSON reports canonical target, lifecycle, blockers, valid transitions, and per-gate readiness | R13, R16; AR-20 |
| ST-37 | Two writers transition the same expected revision | Exactly one commits; the stale writer exits nonzero without overwriting; committed graph validates | R16; AR-19 |
| ST-38 | Run root readiness in this repository, then run against an isolated fixture root | Repository run excludes fixture graphs; fixture-root run loads exactly fixture graphs | R17; AR-24 |
| ST-39 | Preview then apply traceability upgrade with complete versioned resolutions | Preview changes no artifact; apply preserves facts, writes valid v2 atomically, retains backup, and rerun is no-op | R9; AR-21 |
| ST-40 | Discover all declared conformance modules and enumerate ST implementations | Every declared module imports and every ST-1–ST-49 has one collected implementation | R14; AR-23, AR-27 |
| ST-41 | Complete corrective plan but omit or fail pilot rerun | codex-port 6.8 remains open; only passing retained rerun evidence permits closeout | R12; AR-26 |
| ST-42 | Same semantic sources with CRLF/LF, reordered source declaration, and trailing whitespace | Canonical revision is identical; semantic text change produces a different revision | R7; AR-18 |
| ST-43 | Transition request attempts an unlisted lifecycle jump or lacks required gate evidence | Exit nonzero, graph byte-identical, and stable invalid-transition blocker code returned | R16; AR-19, AR-20 |
| ST-44 | Recovery request targets a lock whose prior owner absence cannot be proven | Recovery is refused; lock, journal, and graphs remain unchanged | R16; AR-29 |
| ST-45 | Atomic replace succeeds but post-write validation fails | Before-image is restored and exit 1 returned, or exit 2 `recovery-required` preserves the journal if restoration cannot be proven | R16; AR-29 |
| ST-46 | Interrupted multi-graph journal is recovered with explicit roll-forward and matching hashes | Remaining graphs commit in journal order, all invariants validate, and recovery reports `recovered` | R16; AR-29 |
| ST-47 | Upgrade apply finds a non-identical existing backup | Apply refuses without overwriting the backup or graph | R9; AR-29 |
| ST-48 | Repeat an identical completed recovery request | No graph changes; result is `already-recovered` with exit 0 | R16; AR-29 |
| ST-49 | Approve a draft target once with a valid closure and once with an invalid dependency | Valid projected after-state commits approved; invalid closure exits nonzero and remains byte-identical | R16; AR-15, AR-19, AR-20 |

## Authoritative ST Ownership

This table is the single owner of ST-to-specification mapping. Specifications and execution tasks
cite these ranges only as consumers. (AR-27)

| Normative specification owner | ST cases |
|---|---|
| `03-01-graph-schema.md` | ST-1–ST-8, ST-15–ST-18, ST-42 |
| `03-02-readiness-engine.md` | ST-9–ST-20, ST-35, ST-36, ST-38, ST-43, ST-49 |
| `03-03-migration-and-invalidation.md` | ST-21–ST-27, ST-37, ST-39, ST-44–ST-48 |
| `03-04-workflow-integration.md` | ST-28–ST-34, ST-40, ST-41 |

`03-03` consumes ST-42 when verifying invalidation, but `03-01` is its sole normative owner.

## Test Categories

### Specification Tests

| Test File | ST Cases Covered | Component |
|---|---|---|
| `tests/conformance/test_state_v1_compat_spec.py` | ST-25 plus legacy command/output characterization | Schema-1 compatibility |
| `tests/conformance/test_state_v2_spec.py` | ST-1–ST-24, ST-35–ST-38, ST-42, ST-43, ST-49 | Schema and readiness engine |
| `tests/conformance/test_state_migration_spec.py` | ST-26, ST-27, ST-37, ST-39, ST-44–ST-48 | Compatibility, transitions, recovery, and migration |
| `tests/conformance/test_targeted_workflows_spec.py` | ST-28–ST-34, ST-40, ST-41 | Skills, roadmap, and product verification |

### Implementation Tests

| Test File | Description | Priority |
|---|---|---|
| `tests/conformance/test_state_v2_impl.py` | Parser boundaries, deterministic ordering, hostile cycles, relation matrices | High |
| `tests/conformance/test_state_migration_impl.py` | Interrupted writes, preview stability, malformed resolutions, path safety | High |
| `tests/conformance/test_targeted_workflows_impl.py` | Static command contracts and sibling-scope regression cases | High |

### Integration Tests

| Test | Components | Description |
|---|---|---|
| ERP independent advancement | Schema, engine, workflow | One RD advances while unrelated and downstream RDs remain draft |
| Compiler frontend group | Contracts, groups, engine | Contract maturity and atomic cyclic design group |
| Cross-feature release | Engine, release, roadmap | Required/coupled membership across features |
| Legacy upgrade | Schema, migration, engine | Preview, decision resolution, apply, validate, rerun |

### End-to-End Tests

| Scenario | Steps | Expected Result |
|---|---|---|
| RD lifecycle | Create graph, approve target, preflight, plan, execute, refresh roadmap | Each gate advances only the target closure |
| Release lifecycle | Declare release membership, verify members, run release gate | Only declared required/coupled members determine verdict |

## Test Data

### Fixtures Needed

- `tests/fixtures/state-v2-erp/`
- `tests/fixtures/state-v2-compiler/`
- `tests/fixtures/state-v2-cross-feature/`
- `tests/fixtures/state-v2-release/`
- `tests/fixtures/state-v2-invalid/`
- `tests/fixtures/state-v1-upgrade/`

### Mock Requirements

No network or service mocks. Use temporary directories and real JSON/Markdown artifacts.

## Verification Checklist

- [ ] All ST cases have concrete input and expected behavior.
- [ ] Specification tests exist before implementation and fail for missing schema-2 behavior.
- [ ] Specification expectations remain unchanged through implementation.
- [ ] Implementation tests cover hostile input, ordering, and interrupted migration.
- [ ] Existing schema-1 conformance remains green.
- [ ] All five commands confirmed in AR-14 pass.
- [ ] Test collection proves all declared modules and ST cases execute.
