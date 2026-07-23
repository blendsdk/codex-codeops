# Authority Policy: Auto Design

> **Document**: 03-01-authority-policy.md
> **Parent**: [Index](00-index.md)

## Activation and precedence

The exact token `--auto-design` activates delegated technical authority for the current top-level
workflow and explicitly invoked nested CodeOps handoffs. It is not stored as a repository default.
Explicit user constraints and governing artifacts outrank auto-design choices. Nested calls
receive a downward-only context containing mode, root invocation ID, policy version, and allowed
decision classes. Children may narrow but never widen it; unsupported children fail closed. (AR-9)

## Eligible authority

CodeOps may decide algorithms, data structures, internal architecture, technical interfaces,
failure/recovery mechanisms, concurrency, persistence, migration, security mechanisms, testing,
performance engineering, and implementation sequencing when these do not redefine the product.
(AR-1, AR-6)

## Reserved authority

CodeOps must escalate product behavior, scope, priority, acceptance criteria, access/security
policy, data ownership/retention, legal/ethical/compliance or risk acceptance, financial exposure,
budget/deadline, paid-vendor commitments, public compatibility breaks, destructive migration,
credentials, spending, destructive/irreversible external actions, deployment/publication, external
communication, or equally defensible options that create materially different products. The flag
does not grant action permission. (AR-5, AR-6)

## Decision algorithm

1. Classify the decision as eligible or reserved.
2. Gather repository and domain evidence; identify governing constraints.
3. Generate viable options and at least one non-obvious alternative.
4. Score the survivors against correctness, safety, objective fit, maintainability, verifiability,
   performance obligations, compatibility, recovery, delivery risk, and evolution.
5. Run recommendation hardening; require a blind independent challenger for complex, sensitive,
   high-impact, or difficult-to-reverse choices.
6. Select one option only when it is defensible; otherwise research further or escalate.
7. Record authority, eligibility class/boundary rationale, objective, evidence, rejected
   alternatives, counterargument, confidence, policy version, root invocation ID, hardening result,
   and reopen triggers in the owning ambiguity/decision artifact.
8. Propagate the decision into requirements/specifications/tests/tasks and invalidate it visibly
   if later evidence breaks an assumption. (AR-3, AR-7, AR-8, AR-10, AR-11)

## Durable record

An auto-design AR resolution uses `Authority: AI — delegated by --auto-design` and contains the
chosen option, eligibility class/boundary rationale, objective, evidence, rejected viable
alternatives, strongest counterargument, confidence, policy version, root invocation ID,
hardening/challenger result when applicable, and concrete reopen triggers. It counts as resolved
for the Zero-Ambiguity Gate without falsely attributing the decision to the user. (AR-8)
