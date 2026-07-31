# Task T-01: Scope Expansion Control

> **Type**: Task (lightweight) · **CodeOps Artifact Schema**: 1
> **Last Updated**: 2026-07-31 23:14
> **Progress**: 3/3 tasks (100%)
> **Phase baseline tree**: c43f77d8d99cd6b0ebd119636d092e36848de9a4

## Objective

Keep CodeOps strictly within user-authorized product scope by default. When a workflow is invoked
with `--explore-scope`, let it present optional additions as stable `SE-*` proposals while leaving
acceptance, deferral, or discard decisions with the user. Always report evidence that the requested
behavior itself cannot be correct, safe, or feasible.

A correction is necessary only when grounded causal evidence shows that omitting the smallest
correction makes the explicitly requested behavior incorrect, unsafe, or infeasible and no
compliant solution exists inside the authorized scope. A credible unresolved material risk blocks
for investigation. Speculative benefits are optional and silent in strict mode.

## Scope

- **Target**: shared scope-expansion policy and its `make-plan`, `preflight`, and `exec-plan`
  integrations.
- **Context**: existing ambiguity, auto-design, finding, traceability, and quality-review contracts.
- **Modification set**: `_shared/scope-expansion-control.md`, `_shared/auto-design.md`,
  `_shared/quality-profile.md`, `_shared/layout-convention.md`, `skills/make-plan/SKILL.md`,
  `skills/make-plan/quality-checklist.md`, `skills/preflight/SKILL.md`,
  `skills/preflight/dimensions.md`, `skills/preflight/report-format.md`,
  `skills/exec-plan/SKILL.md`, `skills/exec-plan/execution-protocol.md`,
  `agent-templates/plan-task-executor.md`, `agent-templates/plan-task-executor-opus.md`,
  `agent-templates/preflight-auditor.md`, `agent-templates/phase-reviewer.md`,
  `tests/conformance/test_scope_expansion_control_spec.py`,
  `tests/conformance/test_scope_expansion_control_impl.py`, `scripts/validate-codex.sh`,
  `README.md`, `docs/concepts.md`, `docs/tutorial.md`, and `CHANGELOG.md`.
- **Excluded**: requirements discovery, traceability schema changes, automatic expansion approval,
  GitHub issue mutation, and unrelated workflow redesign.

Any newly discovered file is context-only until execution pauses and the user explicitly adds its
exact path to this modification set.

## Scope-Expansion Lifecycle

When exploration finds at least one optional addition, the governed target owns a collision-free,
target-qualified register at the path defined by `_shared/layout-convention.md`. IDs are local to
that register, monotonic, and never reused. Each `SE-*` entry append-preserves its history across
`Keep`, `Defer`, `Discard`, and `Superseded` decisions. Only `Keep` may produce executable work.

`Defer` records a named owner and observable revisit trigger. It stays dormant and non-executable
on ordinary resume and is re-presented under the same ID only when unambiguous trigger evidence
exists or the user explicitly requests reconsideration; re-presentation never implies `Keep`.
Reviving `Discard` requires new evidence and renewed explicit authority.

Reversing `Keep` stops affected execution, marks every dependency-traced downstream specification,
test, task, implementation, and verification stale, and supersedes pending or in-progress derived
tasks. Historical evidence remains intact. Readiness resumes only after the user authorizes a safe
removal or remediation; CodeOps never auto-reverts irreversible or externally applied work.

## Tasks

- [x] T-01.1 Write specification tests for strict default scope, exact `--explore-scope` parsing,
  necessary-correction reporting, user-owned `SE-*` decisions, resume behavior, and interaction
  with `--auto-design`; confirm the expanded specification module is red. Reopened after preflight;
  the earlier seven-case red result remains historical evidence. ✅ (completed: 2026-07-31 21:55; 10 expanded specification cases red)
- [x] T-01.2 Implement the shared protocol and integrate it into planning, preflight, and execution;
  confirm the specification module is green. ✅ (completed: 2026-07-31 22:00; 10 specification cases green)
- [x] T-01.3 Add `tests/conformance/test_scope_expansion_control_impl.py`, deterministic assertions
  in `scripts/validate-codex.sh`, user documentation in `README.md`, `docs/concepts.md`, and
  `docs/tutorial.md`, release notes in `CHANGELOG.md`, and pass the complete repository verification
  suite. ✅ (completed: 2026-07-31 22:03; all five repository gates passed)

After T-01.3 verifies, the exec-plan post-task quality gate owns the independent whole-task review,
accepted-fix verification, and the single required re-review for any blocking fix.

## Post-Task Quality Review

> **Status**: ✅ COMPLETE — review findings resolved and final verification passed
> **Review-fix baseline tree**: eb83a0817fb50d9ea6caa326077eac7909a10092

| ID | Severity | Finding | Recommendation | User ruling |
|---|---|---|---|---|
| RV-001 | Major | `<document-stem>` collides for equal-stem files and omits ad-hoc directory targets. | Use the complete target filename for file/document registers and a register inside an ad-hoc target directory; define target type and normalized path in the register header. | Accepted by user; exact collision-free mapping selected under `--auto-design` |
| RV-002 | Major | One mutable decision cell cannot preserve lifecycle events, triggers, provenance, or derived authority links. | Define current-state, append-only decision-event, and derived-link tables; keep implementation linkage in traceability/artifact evidence, never source comments. | Accepted by user; append-only event model selected under `--auto-design` |
| RV-003 | Major | Green tests mostly assert token presence rather than hostile parsing, path collisions, and state transitions. | Add table-driven activation cases plus parsed path and lifecycle contract cases without changing the accepted specification expectations. | Accepted by user; test-oracle defect correction explicitly authorized |
| RV-004 | Minor | Executor packets promise scope context but the authoritative packet list and executor template omit it. | Add `agent-templates/plan-task-executor.md` to the exact modification set and give executors scope mode, baseline, and strict fail-closed handling. | Accepted by user; path added to modification set |

### Fix-scoped re-review

The one permitted re-review found that the first fix set still tested test-local algorithms, omitted
the high-sensitivity executor variant, and left event ordering implicit.

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| RV-003-R1 | Major | Activation and register-path cases exercised test-local algorithm copies instead of parsing the shipped contracts. | Fixed under `--auto-design`: tests now parse the normative activation and layout tables plus each workflow's activation section. |
| RV-004-R1 | Major | `agent-templates/plan-task-executor-opus.md` lacks the general executor scope packet and fail-closed rules. | Fixed after explicit user authorization: both executor variants receive scope mode, baseline, and fail-closed rules. |
| RV-005-R1 | Minor | `SEV-*` allocation and event ordering were undefined. | Fixed under `--auto-design`: IDs are register-local, monotonic, never reused, and append order determines current state. |

The quality policy permits only one fix-scoped re-review. After that review, all reported findings
were fixed, the user explicitly authorized the newly required executor path, and the complete five-gate
repository verification passed. No second re-review was performed.

**Verify**:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```
