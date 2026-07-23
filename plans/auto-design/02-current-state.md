# Current State: Auto Design

> **Document**: 02-current-state.md
> **Parent**: [Index](00-index.md)

## Existing Implementation

CodeOps already centralizes zero-ambiguity and recommendation hardening in `_shared/`. Requirements
and planning prohibit AI-owned material decisions, while preflight and execution pause for user
rulings. This is safe for informed operators but becomes ceremonial when the operator lacks the
domain expertise needed to evaluate specialist technical options.

## Relevant Files

| File | Current role | Required change |
|---|---|---|
| `_shared/zero-ambiguity-gate.md` | Explicit user decision invariant | Define delegated authority compatibility |
| `_shared/recommendation-hardening.md` | Best-option search and challenge | Supply the selection machinery |
| `_shared/auto-design.md` | Absent | Add the single normative policy |
| `skills/make-requirements/SKILL.md` | Requirements decisions | Recognize and propagate the mode |
| `skills/make-plan/SKILL.md` | Design decisions | Resolve eligible ARs autonomously |
| `skills/preflight/SKILL.md` | Finding rulings | Select and apply eligible remediations |
| `skills/exec-plan/SKILL.md` | Runtime ambiguity rulings | Resolve eligible technical blockers |
| `scripts/validate-codex.sh` | Static contracts | Add deterministic policy assertions |
| `tests/conformance/` | Behavioral contracts | Add flag, provenance, boundary, and compatibility cases |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| “Best” becomes subjective model preference | Wrong architecture with false confidence | Objective rubric, evidence, counterargument, challenger |
| Flag silently broadens action permissions | External or destructive side effects | Explicit orthogonality invariant and tests |
| Skills drift into inconsistent semantics | Unpredictable authority | One shared owner plus static conformance |
| Delegation hides uncertainty | Unreviewable failure | Confidence and reopen triggers; bounded escalation |
| Existing strict behavior regresses | Backward incompatibility | Absence-of-flag characterization |
