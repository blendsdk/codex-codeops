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

## Native Windows boundary

Windows command selection is host-native: PowerShell resolves Python 3.10 or newer and portable
Python owners perform the work. WSL may be installed, but a CodeOps process actually running in
WSL is unsupported and blocks before mutation; Git Bash is not a Windows runtime path. Durable
mutation support is limited to writable fixed local NTFS workspaces without reparse-backed path
components. These constraints define the supported native Windows mutation boundary; see
[installation](installation.md) for current release status, prerequisites, and verification commands.

## Delegated technical design

`--auto-design` lets CodeOps resolve eligible technical choices during `make-requirements`,
`make-plan`, `preflight`, and `exec-plan`. It is useful when domain depth or project complexity
makes repeated user selection counterproductive. CodeOps compares viable options for correctness,
safety, objective fit, maintainability, verification, performance, compatibility, recovery,
delivery risk, proportional complexity, and future evolution. Consequential decisions retain an
auditable record and high-impact decisions require an independent challenger.

The delegation is deliberately narrow. Product behavior and scope, acceptance criteria,
security/access policy, legal or financial risk, destructive migration, credentials, spending,
publication, deployment, external communication, and materially different product directions
remain user-owned. Auto-design does not authorize implementation, scope expansion, commits,
pushes, or deployment. Child workflows may inherit less authority, never more; unsupported
children fail closed.

## Scope expansion control

Strict scope is the default for planning, preflight, and execution. Reviewers close defects,
security obligations, failure modes, and edge cases required by the confirmed behavior, but do not
report optional adjacent functionality. A correction is necessary only when grounded evidence
shows the requested behavior cannot otherwise be correct, safe, or feasible; unresolved material
risk blocks for investigation instead of being hidden or promoted automatically.

`--explore-scope` enables optional proposal discovery for one invocation. Proposals receive stable
`SE-*` identifiers and explicit `Keep`, `Defer`, or `Discard` decisions. `Keep` is the only state
that authorizes requirements, specifications, tests, or executable tasks. Deferred and discarded
entries remain durable, non-executable context across resumed sessions. Reversing `Keep` invalidates
only causally derived downstream state and requires an explicitly authorized safe remediation.

Scope exploration and `--auto-design` are orthogonal. Auto-design may choose technical details
inside scope that the user already kept, but it cannot choose `Keep` or activate exploration.

## Project tracking

Tracking combines lifecycle—discovery through archive—with readiness, task progress, verification, findings, blockers, dependencies, and deferrals. A new thread can reconstruct the next safe action from repository and Git evidence.

## Agents

Subagents isolate reconnaissance, implementation, specification-test authoring, or independent review. Complete dispatch packets are the correctness baseline; project-local TOML agents are optional optimizations. Missing agents never lower a gate.
