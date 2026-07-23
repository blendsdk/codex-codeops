# Preflight Report: Dependency-Aware Readiness

> **Status**: ✅ PREFLIGHT PASSED — all 15 findings resolved
> **Iteration**: 2 (bounded verification after accepted fixes)
> **Artifact**: Full implementation plan at `plans/dependency-aware-readiness/`
> **Artifact Content Hash**: `2eb619114384798fc219c141d0f67c81d5380d319511e814e602286d657a8b07`
> **Iteration-1 Content Hash**: `e5ad29cda809d3d668b19a8cf98cf9fd9e95c1e3a51013d443b8cbbe713ab79c`
> **Audit Target**: `plans/dependency-aware-readiness/`
> **Context Documents**: CodeOps implementation, schemas, tests, skills, docs, and governing
> `plans/codex-port/` program; context is not part of the pass verdict or modification set
> **Modification Set**: This report and `_preflight-notes.md` only; plan fixes not yet authorized
> **Codebase Grounded**: 18 implementation/test/workflow files examined; 34 ST cases and 36 plan
> tasks checked against repository behavior
> **Last Updated**: 2026-07-23

> ⚠️ **SAME-SESSION REVIEW:** This plan was created in the current session. Same-agent bias risk
> is elevated. Independent clustered auditors and a separate recommendation challenger were used;
> a fresh-session or human architecture review remains advisable for this foundational state model.

## Codebase Context Summary

**Tech Stack:** Python standard-library state engine; Bash validation, migration, and roadmap
tools; JSON Schema; Markdown skills/docs; Python `unittest` conformance tests.

**Architecture:** `scripts/codeops_state.py` discovers and validates per-feature
`traceability.json` graphs and emits lifecycle/readiness/status. Semantic skills call that
deterministic core. Roadmaps and docs are derived consumers. Schema 1 uses closed node objects and
untyped string links.

**Key Files Examined:** `AGENTS.md`, `scripts/codeops_state.py`,
`schemas/traceability.schema.json`, `tests/conformance/test_state.py`,
`scripts/validate-codex.sh`, `scripts/codeops-roadmap-sync.sh`,
`references/artifacts/traceability.md`, lifecycle skills, roadmap fixtures,
`plans/codex-port/03-02-workflow-and-gates.md`, and
`plans/codex-port/99-execution-plan.md`.

**Deterministic Evidence:** `codeops_state.py readiness --root . --json` exits 1 because broad
discovery ingests deliberately invalid state fixtures and sees duplicate `ledger` identities,
a missing fixture link, draft content, and an open fixture ambiguity. The five repository
verification commands otherwise passed before this scan.

## Summary by Dimension

| # | Dimension | Findings | Highest Severity |
|---|---|---:|---|
| 1 | Ambiguities | 7 | 🟠 |
| 2 | Implicit Assumptions | 10 | 🟠 |
| 3 | Logical Contradictions | 2 | 🟠 |
| 4 | Completeness Gaps | 9 | 🟠 |
| 5 | Dependency Issues | 5 | 🟠 |
| 6 | Feasibility Concerns | 5 | 🟠 |
| 7 | Testability | 6 | 🟠 |
| 8 | Security Blind Spots | 2 | 🟠 |
| 9 | Edge Cases | 5 | 🟠 |
| 10 | Scope Creep Indicators | 0 | — |
| 11 | Ordering & Sequencing | 5 | 🟠 |
| 12 | Consistency | 4 | 🟠 |
| 13 | Codebase Alignment | 10 | 🟠 |

## Summary by Severity

| Severity | Count | Status |
|---|---:|---|
| 🔴 CRITICAL | 0 | — |
| 🟠 MAJOR | 14 | all resolved and verified |
| 🟡 MINOR | 1 | resolved and verified |
| 🔵 OBSERVATION | 0 | — |

## Findings

### PF-001 — 🟠 MAJOR — Gate profiles lack normative predicates

**Dimensions:** Ambiguities, Completeness, Testability, Consistency

**Problem:** `03-02-readiness-engine.md` names six profiles but supplies only prose summaries.
It says status matrices will be constants without defining valid targets, required statuses,
trace descendants, evidence, ambiguity/finding/deferral rules, revision rules, or verdict
predicates. ST-12 therefore has no independent oracle.

**Impact:** Different implementations can enforce different gates while all claiming conformance;
the implementation would become the specification.

**Options:**

- **A — Normative matrices (recommended):** Specify every gate's valid targets, closure relations,
  node-status/evidence predicates, blocker handling, revision requirements, and verdict; derive
  direct cases from each row.
- **B — Formal predicates:** Define equivalent normative pseudocode per gate and test each branch.

Leaving the behavior to implementation constants is not viable.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged; strongest counterargument is that constants could
be added during coding, but that prevents specification-first tests.
**User Decision:** Resolved — user accepted Option A.

### PF-002 — 🟠 MAJOR — Governing G2 specifications gate is omitted

**Dimensions:** Contradictions, Completeness, Ordering, Codebase Alignment

**Problem:** The plan says the codex-port G1–G6 workflow remains governing, but its profile list
omits G2 “Specifications complete” and jumps from requirements to plan. The governing
`plans/codex-port/03-02-workflow-and-gates.md` defines distinct G2 interface, invariant,
acceptance, and domain-review evidence.

**Impact:** Schema 2 could weaken specification independence by making specification readiness
neither independently provable nor invalidatable.

**Options:**

- **A — Restore `specifications` gate (recommended):** Add it between requirements and plan and
  make plan readiness depend on its successful evidence.
- **B — Requirements subprofiles:** Retain one public gate name but model independently durable
  `requirements` and `specifications` stages.

Silently folding G2 into plan readiness is not viable under the governing program.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-003 — 🟠 MAJOR — Several declared targets and audit readiness are unrepresentable

**Dimensions:** Ambiguities, Completeness, Dependencies, Codebase Alignment

**Problem:** Profiles accept requirement sets, task plans, feature aggregates, and exact preflight
artifacts, while schema 2 adds only contract, planning-group, plan, and release nodes. Canonical
identity requires `<feature>/<node-id>`, but the feature field is currently a namespace, not a node,
and no audit gate is defined.

**Impact:** Implementers must invent identities/membership or fall back to directories and paths,
contradicting AR-5.

**Options:**

- **A — Explicit aggregate/audit model (recommended):** Add requirement-set and feature aggregate
  target types, use `plan` consistently for task plans, and define an `audit` profile for graph
  artifacts. Ad-hoc paths remain semantic-only when no graph node exists.
- **B — Normative virtual targets:** Specify canonical virtual syntax, membership derivation,
  revision, lifecycle ownership, and compatibility for every aggregate.
- **C — Narrow initial release:** Remove unsupported targets/workflows until a later schema.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-004 — 🟠 MAJOR — Semantic revision and snapshot contract is incomplete

**Dimensions:** Ambiguities, Data/State Completeness, Testability, Migration, Codebase Alignment

**Problem:** The plan requires deterministic semantic digests and validation snapshots but defines
no persisted source descriptor, selector rules, snapshot shape, normalization, algorithm/version,
multi-file ordering, moved/missing-source behavior, or handling for multiple nodes in one Markdown
file.

**Impact:** Formatting may create false invalidation, semantic changes may escape invalidation, and
different workflows/platforms can produce incompatible durable state.

**Options:**

- **A — Versioned digest contract (recommended):** Define source path plus stable semantic selector,
  canonical normalization/ordering, digest algorithm/version, and snapshots containing upstream
  canonical ID, relation, revision, and validation context.
- **B — Monotonic semantic revisions:** Authoring workflows explicitly increment revisions under
  a separate normative bump policy instead of hashing content.

The approved deterministic-digest baseline favors A.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-005 — 🟠 MAJOR — No deterministic atomic state-transition writer is planned

**Dimensions:** Completeness, Feasibility, Security, Failure Recovery

**Problem:** The specification requires status, revision, snapshots, and timestamps to change
atomically, but `codeops_state.py` is read-only today and no task builds a shared mutation
mechanism. Prompting each skill to edit JSON cannot guarantee the required invariant.

**Impact:** Interruptions or concurrent sessions can leave partially updated durable state that
either falsely claims readiness or becomes unrecoverable.

**Options:**

- **A — Shared transition library plus thin commands (recommended):** Validate expected old state,
  write a complete temp graph, flush, atomically replace, recover stale temp state, validate
  post-write, and expose purpose-specific approval/snapshot/stale/task transitions.
- **B — One generic transition CLI:** Provide the same transaction guarantees through a validated
  declarative mutation request.

Manual independent skill edits are not viable.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged; exact durability calls may be platform-bounded,
but same-file atomic replacement and stale-writer detection are mandatory.
**User Decision:** Resolved — user accepted Option A.

### PF-006 — 🟠 MAJOR — Target lifecycle/status command contract is missing

**Dimensions:** Completeness, Dependencies, Testability, Codebase Alignment

**Problem:** Roadmap and workflow specs require per-target status and lifecycle transitions, but
the only new command contract covers `readiness`. Phase 4 depends on a Phase-2 capability that no
ST case or task defines.

**Impact:** Roadmap may reimplement gate logic, and workflows may invent incompatible mutation and
status interfaces.

**Options:**

- **A — Define target status and transition commands (recommended):** Specify target/gate flags,
  lifecycle output, JSON schema, exit semantics, and transition preconditions in the deterministic
  core before roadmap integration.
- **B — Library-only API:** Let skills/scripts call one shared Python API, with an equally explicit
  contract and black-box harness.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Challenger converged that status/mutation and migration need separate contracts.
**User Decision:** Resolved — user accepted Option A.

### PF-007 — 🟠 MAJOR — Traceability graph upgrade protocol has no executable interface

**Dimensions:** Ambiguities, Completeness, Feasibility, Security, Migration

**Problem:** Preview, resolution collection, atomic apply, recovery, validation, and idempotence are
required, but the plan defines no command, flags, feature selection, resolution-file schema, preview
schema, exit codes, backup disposition, interruption recovery, or JSON/human output. “Schema 2”
also risks confusion with the unchanged Markdown `CodeOps Artifact Schema: 1`.

**Impact:** `upgrade-plan` cannot integrate deterministically; implementations can produce
incompatible migrations and unsafe recovery behavior.

**Options:**

- **A — State-engine graph-upgrade subcommand (recommended):** Specify
  `traceability-upgrade` preview/apply forms, versioned resolution/preview schemas, output location,
  exit codes, recovery lifecycle, and idempotent rerun behavior.
- **B — Separate standard-library upgrader:** Give a dedicated script the same complete contract,
  keeping the state CLI read-only.

Both must call this “traceability graph schema 2,” while Markdown artifact schema remains 1.

**Recommendation:** Option A, unless modularization under PF-011 makes B the cleaner thin entry
point.
**Confidence:** High.
**Hardening:** Challenger converged but identified modular placement as coupled to PF-011.
**User Decision:** Resolved — user accepted Option A, with modular placement reconciled under PF-011.

### PF-008 — 🟠 MAJOR — Schema-1 compatibility tests occur after risky rewrites

**Dimensions:** Ordering, Testability, Compatibility

**Problem:** Phases 1 and 2 rewrite parsing, selection, traversal, diagnostics, and output before
Phase 3 authors ST-25 schema-1 characterization. Existing tests do not freeze all promised
validate/readiness/status exit codes and human/JSON output.

**Impact:** Legacy semantics can regress before their independent oracle exists, violating the
plan's specification-first compatibility promise.

**Options:**

- **A — Move characterization to Phase 1 (recommended):** Freeze exact schema-1 behavior before
  task 1.2.2 and run the suite in every phase; retain migration-specific ST-26/27 in Phase 3.
- **B — Expand existing tests first:** Make `test_state.py` the explicit compatibility oracle
  before any production edit.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-009 — 🟠 MAJOR — Planned Python test modules are not discoverable

**Dimensions:** Implicit Assumptions, Testability, Codebase Alignment

**Problem:** The plan names files such as `test_state_v2.spec.test.py`. The authoritative runner is
`python3 -m unittest discover -s tests/conformance -p 'test_*.py'`. A direct isolated proof with
that dotted form ran zero tests.

**Impact:** Red/green proofs and final verification can falsely pass while every new test is skipped.

**Options:**

- **A — Importable underscore modules (recommended):** Use names such as
  `test_state_v2_spec.py` and `test_state_v2_impl.py`, plus an assertion that declared suites/ST
  cases are collected.
- **B — Existing module:** Put separated spec/implementation test classes into importable existing
  modules.

Changing test frameworks or invoking files ad hoc is not justified.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent auditor reproduced the failure; challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-010 — 🟠 MAJOR — Graph discovery ingests repository test fixtures as live state

**Dimensions:** Implicit Assumptions, Dependencies, Test Impact, Codebase Alignment

**Problem:** `discover_graphs()` recursively loads every `traceability.json` except a short ignored
directory list. Root readiness currently loads valid and invalid fixture graphs and sees duplicate
`ledger` identities. The plan adds six more fixture trees while preserving duplicate canonical IDs
as global blockers.

**Impact:** CodeOps cannot truthfully preflight its own repository; additional fixtures worsen
global collisions before target scoping can operate.

**Options:**

- **A — Artifact-root-aware discovery (recommended):** Discover only configured/conventional live
  artifact roots; explicitly exclude fixture roots. Fixture tests pass their fixture directory as
  `--root`.
- **B — Explicit graph roots:** Accept repeatable graph-root inputs and stop broad recursive
  discovery.

Scoped diagnostics alone cannot solve duplicate global identities.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Current root failure was reproduced; challenger converged.
**User Decision:** Resolved — user accepted Option A.

### PF-011 — 🟠 MAJOR — Engine architecture and tasks violate plan granularity

**Dimensions:** Feasibility, Scope, Ordering, Maintainability

**Problem:** `scripts/codeops_state.py` is already roughly 466 lines. The plan assigns versioned
schema parsing, identity, relation validation, group contraction, closure, gates, rendering,
migration, transactions, and revisions to large single-file tasks. This will exceed the planning
checklist's ~700-line and 200+/three-concern split thresholds.

**Impact:** Tasks are not reviewable 2–4-hour changes, independent verification is weak, and one
module becomes the owner of unrelated concerns.

**Options:**

- **A — Thin CLI plus focused modules (recommended):** Split models/schema, discovery/identity,
  closure/gates, transitions/revisions, migration, and rendering, with one-concern tasks.
- **B — Two-layer split:** Keep fewer modules but separate read-only graph evaluation from mutation
  and migration.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Challenger converged; strongest counterargument is single-file distribution
simplicity, outweighed by the plan's own granularity invariant.
**User Decision:** Resolved — user accepted Option A.

### PF-012 — 🟠 MAJOR — Corrective work is disconnected from governing pilot gate

**Dimensions:** Dependencies, Ordering, Codebase Alignment

**Problem:** `AGENTS.md` makes `plans/codex-port/` governing until 1.0. Its only incomplete item,
6.8, is the real complex-project pilot and incorporation of findings. This correction arose from
that pilot behavior, but the new plan has no durable relationship or verified closeout task.

**Impact:** The new plan can claim completion while the authoritative program remains unresolved,
creating competing completion narratives and losing the pilot evidence.

**Options:**

- **A — Explicit corrective child and closeout (recommended):** Link this plan to 6.8, retain pilot
  evidence, rerun the affected milestone after implementation, and close 6.8 only when that
  evidence passes.
- **B — Separate owner:** Record a durable link stating that 6.8 remains owned by a later closeout
  plan and must not be inferred complete here.

**Recommendation:** Option A.
**Confidence:** Medium-high.
**Hardening:** Challenger retained major severity because the repository explicitly declares the
port program governing. The counterargument is that 6.8 could close later; Option B preserves that
choice if made explicit.
**User Decision:** Resolved — user accepted Option A.

### PF-013 — 🟡 MINOR — ST ownership ranges conflict

**Dimensions:** Consistency, Testability

**Problem:** `03-01` claims ST-14–16 even though ST-14 is scoped diagnostics and group cases are
ST-17/18. `03-02` omits cases its execution phase consumes. The testing strategy remains readable,
but ownership references disagree.

**Options:**

- **A — Single ST-to-owner mapping (recommended):** Assign one normative specification owner per ST
  and let execution tasks cite cases as consumers.
- **B — Correct ranges locally:** Reconcile every component's Testing Requirements manually.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent challenger converged.
**User Decision:** Resolved — user accepted Option A.

## Adversarial Closing Check

- The approved architecture remains sound; findings concern missing executable detail and
  repository integration, not a reason to return to feature-wide readiness.
- No external protocol or regulatory standard is claimed.
- A dissenting architecture expert would most likely challenge the durable digest/transaction
  complexity; PF-004 and PF-005 make those boundaries explicit rather than hiding them.
- Because this is a foundational state/migration design, a human architecture review remains
  advisable after fixes.

## Iteration 2 Verification

PF-002, PF-008, PF-009, PF-010, PF-011, and PF-012 verified fixed. Direct residuals for PF-001,
PF-003, PF-004, PF-006, and PF-013 were corrected under their already accepted decisions. PF-005
and PF-007 exposed the shared recovery-contract gap recorded as PF-015. No other new
critical/major defect was found.

### PF-014 — 🟠 MAJOR — Compatibility and fixture-discovery promises conflict

**Dimensions:** Contradictions, Compatibility, Testability

**Problem:** The revised plan freezes exact schema-1 repository-root behavior before shared
rewrites while also correcting repository-root discovery so test fixtures are no longer treated as
live graphs. Current schema-1 root behavior demonstrably includes those fixtures. ST-25 says
existing outcomes remain unchanged while ST-38 requires this outcome to change.

**Options:**

- **A — Explicit compatibility exception (recommended):** Preserve schema-1 validate/readiness/
  status semantics and output on isolated live/fixture roots, but classify repository fixture
  ingestion as a corrected discovery defect outside the compatibility envelope. ST-38 becomes the
  authorized delta.
- **B — Version-bound discovery:** Preserve broad discovery only for schema-1 commands and fix
  discovery only for schema 2.

Option B leaves CodeOps unable to truthfully inspect its own repository through schema 1.

**Recommendation:** Option A.
**Confidence:** High.
**Hardening:** Independent iteration-2 auditor reproduced the contradiction.
**User Decision:** Resolved — user accepted Option A.

### PF-015 — 🟠 MAJOR — Required recovery has no executable contract

**Dimensions:** Failure Recovery, Feasibility, Security, Ordering

**Problem:** The plan requires explicit stale-lock recovery and journaled roll-forward/rollback but
defines no recovery command/request/output contract or dedicated task. It also says upgrade exit 1
means no state changed, which is false if atomic replace succeeds and post-write validation then
fails unless rollback is guaranteed.

**Options:**

- **A — Explicit recovery contract (recommended):** Add `transition-recover` with operation/journal
  ID, expected hashes, explicit `roll-forward|rollback`, proof that the prior owner is absent,
  stale-lock disposition, backup collision/no-overwrite rules, post-replace rollback, stable
  output/exit states, direct ST cases, and Phase-3/4 tasks.
- **B — Single-graph-only first release:** Remove multi-graph transitions and every recovery claim
  beyond same-file atomic replacement; defer grouped/release mutations requiring journals.

**Recommendation:** Option A because planning groups, releases, and cross-feature invalidation need
durable multi-graph recovery.
**Confidence:** High.
**Hardening:** Independent iteration-2 auditor and challenger converged.
**User Decision:** Resolved — user accepted Option A.

## Final Convergence

Iteration 2 verified every accepted correction across the unchanged audit target and direct
dependency surface. Residual inconsistencies in audit-task mapping, projected approval,
test-collection range, and recovery exits were corrected under their accepted finding roots and
rechecked independently.

- PF-001–PF-015: resolved and verified.
- New unresolved findings: 0.
- Critical/major open findings: 0.
- Specification cases: ST-1–ST-49 with one authoritative ownership map.
- Execution plan: 51 tasks across five specification-first phases.
- Repository verification: all five AGENTS.md commands pass.
- Roadmap hook: inert because `plans/00-roadmap.md` does not exist.

The plan is ready for execution. Because it defines foundational durable-state and migration
behavior and was created/reviewed in one session, a fresh-session or human architecture review is
still recommended as additional assurance, not as a blocking gate.
