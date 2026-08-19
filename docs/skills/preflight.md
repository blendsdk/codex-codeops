# `preflight`

Use `preflight` as an adversarial review gate for requirements, plans, specifications, or another
named artifact. It verifies claims against the codebase and scans thirteen dimensions including
completeness, consistency, security, data integrity, failure behavior, compatibility, testing, and
operability.

```text
Use preflight on the invoice-reconciliation plan.
```

## Findings

Findings have stable identities, severity, evidence, impact, viable resolution options, and a
recommendation. Critical and major findings block a passing gate until resolved or handled under
the workflow's explicit authority rules. Preflight never silently fixes the artifact it audits.

## Controls

```text
Use preflight --continue.
Use preflight --auto-design on the plan.
Use preflight --explore-scope on the requirements.
```

Resume mode checks whether the source changed before continuing. Auto-design may select eligible
technical remediations when action authority already exists, but it cannot waive risk. Scope
exploration records optional additions separately from audit findings.
