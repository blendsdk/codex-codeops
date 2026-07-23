# Current State: Dependency-Aware Readiness

> **Document**: 02-current-state.md
> **Parent**: [Index](00-index.md)

## Existing Implementation

### What Exists

`scripts/codeops_state.py` discovers per-feature traceability graphs, validates schema-1 nodes and
string links, checks bidirectional coverage by node type, detects ambiguity-driven stale state,
derives feature lifecycle, and emits human or JSON status. `--feature` narrows readiness to one
feature graph.

The schema, fixtures, state tests, workflow skills, roadmap behavior, upgrade guidance, and port
program already establish deterministic state as the source for semantic workflows. The current
implementation therefore supplies a sound base but lacks the relationship semantics required for
safe target closure.

### Relevant Files

| File | Purpose | Changes Needed |
|---|---|---|
| `scripts/codeops_state.py` | Graph loading, validation, readiness, status | Add versioned models, target resolution, typed traversal, profiles, releases, revisions |
| `scripts/codeops_state_lib/` | New focused deterministic modules | Separate schema, discovery, closure, gates, revisions, transitions, migration, and rendering |
| `schemas/traceability.schema.json` | Schema-1 contract | Preserve schema 1 and add an explicit schema-2 contract |
| `tests/conformance/test_state.py` | State-engine conformance | Add schema-2 specification and implementation tests |
| `tests/fixtures/state-*` | Durable graph examples | Retain v1; add ERP, compiler, migration, release, and hostile v2 fixtures |
| `references/artifacts/traceability.md` | Human contract | Document canonical schema-2 semantics |
| `skills/*` | Lifecycle workflows | Select exact target/gate and respect closure scope |
| `scripts/validate-codex.sh` | Deterministic product contract | Assert targeted workflow integration |
| `docs/*` | User guidance | Explain authoring, upgrading, diagnostics, and releases |

### Code Analysis

- Node validation accepts only a closed schema-1 node shape with string `links`.
- Coverage treats links as effectively undirected by combining outgoing and incoming references.
- Ambiguity invalidation follows outgoing links, giving the same field two incompatible meanings.
- `readiness()` applies one rule set to all nodes in the selected feature.
- Global discovery and relationship validation occur before feature selection, so unrelated broken
  graphs can contaminate a targeted check.
- Repository-root discovery currently ingests deliberately invalid test fixtures as live state.
- The current 466-line engine cannot absorb schema, migration, transactions, and rendering without
  violating the plan's module-size and task-granularity constraints.
- Workflows call either portfolio-wide or feature-wide readiness; none provides artifact identity
  or lifecycle gate.

## Gaps Identified

### Gap 1: Relationship semantics

**Current Behavior:** String links identify association but not direction, ownership, dependency,
contract consumption, or release coupling.

**Required Behavior:** `03-01-graph-schema.md` defines one canonical meaning per stored edge.

### Gap 2: Gate scope

**Current Behavior:** Every content node in the selected feature must be approved.

**Required Behavior:** `03-02-readiness-engine.md` computes a gate-specific target closure.

### Gap 3: Durable change identity

**Current Behavior:** Only reopened ambiguities trigger stale validation.

**Required Behavior:** `03-03-migration-and-invalidation.md` defines semantic revisions and
validation snapshots.

### Gap 4: Workflow handoff

**Current Behavior:** Narrow preflight, plan, and execution requests invoke broader readiness.

**Required Behavior:** `03-04-workflow-integration.md` maps every workflow to a target and gate.

## Dependencies

### Internal Dependencies

- The codex-port architecture and G1–G6 lifecycle definitions remain governing.
- Layout, zero-ambiguity, specification-first, quality-profile, and roadmap contracts remain
  authoritative.
- Schema-2 rollout depends on deterministic engine support before skills may require it.

### External Dependencies

None. The implementation remains Python standard-library plus repository shell validation.

## Risks and Concerns

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Relationship vocabulary becomes ambiguous | Medium | High | Closed enums, source/target matrices, specification fixtures |
| Target closure omits a true blocker | Medium | Critical | Gate-profile tables, dependency-path tests, adversarial fixtures |
| Migration invents legacy semantics | Medium | High | Preview and unresolved conversion records; never infer |
| Schema-1 regression | Medium | High | Preserve v1 fixtures and exact legacy path |
| Invalidation cascades too broadly | Medium | High | Revision snapshots and relation-specific propagation |
| Cross-feature corruption hides a blocker | Low | Critical | Validate all graphs entering closure and global canonical identity |
| Workflow docs drift from CLI | Medium | High | Static contract assertions plus documentation checks |
