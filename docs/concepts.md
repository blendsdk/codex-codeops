# CodeOps concepts

## Recursive ambiguity closure

CodeOps does not ask one round of questions and call the result a specification. Requirements, component specifications, testing strategies, and execution plans each receive their own ambiguity pass. A later discovery can reopen an earlier gate and block affected downstream tasks.

## Material ambiguity

An ambiguity is material when plausible answers can change behavior, semantics, data integrity, security, financial results, contracts, persistence, concurrency, recovery, compatibility, performance obligations, tests, architecture, operations, scope, or ordering. Material choices require explicit resolution or an approved, risk-recorded deferral.

## Durable artifacts

Markdown owns requirements, decisions, specifications, tests, plans, and progress. Requirements
documents own agreed behavior and acceptance criteria. A plan's `00-index.md` declares the RD or
RDs it implements. Its `99-execution-plan.md` is the only mutable task-progress authority.
Roadmaps and status output are derived views. Git supplies history and recovery.

## Readiness

Readiness is checked directly from artifacts: required documents exist, material ambiguities are
closed, specification tests precede implementation, and critical/major findings are resolved.
Semantic review validates truth, completeness, consistency, feasibility, and risk.

A plan has four derived states: `Ready`, `Executing`, `Done`, and `Blocked`. Tasks use `[ ]` for
not started, `[~]` for implemented with verification pending, `[x]` for verified, and `[!]` for
blocked with a visible reason. Resume selects the first `[~]` task, otherwise the first `[ ]`.
Only a passing verification permits `[~]` to become `[x]`.

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

## Complexity approval

CodeOps uses the smallest viable design as its baseline. A material new layer, dependency,
framework, test harness, support system, or infrastructure surface causes a visible stop. An
independent challenger compares it with the original goal and the smaller alternative. CodeOps
shows the reason, evidence, and added maintenance cost. The larger design remains blocked until the
user approves that specific machinery. `--auto-design` cannot approve it.

If unapproved complexity reaches preflight or phase review, it is at least a major finding. CodeOps
reuses its existing ambiguity and finding records; it does not create a separate complexity system.

## Operator communication

CodeOps uses plain international English in user-facing text. It prefers short sentences and common
words, defines uncommon technical terms, and avoids idioms or dense grammar. Exact commands and
technical identifiers stay unchanged.

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

Tracking combines lifecycle—discovery through archive—with derived plan progress, findings,
blockers, dependencies, and deferrals. A new thread reconstructs the next safe action from the
execution plan and Git evidence.

## Agents

Subagents isolate reconnaissance, implementation, specification-test authoring, or independent review. Complete dispatch packets are the correctness baseline; project-local TOML agents are optional optimizations. Missing agents never lower a gate.
