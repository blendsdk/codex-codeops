# Execution Plan: Auto Design

> **Document**: 99-execution-plan.md
> **Parent**: [Index](00-index.md)
> **Last Updated**: 2026-07-23 18:15
> **Progress**: 12/12 tasks (100%)
> **CodeOps Artifact Schema**: 1

## Overview

Implement the shared delegated technical-authority policy and integrate it without weakening
normal mode, quality gates, or action permissions.

**🚨 Update this document after EACH completed task!**

## Implementation Phases

| Phase | Title | Tasks |
|---|---|---:|
| 1 | Normative policy and specification oracle | 4 |
| 2 | Workflow integration | 4 |
| 3 | Hardening, documentation, and release | 4 |

**Total: 12 tasks across 3 phases**

> **⚠️ EXECUTION RULE — APPLIES TO EVERY AGENT EXECUTING THIS PLAN:**
>
> Mark implementation `[~]` with an implementation timestamp, promote to `[x]` only after
> verification, and update Progress and Last Updated after every task. Resume `[~]` before `[ ]`.

## Phase 1: Normative Policy and Specification Oracle

> **Phase baseline tree**: `091e88a3b441f120432c8d187f4aa2e2466b62c0`

- [x] 1.1.1 [spec-author] Write ST-1–ST-9 specification tests — `tests/conformance/test_auto_design_spec.py` ✅ (completed: 2026-07-23 17:49)
- [x] 1.1.2 Run the new specification module red while existing conformance remains green ✅ (completed: 2026-07-23 17:49; 9 expected failures/errors, 108 existing state cases green)
- [x] 1.2.1 Implement the shared authority, selection, provenance, escalation, propagation, and permission policy — `_shared/auto-design.md`, `_shared/zero-ambiguity-gate.md` ✅ (completed: 2026-07-23 17:51)
- [x] 1.2.2 Run policy-owned specification cases green, retaining the workflow-integration ST-2 red result for Phase 2 ✅ (completed: 2026-07-23 17:51; 8 policy cases green)

**Verify**: `python3 -m unittest tests.conformance.test_auto_design_spec`

## Phase 2: Workflow Integration

- [x] 2.1.1 Integrate exact flag parsing and normal-mode compatibility into requirements and planning — `skills/make-requirements/SKILL.md`, `skills/make-plan/SKILL.md` ✅ (completed: 2026-07-23 17:59)
- [x] 2.1.2 Integrate remediation and runtime-decision behavior without permission coupling — `skills/preflight/SKILL.md`, `skills/exec-plan/SKILL.md`, `skills/exec-plan/execution-protocol.md` ✅ (completed: 2026-07-23 17:59)
- [x] 2.1.3 Add deterministic integration assertions and collection coverage — `scripts/validate-codex.sh`, `tests/conformance/test_state_test_collection.py` ✅ (completed: 2026-07-23 17:59)
- [x] 2.1.4 Run all auto-design and existing conformance cases green ✅ (completed: 2026-07-23 18:04; 157 conformance cases green)

**Verify**: `./scripts/validate-codex.sh`

## Phase 3: Hardening, Documentation, and Release

- [x] 3.1.1 Add hostile arguments, nested propagation, reserved-authority, permission-orthogonality, and broken-link tests — `tests/conformance/test_auto_design_impl.py` ✅ (completed: 2026-07-23 18:04)
- [x] 3.1.2 Document usage, authority boundaries, and examples — `README.md`, `docs/concepts.md`, `docs/tutorial.md`, `CHANGELOG.md` ✅ (completed: 2026-07-23 18:04)
- [x] 3.1.3 Run independent correctness and authority-boundary review; resolve all critical/major findings once ✅ (completed: 2026-07-23 18:09; correctness and authority audits reconciled)
- [x] 3.1.4 Run all five repository gates, commit, push, apply the SemVer release rule, and reinstall ✅ (completed: 2026-07-23 18:15; 0.3.0 installed from public main; final tag pending verified evidence commit)

**Verify**:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

## Dependencies

```text
Policy oracle → shared policy → workflow integration → hardening → release
```

## Success Criteria

The feature is complete when normal mode is unchanged, auto-design decisions are strong and
auditable, reserved authority and action permissions remain protected, all links and tests pass,
and the installed plugin exposes the new option.
