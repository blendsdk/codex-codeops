# Execution Plan: Dependency-Aware Readiness

> **Document**: 99-execution-plan.md
> **Parent**: [Index](00-index.md)
> **Last Updated**: 2026-07-23 14:55
> **Progress**: 28/51 tasks (55%)
> **CodeOps Artifact Schema**: 1

## Overview

Implement target-scoped lifecycle gates through a thin CLI and focused standard-library modules,
preserving schema-1 behavior and the governing G1–G6 workflow. Every production phase follows
specification tests → red proof → implementation → green proof → implementation hardening → full
verification. Schema-1 characterization is written before the first shared parser change and runs
in every phase. (AR-15–AR-27)

**🚨 Update this document after EACH completed task!**

## Implementation Phases

| Phase | Title | Tasks |
|---|---|---:|
| 1 | Compatibility oracle and schema-2 model | 10 |
| 2 | Discovery, target closure, gates, and status | 9 |
| 3 | Revisions and atomic transitions | 9 |
| 4 | Traceability graph migration | 9 |
| 5 | Workflow, roadmap, docs, and pilot closeout | 14 |

**Total: 51 tasks across 5 phases**

> **⚠️ EXECUTION RULE — APPLIES TO EVERY AGENT EXECUTING THIS PLAN:**
>
> The task checkboxes below are the single source of truth. Every task appears exactly once.
> On implementation mark it `[~]` with `implemented: YYYY-MM-DD HH:MM`; on verification promote
> it to `[x]` with `completed: YYYY-MM-DD HH:MM`. Update Progress and Last Updated after every
> task. Resume the first `[~]`, otherwise the first `[ ]`. Obtain timestamps using
> `date '+%Y-%m-%d %H:%M'`.

## Phase 1: Compatibility Oracle and Schema-2 Model

> **Phase baseline tree**: `aad52b78b1e6d018dae0d7668302c93fcc87fc17`

### Step 1.1: Specification Tests

**Reference**: `03-01-graph-schema.md` · ST-1–ST-8, ST-15–ST-18, ST-25, ST-40, ST-42 ·
AR-2, AR-3, AR-5–AR-7, AR-18, AR-22, AR-23, AR-27

- [x] 1.1.1 [spec-author] Characterize exact schema-1 validate/readiness/status semantics and output on legitimate isolated roots, recording repository fixture exclusion as the sole authorized delta — `tests/conformance/test_state_v1_compat_spec.py` ✅ (completed: 2026-07-23 13:20)
- [x] 1.1.2 [spec-author] Add schema-2 model, identity, relation, aggregate, maturity, group, and revision cases — `tests/conformance/test_state_v2_spec.py` ✅ (completed: 2026-07-23 13:27)
- [x] 1.1.3 Add ERP and compiler schema-2 fixture artifacts — `tests/fixtures/state-v2-erp/`, `tests/fixtures/state-v2-compiler/` ✅ (completed: 2026-07-23 13:28)
- [x] 1.1.4 Run both specification modules: record schema-1 green characterization and schema-2 red result before production changes — `tests/conformance/test_state_v1_compat_spec.py`, `tests/conformance/test_state_v2_spec.py` ✅ (completed: 2026-07-23 13:28; schema 1: 6/6 green; schema 2: 10/10 expected red because schema 2 and target/gate arguments are absent)

### Step 1.2: Implementation

**Reference**: `03-01-graph-schema.md`

- [x] 1.2.1 Add the closed schema-2 contract while preserving the schema-1 contract — `schemas/traceability.schema.json`, `schemas/traceability-v2.schema.json` ✅ (completed: 2026-07-23 13:29)
- [x] 1.2.2 Create versioned graph/node/edge/source/snapshot models and status vocabularies — `scripts/codeops_state_lib/__init__.py`, `scripts/codeops_state_lib/models.py` ✅ (completed: 2026-07-23 13:31)
- [x] 1.2.3 Implement schema-specific parsing, relation matrices, aggregate membership, maturity, and group contraction — `scripts/codeops_state_lib/schema.py` ✅ (completed: 2026-07-23 13:36)
- [x] 1.2.4 Refactor the existing CLI into a thin dispatcher without changing schema-1 results, then run Phase-1 specification modules green — `scripts/codeops_state.py` ✅ (completed: 2026-07-23 13:37)

### Step 1.3: Implementation Tests and Hardening

**Reference**: `03-01-graph-schema.md` §Error Handling

- [x] 1.3.1 Add importable implementation tests for hostile relationships, identities, aggregate membership, maturity, deterministic cycles, and source selectors — `tests/conformance/test_state_v2_impl.py` ✅ (completed: 2026-07-23 13:38)
- [x] 1.3.2 Add the collection guard for every test module declared so far, rerun schema-1 compatibility, and run the confirmed full verification gate — `scripts/validate-codex.sh`, `tests/conformance/test_state_test_collection.py` ✅ (completed: 2026-07-23 13:39)

**Verify**: run all five commands confirmed in AR-14.

## Phase 2: Discovery, Target Closure, Gates, and Status

> **Phase baseline tree**: `28f29f740e88ec3d0bf9d1cef13af6470b5716cd`

### Step 2.1: Specification Tests

**Reference**: `03-02-readiness-engine.md` · ST-3–ST-20, ST-35, ST-36, ST-38 ·
AR-1, AR-4, AR-10, AR-15, AR-16, AR-17, AR-20, AR-24

- [x] 2.1.1 [spec-author] Add matrix-row cases for requirements, specifications, plan, audit, execution, task-complete, feature-acceptance, and release gates — `tests/conformance/test_state_v2_spec.py` ✅ (completed: 2026-07-23 13:59)
- [x] 2.1.2 [spec-author] Add target status, scoped diagnostics, dependency-path, discovery-root, and release-closure cases — `tests/conformance/test_state_v2_spec.py` ✅ (completed: 2026-07-23 14:04)
- [x] 2.1.3 Add cross-feature, release, invalid-unrelated, and repository-root discovery fixtures, then record the expected red result while schema-1 remains green — `tests/fixtures/state-v2-cross-feature/`, `tests/fixtures/state-v2-release/`, `tests/fixtures/state-v2-invalid/` ✅ (completed: 2026-07-23 14:04)

### Step 2.2: Implementation

**Reference**: `03-02-readiness-engine.md` §Closure Algorithm, §Gate Profiles, §Scoped Structural Policy

- [x] 2.2.1 Implement configured/conventional live-root discovery, canonical identity resolution, and isolated fixture-root loading — `scripts/codeops_state_lib/discovery.py` ✅ (completed: 2026-07-23 14:04)
- [x] 2.2.2 Implement deterministic target/group/dependency/release closure and shortest blocker paths — `scripts/codeops_state_lib/closure.py` ✅ (completed: 2026-07-23 14:04)
- [x] 2.2.3 Implement the normative gate predicates and target lifecycle/status derivation — `scripts/codeops_state_lib/gates.py` ✅ (completed: 2026-07-23 14:04)
- [x] 2.2.4 Implement stable human/JSON rendering for readiness/status, then run Phase-2 and schema-1 specification modules green — `scripts/codeops_state_lib/rendering.py`, `scripts/codeops_state.py` ✅ (completed: 2026-07-23 14:04)

### Step 2.3: Implementation Tests and Hardening

**Reference**: `03-02-readiness-engine.md` §Error Handling

- [x] 2.3.1 Add traversal-order, shortest-path, hostile-cycle, mixed-schema, incompatible-gate, and root-discovery tests — `tests/conformance/test_state_v2_impl.py` ✅ (completed: 2026-07-23 14:07)
- [x] 2.3.2 Rerun schema-1 compatibility, assert test collection, and run the confirmed full verification gate — `tests/conformance/test_state_v1_compat_spec.py`, `scripts/validate-codex.sh` ✅ (completed: 2026-07-23 14:07)

**Verify**: run all five commands confirmed in AR-14.

**Phase review**: independent reviewer and auditor PASS after accepted remediation; 93 state
conformance tests and all five repository gates passed.

## Phase 3: Revisions and Atomic Transitions

> **Phase baseline tree**: `89c71e415264bd30021bba6510428936c66c922b`

### Step 3.1: Specification Tests

**Reference**: `03-03-migration-and-invalidation.md` §Atomic Transition Protocol ·
ST-21–ST-24, ST-36, ST-37, ST-42–ST-46, ST-48 · AR-8, AR-18–AR-20, AR-29

- [x] 3.1.1 [spec-author] Add canonical revision, snapshot mismatch, relationship-specific invalidation, and normalization cases — `tests/conformance/test_state_v2_spec.py` ✅ (completed: 2026-07-23 14:52)
- [x] 3.1.2 [spec-author] Add legal/illegal lifecycle, compare-and-swap, lock-owner proof, explicit recovery, interruption journal, and post-write rollback cases — `tests/conformance/test_state_migration_spec.py` ✅ (completed: 2026-07-23 14:53)
- [x] 3.1.3 Run Phase-3 specification modules red while every earlier and schema-1 specification module remains green — `tests/conformance/test_state_v2_spec.py`, `tests/conformance/test_state_migration_spec.py` ✅ (completed: 2026-07-23 14:53)

### Step 3.2: Implementation

**Reference**: `03-01-graph-schema.md` §Normative node fields ·
`03-03-migration-and-invalidation.md` §Atomic Transition Protocol

- [x] 3.2.1 Implement semantic-source normalization, versioned SHA-256 revisions, snapshot validation, and stale propagation — `scripts/codeops_state_lib/revisions.py` ✅ (completed: 2026-07-23 14:55)
- [x] 3.2.2 Implement lock-safe compare-and-swap, atomic replacement, transition journals, and explicit recovery — `scripts/codeops_state_lib/transitions.py` ✅ (completed: 2026-07-23 14:59)
- [x] 3.2.3 Expose target transition/status contracts through the thin CLI, then run Phase-3 specification modules green — `scripts/codeops_state.py`, `scripts/codeops_state_lib/rendering.py` ✅ (completed: 2026-07-23 14:59)
- [x] 3.2.4 Expose `transition-recover` request/result/exit contracts with explicit roll-forward/rollback — `scripts/codeops_state.py`, `scripts/codeops_state_lib/transitions.py`, `scripts/codeops_state_lib/rendering.py` ✅ (completed: 2026-07-23 15:01)

### Step 3.3: Implementation Tests and Hardening

**Reference**: `03-03-migration-and-invalidation.md` §Error Handling

- [x] 3.3.1 Add concurrent-writer, stale-lock, interrupted-journal, moved-source, cross-platform normalization, and path-safety tests — `tests/conformance/test_state_migration_impl.py` ✅ (completed: 2026-07-23 15:01)
- [x] 3.3.2 Rerun all earlier/schema-1 specification modules, assert collection, and run the confirmed full verification gate — `scripts/validate-codex.sh`, `tests/conformance/test_state_v1_compat_spec.py` ✅ (completed: 2026-07-23 15:03)

**Verify**: run all five commands confirmed in AR-14.

**Phase review remediation**: the initial independent review found unsafe recovery-owner trust,
post-replace cleanup gaps, caller-selectable gate bypass, incomplete projected/post-write
validation, missing lifecycle evidence enforcement, optional snapshots, non-durable recovery
images, incomplete lock/journal binding, and absent production multi-graph invalidation. The user
accepted every recommended fix. The transition engine now derives governing gates, persists
lifecycle evidence, requires relationship snapshots, proves recorded process absence, serializes
recovery, retains uncertain state, validates complete projected and committed portfolios, and
journals downstream invalidation across graphs. Focused state verification passes; one-time
re-review findings were resolved under the user's delegated technical authority, and the final
97-test state suite plus all five repository gates passed on 2026-07-23 15:45.

## Phase 4: Traceability Graph Migration

> **Phase baseline tree**: recorded by exec-plan before the first phase mutation

### Step 4.1: Specification Tests

**Reference**: `03-03-migration-and-invalidation.md` §Upgrade Protocol ·
ST-25–ST-27, ST-39, ST-47 · AR-9, AR-18, AR-21, AR-22, AR-28, AR-29

- [ ] 4.1.1 [spec-author] Add preview/resolution/apply, source-classification, backup, recovery, and idempotence cases — `tests/conformance/test_state_migration_spec.py`
- [ ] 4.1.2 Add ambiguous/resolved schema-1 graphs and versioned preview/resolution fixtures — `tests/fixtures/state-v1-upgrade/`
- [ ] 4.1.3 Run migration specification cases red while all schema-1 and earlier schema-2 cases remain green — `tests/conformance/test_state_migration_spec.py`, `tests/conformance/test_state_v1_compat_spec.py`

### Step 4.2: Implementation

**Reference**: `03-03-migration-and-invalidation.md` §Upgrade Protocol

- [ ] 4.2.1 Implement deterministic preview generation and versioned resolution validation — `scripts/codeops_state_lib/migration.py`
- [ ] 4.2.2 Implement atomic apply, backup lifecycle, interruption recovery, and idempotent rerun through shared transitions — `scripts/codeops_state_lib/migration.py`, `scripts/codeops_state_lib/transitions.py`
- [ ] 4.2.3 Expose `traceability-upgrade` CLI/output/exit contracts, then run Phase-4 specification cases green — `scripts/codeops_state.py`, `scripts/codeops_state_lib/rendering.py`
- [ ] 4.2.4 Integrate backup collision, post-replace rollback, and exit-2 recovery-required behavior with `transition-recover` — `scripts/codeops_state_lib/migration.py`, `scripts/codeops_state_lib/transitions.py`

### Step 4.3: Implementation Tests and Hardening

**Reference**: `03-03-migration-and-invalidation.md` §Error Handling

- [ ] 4.3.1 Add malformed-resolution, changed-preview, partial-write, backup, repeated-apply, permission, and path-escape tests — `tests/conformance/test_state_migration_impl.py`
- [ ] 4.3.2 Rerun every schema-1/schema-2 specification module, assert collection, and run the confirmed full verification gate — `scripts/validate-codex.sh`, `tests/conformance/test_state_v1_compat_spec.py`

**Verify**: run all five commands confirmed in AR-14.

## Phase 5: Workflow, Roadmap, Documentation, and Pilot Closeout

> **Phase baseline tree**: recorded by exec-plan before the first phase mutation

### Step 5.1: Specification Tests

**Reference**: `03-04-workflow-integration.md` · ST-28–ST-34, ST-40, ST-41 ·
AR-12, AR-20, AR-21, AR-23, AR-24, AR-26, AR-27

- [ ] 5.1.1 [spec-author] Add exact target/gate/transition/upgrade command-contract cases for every lifecycle skill — `tests/conformance/test_targeted_workflows_spec.py`
- [ ] 5.1.2 [spec-author] Add independent sibling roadmap, explicit release, test-collection, and codex-port 6.8 closeout cases — `tests/conformance/test_targeted_workflows_spec.py`
- [ ] 5.1.3 Extend roadmap and retained pilot fixtures, then record Phase-5 red while every engine/migration suite remains green — `scripts/fixtures/roadmap-repo/`, `tests/evidence/`

### Step 5.2: Implementation

**Reference**: `03-04-workflow-integration.md` §Workflow Mapping, §Rollout Order,
§Governing Port Program

- [ ] 5.2.1 Update traceability reference and requirements workflow for schema-2 target/gate/transition authoring — `references/artifacts/traceability.md`, `skills/make-requirements/SKILL.md`, `skills/make-requirements/templates.md`
- [ ] 5.2.2 Update specification completion, narrow preflight, and plan creation to use exact targets without scope expansion — `skills/preflight/SKILL.md`, `skills/preflight/dimensions.md`, `skills/make-plan/SKILL.md`
- [ ] 5.2.3 Update execution and upgrade workflows for target transitions and traceability graph migration — `skills/exec-plan/SKILL.md`, `skills/exec-plan/execution-protocol.md`, `skills/upgrade-plan/SKILL.md`
- [ ] 5.2.4 Update roadmap aggregation and sync behavior for target status, independent siblings, and releases — `skills/roadmap/SKILL.md`, `scripts/codeops-roadmap-sync.sh`, `scripts/roadmap-sync-check.sh`
- [ ] 5.2.5 Extend deterministic assertions for workflow commands and fixture exclusion, and extend the collection guard through ST-49 — `scripts/validate-codex.sh`, `tests/conformance/test_state_test_collection.py`, `tests/conformance/test_targeted_workflows_spec.py`
- [ ] 5.2.6 Document graph schema, gate profiles, target workflows, and migration — `docs/concepts.md`, `docs/tutorial.md`, `docs/migration.md`
- [ ] 5.2.7 Document diagnostics, public usage, compatibility, and release semantics — `docs/troubleshooting.md`, `README.md`, `CHANGELOG.md`
- [ ] 5.2.8 Run Phase-5 specification cases green without changing any ST expectation — `tests/conformance/test_targeted_workflows_spec.py`

### Step 5.3: Implementation Tests, Pilot Evidence, and Hardening

**Reference**: `03-04-workflow-integration.md` §Error Handling and §Governing Port Program

- [ ] 5.3.1 Add workflow scope-drift, sibling-stage, command-output, broken-link, and documentation tests — `tests/conformance/test_targeted_workflows_impl.py`
- [ ] 5.3.2 Rerun the triggering complex-project milestone with target-scoped gates and retain redacted/content-safe result evidence — `tests/evidence/`
- [ ] 5.3.3 If and only if retained pilot evidence passes, update codex-port task 6.8/progress and run the complete confirmed verification gate — `plans/codex-port/99-execution-plan.md`, `tests/evidence/`

**Verify**:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

## Dependencies

```text
Phase 1: freeze schema-1 + add schema-2 model
    ↓
Phase 2: live discovery + target closure/gates/status
    ↓
Phase 3: revisions + atomic lifecycle transitions
    ↓
Phase 4: explicit traceability graph migration
    ↓
Phase 5: workflow adoption + pilot closeout
```

## Success Criteria

The feature is complete when all 51 tasks are verified, ST-1 through ST-49 pass unchanged,
schema-1 behavior remains green in every phase, all declared tests are collected, repository-root
state excludes fixtures, migration and lifecycle transitions meet recovery contracts, G1–G6 remain
independently enforced, workflows advance only their target closures, retained pilot evidence
permits codex-port 6.8 closeout, and all five confirmed verification commands pass.
