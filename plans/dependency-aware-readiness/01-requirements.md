# Requirements: Dependency-Aware Readiness

> **Document**: 01-requirements.md
> **Parent**: [Index](00-index.md)

## Feature Overview

CodeOps shall evaluate lifecycle readiness for an explicitly selected graph target and the exact
evidence and blocking dependencies required by the selected lifecycle gate. Feature and portfolio
aggregation remain available for acceptance and governance but do not block independent work
merely because it shares a directory or feature label. (AR-1, AR-4)

## Functional Requirements

### Must Have

- [ ] **R1 — Typed graph:** Schema 2 stores canonical directed, typed relationships and rejects
  invalid, redundant, contradictory, or dangling relationships. (AR-2, AR-3)
- [ ] **R2 — Stable targets:** Every gateable artifact has canonical identity
  `<feature>/<node-id>`; scoped shorthand is deterministic and ambiguous bare targets fail. (AR-5)
- [ ] **R3 — Target closure:** Readiness includes the selected target, gate-required owned trace
  descendants, transitive blocking dependencies, and entering cross-feature dependencies, while
  excluding contextual and downstream siblings. (AR-2 through AR-5)
- [ ] **R4 — Gate profiles:** Requirements, plan, execution, task-completion, feature-acceptance,
  and release gates enforce distinct evidence and status rules. (AR-4)
- [ ] **R5 — Contracts:** Contract nodes carry maturity; consumers state required maturity and
  block when the provided maturity is insufficient. (AR-6)
- [ ] **R6 — Planning groups:** Explicit groups contract legitimate dependency cycles and expand
  atomically when any member is targeted; remaining blocking cycles fail validation. (AR-7)
- [ ] **R7 — Precise invalidation:** Semantic revision changes invalidate only downstream artifacts
  whose recorded validation snapshots are stale under the relevant relationship semantics. (AR-8)
- [ ] **R8 — Schema compatibility:** Schema-1 graphs retain their current behavior. Typed target
  readiness requires explicit schema-2 upgrade. (AR-9)
- [ ] **R9 — Safe migration:** Upgrade is preview-first, explicit, idempotent, status/evidence
  preserving, and stops for user resolution rather than guessing ambiguous legacy links. (AR-9)
- [ ] **R10 — Scoped diagnostics:** Target readiness blocks on trustworthy identity resolution,
  configuration, and failures within its closure; unrelated invalid graphs are reported without
  becoming target blockers. Portfolio validation remains global. (AR-10)
- [ ] **R11 — Explicit releases:** Release targets declare required, optional, excluded, and
  release-coupled membership; release readiness is distinct from portfolio status. (AR-11)
- [ ] **R12 — Workflow consistency:** Requirements, preflight, planning, execution, roadmap,
  feature acceptance, upgrades, and release checks select the correct target and gate. (AR-12)
- [ ] **R13 — Explainability:** Human and JSON output identify the gate, canonical target, closure
  members, excluded out-of-scope diagnostics, blockers, and dependency path for each blocker.
- [ ] **R14 — Cross-project generality:** Conformance fixtures prove independent ERP-style RDs,
  compiler contracts and planning groups, cross-feature dependencies, and explicit releases.
- [ ] **R15 — Governing lifecycle:** A distinct specifications-complete gate preserves G2 between
  requirements approval and planning, and every gate has normative deterministic predicates.
  (AR-15, AR-16)
- [ ] **R16 — Durable transitions:** All lifecycle, revision, snapshot, and stale-state mutations
  use one validated atomic transition mechanism rather than independent JSON edits. (AR-19, AR-20)
- [ ] **R17 — Self-hosting discovery:** Repository-root state commands ignore test fixtures and
  other non-artifact trees while fixture-root tests remain directly executable. (AR-24)

### Should Have

- [ ] **R18 — Derived views:** Status output may display derived inverse relationships such as
  “blocks” and “provided to” without persisting inverse edges. (AR-2)
- [ ] **R19 — Upgrade guidance:** Schema-1 target requests return the exact preview/upgrade action
  needed rather than a generic incompatibility error. (AR-9)

### Won't Have

- Automatic semantic inference for legacy untyped links.
- Silent approval of dependencies, sibling requirements, or planning-group members.
- Automatic release membership derived from directory contents.
- A network service, database, or third-party graph dependency.
- Project-specific exceptions for ERP, compiler, or jsvision repositories.
- Changes to the preserved Claude implementation in `../codeops`.

## Technical Requirements

### Performance

- Target closure and validation shall be deterministic and bounded by the selected graph plus
  explicitly entering cross-feature references; no network access is permitted.
- Graph traversal shall terminate for hostile cycles and report deterministic cycle paths.

### Compatibility

- Existing schema-1 validation, readiness, status, fixtures, and command behavior remain supported.
- Compatibility is measured on legitimate configured/conventional or explicitly isolated roots.
  Recursive ingestion of repository test fixtures is a corrected discovery defect, not protected
  schema-1 behavior. (AR-28)
- Schema-2 output is stable, machine-readable JSON with deterministic ordering.
- Mixed schema-1/schema-2 repositories remain inspectable; typed dependencies cannot cross through
  a schema-1 graph until that graph is upgraded. (AR-9, AR-10)

### Security

- Feature names, target IDs, paths, revisions, and migration output paths are validated as
  untrusted local input.
- Artifact and evidence paths cannot escape the project root.
- Upgrade preview performs no writes; apply writes only explicitly resolved conversions.
- Diagnostics never execute artifact content or shell fragments.

## Scope Decisions

All scope decisions are owned by AR-1 through AR-14 in the
[Ambiguity Register](00-ambiguity-register.md); this document cites them instead of restating the
option analysis.

## Acceptance Criteria

1. [ ] A plan gate for one approved RD succeeds while unrelated sibling RDs remain draft.
2. [ ] A plan gate fails with a dependency path when an upstream blocking RD is draft.
3. [ ] A downstream consumer does not block its provider's plan gate.
4. [ ] Contract maturity and atomic planning-group behavior are deterministic.
5. [ ] Revision mismatch invalidates only the affected downstream closure.
6. [ ] Schema-1 behavior is regression-tested and schema-2 upgrade is explicit and lossless.
7. [ ] Each lifecycle skill invokes the correct target/gate and respects its modification scope.
8. [ ] Explicit feature and release aggregation gates remain strict.
9. [ ] All five confirmed verification commands pass. (AR-14)
10. [ ] The governing G2 specification gate remains independently observable and invalidatable.
11. [ ] Root state discovery excludes repository fixtures and the codex-port 6.8 pilot closes only
    after retained target-scoped rerun evidence passes. (AR-24, AR-26)
