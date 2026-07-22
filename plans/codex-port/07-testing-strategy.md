# Testing and Evaluation Strategy

## Test principle

The port is accepted through observed behavior, not file similarity. Every critical capability requires both deterministic conformance tests and end-to-end agent scenarios.

## Test layers

### T1 — Static conformance

- Codex plugin manifest validation
- Marketplace schema and path validation
- Skill metadata and progressive-reference validation
- Hook schema and command-path validation
- No unapproved Claude runtime paths or model names
- Documentation link and example validation

### T2 — Artifact engine

- Identifier uniqueness
- Bidirectional traceability
- Orphan and conflict detection
- Gate invalidation propagation
- Readiness calculation
- Progress state transitions
- Roadmap derivation and drift reporting
- Archive and migration idempotency
- Malicious/path-traversal fixture handling

### T3 — Hook fixtures

Capture real Codex payloads for:

- startup, resume, clear, and compact;
- `apply_patch` and shell tool calls;
- subagent start/stop and agent tool completion;
- blocked/rewritten tool actions where supported; and
- plugin data/root variables.

No Claude payload fixture may be treated as proof of Codex compatibility.

### T4 — Skill behavior

For each core skill, evaluate:

- explicit invocation;
- natural-language invocation;
- correct non-invocation on adjacent tasks;
- reference loading;
- interruption/resumption;
- ambiguity handling;
- authorization boundaries; and
- output/artifact schema.

### T5 — Adversarial workflow scenarios

#### Compiler scenario

Design a language feature involving grammar, name resolution, type inference, diagnostics, IR lowering, and compatibility. Seed contradictions and missing cyclic/edge-case semantics. Pass only if CodeOps discovers them before implementation planning and traces the resolutions into tests and tasks.

#### Financial scenario

Design a multi-currency ledger operation involving idempotency, rounding, atomicity, reconciliation, authorization, audit, retries, and partial failure. Pass only if financial invariants and failure semantics are explicit and independently reviewed.

#### Web application scenario

Design a multi-tenant workflow involving roles, API contracts, persistence, background jobs, caching, accessibility, observability, and deployment. Pass only if cross-tenant and state-transition ambiguities are closed.

### T6 — Execution and recovery

- Interrupt before implementation, during implementation, during verify, after verify, and during review.
- Resume in a new conversation with no transcript context.
- Introduce a dirty worktree and unplanned changes.
- Fail specification tests and attempt to weaken them.
- Discover an upstream ambiguity during implementation.
- Make a reviewer unavailable.
- Exhaust subagent capacity.

Pass only if the next safe action is reconstructed and no gate is silently bypassed.

### T7 — Comparative parity

Run matched scenarios through Claude CodeOps 3.12.0 and Codex CodeOps. Compare:

- material ambiguities found before execution;
- contradictions and traceability gaps found;
- acceptance/test coverage;
- unsafe assumptions;
- recovery accuracy;
- verified completion rate;
- escaped critical/major review findings;
- user decision burden; and
- context/token cost as a secondary metric.

Codex passes when it is no worse on safety/correctness dimensions and materially improves at least traceability, recovery, or redundant-user-effort dimensions.

## Release gates

| Release | Required evidence |
|---|---|
| Developer preview | Valid plugin, core skills load, artifact validator works, one complete scenario passes. |
| Alpha | Requirements→plan→execute loop works; roadmap and recovery work; all three domain scenarios pass internally. |
| Beta | Comparative parity suite passes; installation and hooks verified on declared surfaces; migration tested on copies of real projects. |
| 1.0 | All critical requirements pass, no unresolved critical port ambiguity, documentation complete, and at least one real complex project completes a meaningful milestone. |

