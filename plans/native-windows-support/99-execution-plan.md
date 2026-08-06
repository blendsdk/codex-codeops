# Execution Plan: Native Windows Support

> **Document**: 99-execution-plan.md
> **Parent**: [Index](00-index.md)
> **Last Updated**: 2026-08-06 17:09
> **Progress**: 0/72 tasks (0%)
> **CodeOps Artifact Schema**: 1

## Overview

Implement RD-022 and RD-023 through a native preflight, portable Python control layer, certified
Windows state/filesystem adapters, and evidence-gated release claim. GitHub issue #2 is resolved
in Phase 2; the broader umbrella issue closes only after Phase 5 evidence.

**🚨 Update this document after EACH completed task!**

## Implementation Phases

| Phase | Title | Tasks |
|---|---|---:|
| 1 | Native preflight and hook enforcement | 11 |
| 2 | Windows state, recovery, and filesystem safety | 13 |
| 3 | Portable utility control layer | 19 |
| 4 | Workflow integration and native verification | 17 |
| 5 | Windows certification and release claim | 12 |

**Total: 72 tasks across 5 phases**

> **⚠️ EXECUTION RULE — APPLIES TO EVERY AGENT EXECUTING THIS PLAN:**
>
> The task checkboxes below are the single source of truth. Every task appears exactly once.
> On implementation mark it `[~]` with `implemented: YYYY-MM-DD HH:MM`; on verification promote
> it to `[x]` with `completed: YYYY-MM-DD HH:MM`. Update Progress and Last Updated after every
> task. Resume the first `[~]`, otherwise the first `[ ]`. Obtain timestamps using
> `date '+%Y-%m-%d %H:%M'`.

## Phase 1: Native Preflight and Hook Enforcement

> **Phase baseline tree**: _(recorded by the exec-plan skill at phase start)_

### Step 1.1: Specification Tests

**Reference**: [03-01](03-01-runtime-preflight-and-hooks.md) · ST-1–ST-12, ST-28–ST-30 ·
AR-3–AR-7

- [ ] 1.1.1 [spec-author] Add bootstrap, prerequisite, status/exit, WSL, Python 3.x, sandbox, and attestation specification cases — `tests/conformance/test_windows_preflight_spec.py`
- [ ] 1.1.2 [spec-author] Add dual-host hook-manifest, path-with-spaces, mutation-order, and missing-trust specification cases — `tests/conformance/test_windows_preflight_spec.py`, `tests/fixtures/hooks/`
- [ ] 1.1.3 Run the new Phase-1 specification module, record expected red results, and prove every pre-existing conformance test remains green — `tests/conformance/test_windows_preflight_spec.py`

### Step 1.2: Implementation

**Reference**: [03-01 §Implementation Details](03-01-runtime-preflight-and-hooks.md#implementation-details)

- [ ] 1.2.1 Implement closed readiness/check result models, ordered rendering, modes, exit classes, and sanitized diagnostics — `scripts/codeops_windows_preflight.py`, `scripts/codeops_windows_lib/models.py`
- [ ] 1.2.2 Implement native/WSL, Windows version, Python, Git, Codex/sandbox, plugin/hook, workspace, and filesystem probes behind documented adapters — `scripts/codeops_windows_lib/probes.py`, `scripts/codeops_windows_preflight.py`
- [ ] 1.2.3 Implement session-attestation validation, containment, binding, expiry/refresh, and atomic storage — `scripts/codeops_windows_lib/attestation.py`, `scripts/codeops_windows_preflight.py`
- [ ] 1.2.4 Add the minimal PowerShell Python bootstrap with `py -3`/`python` probes and no shell-evaluated input — `scripts/codeops-windows-preflight.ps1`
- [ ] 1.2.5 Move hook behavior to the portable hook entry, add `commandWindows`, and retain thin Unix launchers — `scripts/codeops_hooks.py`, `hooks/hooks.json`, `scripts/hook_session_context.sh`
- [ ] 1.2.6 Complete marker-guard launcher extraction and run all Phase-1 specification cases green — `scripts/hook_marker_guard.sh`, `scripts/codeops_hooks.py`

### Step 1.3: Implementation Tests and Hardening

**Reference**: [03-01 §Error Handling](03-01-runtime-preflight-and-hooks.md#error-handling)

- [ ] 1.3.1 Add adapter, cache-binding, malformed-input, hostile-environment, command-injection, and path-containment implementation tests — `tests/conformance/test_windows_preflight_impl.py`
- [ ] 1.3.2 Run Phase-1 spec/implementation suites, hook validation, and the confirmed five-command full verification gate — `tests/conformance/test_hooks.py`, `scripts/validate-codex.sh`

**Verify**:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

## Phase 2: Windows State, Recovery, and Filesystem Safety

> **Phase baseline tree**: _(recorded by the exec-plan skill at phase start)_

### Step 2.1: Specification Tests

**Reference**: [03-03](03-03-state-and-filesystem-safety.md) · ST-13–ST-27, ST-37,
ST-41–ST-45 · AR-9–AR-11

- [ ] 2.1.1 [spec-author] Add versioned Windows/legacy Linux owner, absence, PID-reuse, uncertainty, concurrency, and recovery specification cases — `tests/conformance/test_windows_state_spec.py`
- [ ] 2.1.2 [spec-author] Add canonical/legacy/hostile path, reserved-name, atomic retry, exhaustion, interruption, and unsupported-filesystem specification cases — `tests/conformance/test_windows_state_spec.py`, `tests/fixtures/windows-state/`
- [ ] 2.1.3 Run new state specification cases red while the immutable Linux state and migration specification modules remain green — `tests/conformance/test_windows_state_spec.py`, `tests/conformance/test_state_migration_spec.py`

### Step 2.2: Implementation

**Reference**: [03-03 §Process Identity Contract](03-03-state-and-filesystem-safety.md#process-identity-contract) and [§Atomic Write Contract](03-03-state-and-filesystem-safety.md#atomic-write-contract)

- [ ] 2.2.1 Add versioned process identity models, backend protocol, and exact legacy-Linux record parser — `scripts/codeops_state_lib/processes.py`, `scripts/codeops_state_lib/models.py`
- [ ] 2.2.2 Move current `/proc` behavior behind the Linux backend without changing its absence decisions — `scripts/codeops_state_lib/processes.py`, `scripts/codeops_state_lib/transitions.py`
- [ ] 2.2.3 Implement least-privilege Windows process creation-time/host-epoch probing with guaranteed handle cleanup and fail-closed uncertainty — `scripts/codeops_state_lib/processes_windows.py`, `scripts/codeops_state_lib/processes.py`
- [ ] 2.2.4 Implement canonical durable path serialization, safe legacy Windows reads, containment, and platform-invalid component rejection — `scripts/codeops_state_lib/paths.py`
- [ ] 2.2.5 Implement shared same-directory atomic writes and bounded allowlisted Windows replace retries without delete fallback — `scripts/codeops_state_lib/filesystem.py`
- [ ] 2.2.6 Integrate process/filesystem adapters into transition, journal, lock, rollback, and recovery flows — `scripts/codeops_state_lib/transitions.py`, `scripts/codeops_state_lib/filesystem.py`
- [ ] 2.2.7 Integrate canonical paths and shared writes into graph migration and rendering, then run Phase-2 specification cases green — `scripts/codeops_state_lib/migration.py`, `scripts/codeops_state_lib/rendering.py`

### Step 2.3: Implementation Tests and Hardening

**Reference**: [03-03 §Error Handling](03-03-state-and-filesystem-safety.md#error-handling)

- [ ] 2.3.1 Add Windows API failure/cleanup, foreign backend, path grammar, retry classification/budget, and every write-boundary fault-injection implementation case — `tests/conformance/test_windows_state_impl.py`
- [ ] 2.3.2 Add native integration helpers for real concurrent owners, stale processes, PID reuse where controllable, interruption, and recovery; skip only with explicit non-Windows reason — `tests/conformance/test_windows_state_native.py`
- [ ] 2.3.3 Run all Windows/Linux state suites and the confirmed five-command full verification gate; retain issue-#2 closure evidence — `tests/evidence/windows-state-issue-2.json`

**Verify**: run all five commands confirmed in AR-14.

## Phase 3: Portable Utility Control Layer

> **Phase baseline tree**: _(recorded by the exec-plan skill at phase start)_

### Step 3.1: Specification Tests

**Reference**: [03-02](03-02-portable-control-layer.md) · ST-31–ST-38 · AR-2, AR-8,
AR-11, AR-14

- [ ] 3.1.1 [spec-author] Add layout migration and roadmap sync/compact cross-host specification cases using existing fixtures and canonical outputs — `tests/conformance/test_portable_utilities_spec.py`
- [ ] 3.1.2 [spec-author] Add native worktree, hook, outcome, agent, and hostile-argument/path specification cases — `tests/conformance/test_portable_utilities_spec.py`
- [ ] 3.1.3 [spec-author] Add portable five-gate verifier and Unix compatibility-launcher specification cases — `tests/conformance/test_portable_utilities_spec.py`
- [ ] 3.1.4 Run the Phase-3 specification module red while existing migration, roadmap, compact, worktree, agent, outcome, and hook suites remain green — `tests/conformance/test_portable_utilities_spec.py`

### Step 3.2: Implementation

**Reference**: [03-02 §Modules and Public Commands](03-02-portable-control-layer.md#modules-and-public-commands)

- [ ] 3.2.1 Extract layout discovery, preview, path mapping, and validation into the Python migration command — `scripts/codeops_migrate.py`, `scripts/codeops_migrate_lib/model.py`
- [ ] 3.2.2 Implement authorized migration apply, clean-tree proof, native Git moves, marker-last commit state, idempotence, and recovery-safe failures — `scripts/codeops_migrate.py`, `scripts/codeops_migrate_lib/apply.py`
- [ ] 3.2.3 Extract roadmap layout parsing, derived stage/status calculation, and deterministic rendering to Python — `scripts/codeops_roadmap.py`, `scripts/codeops_roadmap_lib/model.py`
- [ ] 3.2.4 Implement roadmap sync/compact check/write modes through shared atomic writes — `scripts/codeops_roadmap.py`, `scripts/codeops_roadmap_lib/rendering.py`
- [ ] 3.2.5 Implement Python worktree parsing, topic/name validation, repository/default-branch discovery, and list behavior — `scripts/codeops_worktree.py`, `scripts/codeops_worktree_lib/model.py`
- [ ] 3.2.6 Implement worktree new/remove/dry-run/launch using argument-array native Git/Codex subprocesses — `scripts/codeops_worktree.py`, `scripts/codeops_worktree_lib/commands.py`
- [ ] 3.2.7 Implement the portable validation/docs logical gates and deterministic aggregate reporter — `scripts/codeops_verify.py`, `scripts/codeops_verify_lib/core.py`
- [ ] 3.2.8 Implement portable migration/roadmap/compact logical gates by reusing Python commands and fixtures — `scripts/codeops_verify.py`, `scripts/codeops_verify_lib/fixtures.py`
- [ ] 3.2.9 Convert migration and roadmap shell files to thin strict argument-forwarding Unix launchers — `scripts/codeops-migrate.sh`, `scripts/codeops-roadmap-sync.sh`, `scripts/codeops-roadmap-compact.sh`
- [ ] 3.2.10 Convert the worktree binary and five verification shell files to thin Unix launchers; add native PowerShell verification launcher — `bin/codeops-worktree`, `scripts/validate-codex.sh`, `scripts/codeops-verify.ps1`
- [ ] 3.2.11 Complete remaining four verification launchers and run all Phase-3 specification cases green — `scripts/docs-check.sh`, `scripts/migration-check.sh`, `scripts/roadmap-sync-check.sh`

### Step 3.3: Implementation Tests and Hardening

**Reference**: [03-02 §Error Handling](03-02-portable-control-layer.md#error-handling)

- [ ] 3.3.1 Complete compact launcher extraction and add parser, output/exit, injection, containment, Git failure, and deterministic rendering implementation tests — `scripts/compact-check.sh`, `tests/conformance/test_portable_utilities_impl.py`
- [ ] 3.3.2 Run characterization comparisons proving retained Unix launchers match approved behavior on migration, roadmap, compact, worktree, hook, agent, and outcome fixtures — `tests/conformance/test_portable_utilities_impl.py`
- [ ] 3.3.3 Assert every declared Windows/runtime test module is collected and no shipped Windows path contains Bash/WSL delegation — `tests/conformance/test_state_test_collection.py`, `tests/conformance/test_portable_utilities_impl.py`
- [ ] 3.3.4 Run portable `all`, every legacy public launcher, and the confirmed five-command full verification gate — `scripts/codeops_verify.py`

**Verify**: run all five commands confirmed in AR-14.

## Phase 4: Workflow Integration and Native Verification

> **Phase baseline tree**: _(recorded by the exec-plan skill at phase start)_

### Step 4.1: Specification Tests

**Reference**: [03-01 §Hook Integration](03-01-runtime-preflight-and-hooks.md#hook-integration),
[03-02 §Compatibility Launchers](03-02-portable-control-layer.md#compatibility-launchers) ·
ST-35, ST-36, ST-39, ST-40 · AR-3–AR-8, AR-14

- [ ] 4.1.1 [spec-author] Add command-contract cases proving every mutating skill enters shared preflight and uses the certified interpreter without minor pinning — `tests/conformance/test_windows_workflows_spec.py`
- [ ] 4.1.2 [spec-author] Add installed-plugin path-with-spaces lifecycle, no-WSL/Git-Bash command-capture, outcomes, agents, and native full-verification specification cases — `tests/conformance/test_windows_workflows_spec.py`
- [ ] 4.1.3 Run Phase-4 workflow specification cases red while all earlier Windows and Unix suites remain green — `tests/conformance/test_windows_workflows_spec.py`

### Step 4.2: Implementation

**Reference**: [03-01 §Hook Integration](03-01-runtime-preflight-and-hooks.md#hook-integration),
[03-02 §Repository Verification](03-02-portable-control-layer.md#repository-verification)

- [ ] 4.2.1 Add the common prerequisite invocation contract to requirements, retro-requirements, planning, preflight, execution, and upgrade workflows — `skills/make-requirements/SKILL.md`, `skills/retro-requirements/SKILL.md`, `skills/make-plan/SKILL.md`
- [ ] 4.2.2 Complete prerequisite integration for preflight, exec-plan, upgrade-plan, setup-codeops, and roadmap mutations — `skills/preflight/SKILL.md`, `skills/exec-plan/SKILL.md`, `skills/upgrade-plan/SKILL.md`
- [ ] 4.2.3 Complete prerequisite integration for setup-codeops, roadmap, and setup-routing mutations — `skills/setup-codeops/SKILL.md`, `skills/roadmap/SKILL.md`, `skills/setup-routing/SKILL.md`
- [ ] 4.2.4 Complete prerequisite integration for techdocs, analyze-project, and clean-comments mutations — `skills/techdocs/SKILL.md`, `skills/analyze-project/SKILL.md`, `skills/clean-comments/SKILL.md`
- [ ] 4.2.5 Complete prerequisite integration for git-commit and audit every remaining skill so no project-mutating path lacks the gate — `skills/git-commit/SKILL.md`, `tests/conformance/test_windows_workflows_spec.py`
- [ ] 4.2.6 Replace hardcoded `python3` runtime examples with the host-neutral interpreter contract in requirements, planning, and preflight skills — `skills/make-requirements/SKILL.md`, `skills/make-plan/SKILL.md`, `skills/preflight/SKILL.md`
- [ ] 4.2.7 Replace hardcoded `python3` runtime examples with the host-neutral interpreter contract in roadmap, routing, and upgrade skills — `skills/roadmap/SKILL.md`, `skills/setup-routing/SKILL.md`, `skills/upgrade-plan/SKILL.md`
- [ ] 4.2.8 Replace remaining runtime command examples in execution, setup, and artifact references without changing their workflow semantics — `skills/exec-plan/SKILL.md`, `skills/setup-codeops/SKILL.md`, `references/artifacts/traceability.md`
- [ ] 4.2.9 Integrate shared canonical paths/atomic writes into outcomes, worktree snapshots, and optional-agent installation — `scripts/codeops_outcomes.py`, `scripts/codeops_worktree_snapshot.py`, `scripts/install_agents.py`
- [ ] 4.2.10 Add native Windows developer commands and pre-certification documentation that accurately says support is pending evidence — `docs/installation.md`, `docs/troubleshooting.md`, `README.md`
- [ ] 4.2.11 Update migration/tutorial/concepts documentation for native command selection, WSL-installed versus WSL-running behavior, Python 3.x, and local-filesystem constraints — `docs/migration.md`, `docs/tutorial.md`, `docs/concepts.md`
- [ ] 4.2.12 Run all Phase-4 specification cases green without changing their expectations — `tests/conformance/test_windows_workflows_spec.py`

### Step 4.3: Implementation Tests and Hardening

**Reference**: [03-01 §Error Handling](03-01-runtime-preflight-and-hooks.md#error-handling),
[03-02 §Error Handling](03-02-portable-control-layer.md#error-handling)

- [ ] 4.3.1 Add skill command-surface, installed-path, command-capture, outcome/agent/snapshot, docs wording, and interpreter-policy implementation tests — `tests/conformance/test_windows_workflows_impl.py`
- [ ] 4.3.2 Run all Windows workflow suites and the confirmed five-command full verification gate — `scripts/codeops_verify.py`, `scripts/validate-codex.sh`

**Verify**: run all five commands confirmed in AR-14.

## Phase 5: Windows Certification and Release Claim

> **Phase baseline tree**: _(recorded by the exec-plan skill at phase start)_

### Step 5.1: Specification Tests

**Reference**: [03-04](03-04-certification-and-release.md) · ST-46–ST-54 · AR-12–AR-14

- [ ] 5.1.1 [spec-author] Add CI platform/interpreter/native-command and prohibited-runtime specification cases — `tests/conformance/test_windows_certification_spec.py`
- [ ] 5.1.2 [spec-author] Add evidence schema, completeness, failure, version binding, CLI/desktop, and support-claim specification cases — `tests/conformance/test_windows_certification_spec.py`, `tests/fixtures/windows-evidence/`
- [ ] 5.1.3 Run Phase-5 certification cases red while all functional Windows/Unix suites remain green — `tests/conformance/test_windows_certification_spec.py`

### Step 5.2: Implementation

**Reference**: [03-04 §CI Contract](03-04-certification-and-release.md#ci-contract),
[§Evidence Manifest](03-04-certification-and-release.md#evidence-manifest)

- [ ] 5.2.1 Add Ubuntu/native-Windows CI jobs with one current Python 3.x each and native Windows bootstrap/test/verification commands — `.github/workflows/ci.yml`
- [ ] 5.2.2 Add the closed Windows evidence schema and deterministic version/commit/scenario/native-runtime validator — `tests/windows-evidence.schema.json`, `scripts/validate_windows_evidence.py`
- [ ] 5.2.3 Add synthetic valid/invalid CLI and desktop fixtures and integrate evidence validation into portable/full verification — `tests/fixtures/windows-evidence/`, `scripts/codeops_verify_lib/core.py`
- [ ] 5.2.4 Add documentation/release-claim guards that require matching CI, CLI, and desktop evidence before support wording — `scripts/validate_plugin.py`, `scripts/validate_windows_evidence.py`
- [ ] 5.2.5 Run Phase-5 specification cases green and obtain passing Ubuntu plus native Windows CI for the release-candidate commit — `.github/workflows/ci.yml`

### Step 5.3: Real-Host Evidence and Hardening

**Reference**: [03-04 §Evidence Manifest](03-04-certification-and-release.md#evidence-manifest),
[§Documentation and Release Gate](03-04-certification-and-release.md#documentation-and-release-gate)

- [ ] 5.3.1 Execute the complete installed-plugin certification workflow on a real native Windows 11 Codex CLI host and retain sanitized version-matched evidence — `tests/evidence/windows-native-<version>.json`
- [ ] 5.3.2 Execute Windows desktop installation, hook review, preflight, and representative requirements-to-plan smoke on the same candidate and retain evidence — `tests/evidence/windows-desktop-<version>.json`
- [ ] 5.3.3 Validate CI/CLI/desktop evidence together, update README/docs/changelog/release metadata to the proven support boundary, and select the SemVer change under repository policy — `README.md`, `docs/installation.md`, `CHANGELOG.md`
- [ ] 5.3.4 Run the installed release artifact on native Windows and Ubuntu, run all five logical gates, complete independent quality review/audit, then close GitHub issues #2 and #3 only if their acceptance criteria are met — `tests/evidence/windows-native-<version>.json`

**Verify**: run all five commands confirmed in AR-14 on Ubuntu and their native portable
equivalents on Windows.

## Dependencies

```text
Phase 1: prerequisite authority
    ↓
Phase 2: safe native state mutation (closes implementation cause of issue #2)
    ↓
Phase 3: one portable control layer for all utilities
    ↓
Phase 4: every workflow and verification path uses the control layer
    ↓
Phase 5: native CI + real-host evidence + support claim
```

## Success Criteria

The feature is complete when all 72 tasks are verified, every ST-1–ST-54 expectation passes,
Ubuntu and native Windows pass the full logical gate, version-matched Windows CLI and desktop
evidence validates, no Windows path uses WSL/Git Bash, documentation states only the proven
boundary, independent quality review has no unresolved critical/major finding, and GitHub issues
#2 and #3 meet their guarded close criteria.
