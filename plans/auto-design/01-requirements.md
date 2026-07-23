# Requirements: Auto Design

> **Document**: 01-requirements.md
> **Parent**: [Index](00-index.md)

## Functional Requirements

1. Every supported workflow shall recognize invocation-scoped `--auto-design` without changing
   behavior when the flag is absent. (AR-4, AR-9)
2. The mode shall autonomously resolve eligible technical ambiguities using a documented,
   quality-first rubric rather than sophistication or effort alone. (AR-1–AR-3)
3. Every automatic decision shall be durable, attributable, evidence-grounded, and reopenable.
   (AR-7, AR-8, AR-11)
4. Reserved product and consequential external authority shall still escalate to the user.
   (AR-5, AR-6, AR-10)
5. The mode shall preserve zero-ambiguity, readiness, specification-first, verification, review,
   and lifecycle invalidation gates. (AR-7, AR-11)
6. Nested workflow handoffs shall propagate the active mode explicitly for the current workflow
   chain and shall not persist it as a project default. (AR-9)

## Non-Functional Requirements

- Existing invocations and artifacts remain compatible.
- The shared policy has one authoritative owner; skills cite it rather than restating it.
- Deterministic validation detects missing integration, unsafe permission coupling, and weakened
  gate language.
- Automatic decisions use bounded challenger/research effort and converge or escalate cleanly.

## Out of Scope

- Automatic deployment, publication, spending, credentials, destructive operations, or external
  communication.
- A global or project-persistent default.
- Claims that the model is infallible or that “best” is mathematically provable.
- Replacing user-authored product goals.

## Acceptance Criteria

1. Supported skills share one normative authority policy.
2. Normal mode retains explicit-user-decision behavior.
3. Auto-design mode records complete delegated-decision provenance.
4. Reserved authority and insufficient evidence stop with a focused escalation.
5. All five repository verification commands pass.
