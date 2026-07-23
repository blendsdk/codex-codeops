# CodeOps concepts

## Recursive ambiguity closure

CodeOps does not ask one round of questions and call the result a specification. Requirements, component specifications, testing strategies, and execution plans each receive their own ambiguity pass. A later discovery can reopen an earlier gate and invalidate downstream readiness.

## Material ambiguity

An ambiguity is material when plausible answers can change behavior, semantics, data integrity, security, financial results, contracts, persistence, concurrency, recovery, compatibility, performance obligations, tests, architecture, operations, scope, or ordering. Material choices require explicit resolution or an approved, risk-recorded deferral.

## Durable artifacts

Markdown owns human-readable requirements, decisions, specifications, tests, and plans. `traceability.json` owns stable typed relationships and state. Roadmaps are derived views. Conversations are useful context but never durable workflow state.

## Readiness

The deterministic state tool validates identifiers, paths, relationships, status, and coverage shape. Semantic review validates truth, completeness, consistency, feasibility, and risk. Both must pass.

Readiness is target-scoped. A workflow selects one canonical node or group and one gate profile;
the engine computes its dependency closure and shortest blocker paths. Closure is read context,
not permission to edit or advance siblings. Feature and release nodes are explicit aggregates,
and a release contains only declared members.

Schema 2 binds semantic sources to normalized revisions and stores relationship snapshots.
Changing upstream meaning therefore makes affected downstream claims stale. Legal lifecycle
changes are atomic compare-and-swap transitions with recovery evidence.

## Project tracking

Tracking combines lifecycle—discovery through archive—with readiness, task progress, verification, findings, blockers, dependencies, and deferrals. A new thread can reconstruct the next safe action from repository and Git evidence.

## Agents

Subagents isolate reconnaissance, implementation, specification-test authoring, or independent review. Complete dispatch packets are the correctness baseline; project-local TOML agents are optional optimizations. Missing agents never lower a gate.
