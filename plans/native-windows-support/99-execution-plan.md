# Execution Plan: Native Windows Support

> **Document**: 99-execution-plan.md
> **Parent**: [Index](00-index.md)
> **Last Updated**: 2026-08-06 22:10
> **Progress**: 24/72 tasks (33%)
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
> `Get-Date -Format 'yyyy-MM-dd HH:mm'` in native PowerShell or
> `date '+%Y-%m-%d %H:%M'` on Unix.

## Phase 1: Native Preflight and Hook Enforcement

> **Phase baseline tree**: `5337b567cf44b83e00d125f82567ae33214d67ea`
> **Scope mode**: strict
> **Expected modification set**: `tests/conformance/test_windows_preflight_spec.py`,
> `tests/fixtures/hooks/`, `scripts/codeops_windows_preflight.py`,
> `scripts/codeops_windows_lib/`, `scripts/codeops_platform/hosts.py`,
> `scripts/codeops-windows-preflight.ps1`, `scripts/codeops-windows-hook.ps1`,
> `scripts/codeops_hooks.py`, `hooks/hooks.json`,
> `scripts/hook_session_context.sh`, `scripts/hook_marker_guard.sh`,
> `tests/conformance/test_windows_preflight_impl.py`, `tests/conformance/test_hooks.py`,
> `tests/conformance/test_state_v2_spec.py`, `tests/conformance/test_state_v2_impl.py`, this
> execution plan, and the feature traceability graph.
> **Authorized necessary correction**: At 2026-08-06 21:00 the user approved updating the two
> state-discovery assertions whose fixed one-graph expectation was invalidated by the already
> approved native-Windows traceability graph. The correction changes no discovery behavior.
> **Bootstrap tracking exception**: User-authorized under AR-15. Until Task 2.2.6 enables native
> Windows traceability transitions, verified task marks and per-task commits advance while graph
> task nodes remain pending. Reconcile them atomically after 2.2.6 and before 2.2.7.
> **Bootstrap reconciliation completed:** 2026-08-06 21:53. All 20 verified tasks through 2.2.6
> advanced through implemented to verified using 40 native atomic transitions after one complete
> semantic-revision refresh. State validation reports zero problems; 52 future tasks remain pending.

### Step 1.1: Specification Tests

**Reference**: [03-01](03-01-runtime-preflight-and-hooks.md) · ST-1–ST-11, ST-28–ST-30 ·
AR-3–AR-7

- [x] 1.1.1 [spec-author] Add bootstrap, closed mode/input matrix, status/exit, WSL, Python 3.10+, sandbox, and attestation specification cases — `tests/conformance/test_windows_preflight_spec.py` ✅ (completed: 2026-08-06 20:19)
- [x] 1.1.2 [spec-author] Add dual-host hook-manifest, path-with-spaces, mutation-order, and missing-trust specification cases — `tests/conformance/test_windows_preflight_spec.py`, `tests/fixtures/hooks/` ✅ (completed: 2026-08-06 20:22)
- [x] 1.1.3 Run the new Phase-1 specification module, record expected red results, and prove every pre-existing conformance test remains green — `tests/conformance/test_windows_preflight_spec.py` ✅ (completed: 2026-08-06 20:26)

Red evidence: native run recorded 15 expected failing specification cases at
`%TEMP%/verify-red-phase-1.1.3.log`. Immutable baseline evidence: GitHub Actions run
`31116047265` passed all five gates at `a3890b8`; the diff through this task changes only the new
Windows plan/traceability/specification-test artifacts and no pre-existing implementation or
conformance-test file. Rerun `31120294368` remained unassigned to a hosted runner and is treated as
infrastructure state, not verification evidence.

### Step 1.2: Implementation

**Reference**: [03-01 §Implementation Details](03-01-runtime-preflight-and-hooks.md#implementation-details)

- [x] 1.2.1 Implement closed readiness/check result models, ordered rendering, mode/entrypoint/complete-target-set inputs, exit classes, and sanitized diagnostics — `scripts/codeops_windows_preflight.py`, `scripts/codeops_windows_lib/models.py` ✅ (completed: 2026-08-06 20:29)
- [x] 1.2.2 Implement a shared passive pre-dispatch WSL refusal plus native Windows version, Python, Git, Codex/sandbox, plugin/hook, workspace, and filesystem probes behind documented adapters; never invoke WSL to detect or test it — `scripts/codeops_platform/hosts.py`, `scripts/codeops_windows_lib/probes.py`, `scripts/codeops_windows_preflight.py` ✅ (completed: 2026-08-06 20:35)
- [x] 1.2.3 Implement same-session attestation validation, containment, future-time rejection, seven-day orphan cleanup, refresh, and atomic storage — `scripts/codeops_windows_lib/attestation.py`, `scripts/codeops_windows_preflight.py` ✅ (completed: 2026-08-06 20:41)
- [x] 1.2.4 Add the minimal PowerShell Python 3.10+ bootstrap and `-ResolvePython` output with `py -3`/`python` probes and no shell-evaluated input — `scripts/codeops-windows-preflight.ps1` ✅ (completed: 2026-08-06 20:43)
- [x] 1.2.5 Move hook behavior to the portable hook entry, add `commandWindows`, and retain thin Unix launchers — `scripts/codeops_hooks.py`, `hooks/hooks.json`, `scripts/hook_session_context.sh` ✅ (completed: 2026-08-06 20:48)
- [x] 1.2.6 Complete marker-guard launcher extraction and run all Phase-1 specification cases green — `scripts/hook_marker_guard.sh`, `scripts/codeops_hooks.py` ✅ (completed: 2026-08-06 20:51)

### Step 1.3: Implementation Tests and Hardening

**Reference**: [03-01 §Error Handling](03-01-runtime-preflight-and-hooks.md#error-handling)

- [x] 1.3.1 Add adapter, closed matrix, cache-binding/retention, malformed-input, hostile-environment, command-injection, and NTFS/reparse implementation tests — `tests/conformance/test_windows_preflight_impl.py` ✅ (completed: 2026-08-06 20:54)
- [x] 1.3.2 Run Phase-1 spec/implementation suites, hook validation, and the confirmed five-command full verification gate — `tests/conformance/test_hooks.py`, `scripts/validate-codex.sh` ✅ (completed: 2026-08-06 21:18)

Native verification passed all 180 currently executable conformance tests, including 34 Phase-1
preflight/hook tests, plus plugin, skill, Markdown-link, retained-scenario, compile, manifest, and
diff validation. Only the three `/proc`-bound state transition/collection modules are excluded
under AR-15 until Phase 2 installs their native process backend. The immutable Ubuntu five-gate
baseline remains green; the portable current-tree five-gate rerun is owned again by Tasks 3.3.4
and 4.3.2 after the native verifier exists.

**Verify**:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

### Phase 1 Quality Review

Strict independent review ran against baseline tree
`5337b567cf44b83e00d125f82567ae33214d67ea`. Security findings supersede the reviewer's
security lens. Auto-design selected every listed technical correction; no risk was waived.

| Finding | Severity | Decision | State |
|---|---|---|---|
| RV-001 / SA-001: the public PowerShell preflight exits successfully because the Python module has no CLI | CRITICAL / MAJOR | Added a closed argument parser, production dependency construction, JSON rendering, and stable exits | Fixed; verified |
| RV-002: `py -3` is probed but the returned launcher later runs without `-3` | MAJOR | Resolve and return the concrete supported `sys.executable` | Fixed; verified |
| RV-003: hook readiness accepts unrelated Windows commands | MAJOR | Validate the exact event-specific Unix and Windows hook contract | Fixed; verified |
| RV-004: the spaces test does not execute the registered Windows hook | MAJOR | Added installed-path native execution with spaces and hostile legal path characters | Fixed; verified |
| SA-002: mutation target reparses are not checked | MAJOR | Preserve lexical targets and check every existing root-to-target component | Fixed; verified |
| SA-003: inline `-Command` permits plugin-root interpolation injection | MAJOR | Use a checked-in `-File` launcher that reads `$env:PLUGIN_ROOT` and derives siblings from `$PSScriptRoot` | Fixed; verified |
| RV-005: unhashable API values can escape as raw type errors | MINOR | Add explicit type guards and cover stable CLI exit 1 | Fixed; verified |
| RV-003R: hook validation ignores matcher, type, cardinality, and extra hooks | MAJOR | Validate the complete exact two-event manifest object and add substitution cases | Fixed after re-review; verified directly |

Traceability review evidence is deferred under AR-15 and reconciles with task state immediately
after Task 2.2.6.

No project techdocs opt-in exists, so the post-phase techdocs update is not applicable.
The single permitted re-review cleared every other critical/major finding and identified RV-003R;
that exact correction passed direct verification. Per the review cap, no third review was run.

## Phase 2: Windows State, Recovery, and Filesystem Safety

> **Phase baseline tree**: `662a25f283d4e2876b7382335057cb39abdb37a4`
> **Scope mode**: strict
> **Expected modification set**: `tests/conformance/test_windows_state_spec.py`,
> `tests/conformance/test_windows_state_impl.py`,
> `tests/conformance/test_windows_state_native.py`,
> `tests/conformance/test_state_migration_spec.py`,
> `tests/conformance/test_state_migration_impl.py`,
> `tests/conformance/windows_state_test_support.py`,
> `tests/conformance/test_state_test_collection.py`, `tests/fixtures/windows-state/`,
> `tests/evidence/windows-state-issue-2.json`,
> `scripts/codeops_state.py`, `scripts/codeops_state_lib/models.py`,
> `scripts/codeops_state_lib/processes.py`, `scripts/codeops_state_lib/processes_windows.py`,
> `scripts/codeops_state_lib/paths.py`, `scripts/codeops_state_lib/filesystem.py`,
> `scripts/codeops_state_lib/transitions.py`, `scripts/codeops_state_lib/migration.py`,
> `scripts/codeops_state_lib/rendering.py`, `.github/workflows/ci.yml`, this execution plan, and
> the feature traceability graph.
> **Authorized necessary correction:** Task 2.2.6 may update
> `scripts/codeops_windows_lib/probes.py` because native integration proved the Windows Store
> `py.exe` alias cannot launch inside the restricted-token sandbox. The probe now uses the concrete
> already-certified `sys.executable`; prerequisite policy and acceptance behavior are unchanged.
> **Authorized collection correction:** Task 2.3.3 may update the migration fixtures to construct
> equivalent current-host owner records instead of importing `/proc` during Windows collection.
> Linux retains its original procfs record and assertions.
> **Authorized verification correction:** Task 2.3.3 may add the manual trigger to the existing
> Ubuntu CI workflow so the exact five-command gate can be run against the current feature tree.
> This does not change the gate commands, runner, permissions, or automatic triggers.

### Step 2.1: Specification Tests

**Reference**: [03-03](03-03-state-and-filesystem-safety.md) · ST-13–ST-27, ST-37,
ST-41–ST-45 · AR-9–AR-11

- [x] 2.1.1 [spec-author] Add versioned Windows/legacy Linux owner, absence, PID-reuse, uncertainty, concurrency, and recovery specification cases — `tests/conformance/test_windows_state_spec.py` ✅ (completed: 2026-08-06 21:29)
- [x] 2.1.2 [spec-author] Add canonical/legacy/hostile path, reserved/alias/reparse cases, exact WinError 32/33 retry, generic-access refusal, interruption, and non-NTFS specification cases — `tests/conformance/test_windows_state_spec.py`, `tests/fixtures/windows-state/` ✅ (completed: 2026-08-06 21:36)
- [x] 2.1.3 Run new state specification cases red while the immutable Linux state and migration specification modules remain green — `tests/conformance/test_windows_state_spec.py`, `tests/conformance/test_state_migration_spec.py` ✅ (completed: 2026-08-06 21:37)

Task 2.1.1 red evidence: native collection and syntax validation succeeded; all nine process-owner
specification cases failed solely because the planned `scripts.codeops_state_lib.processes` module
does not exist yet. Full output is retained at `%TEMP%/verify-red-task-2.1.1.log`.

Task 2.1.2 red evidence: the 20-case combined module collected; its eleven filesystem cases failed
solely because the planned `scripts.codeops_state_lib.paths` module does not exist, while the nine
owner cases retain their expected missing-process-module failure. Python compilation and fixture
JSON parsing passed. Full output is retained at `%TEMP%/verify-red-task-2.1.2.log`.

Task 2.1.3 regression evidence: the combined Windows module retained exactly 20 expected missing-
adapter errors at `%TEMP%/verify-red-task-2.1.3-windows-state.log`; 48 existing portable state
tests passed natively at `%TEMP%/verify-green-task-2.1.3-native-state.log`. The Linux-only migration
specification, implementation tests, transition implementation, and migration implementation have
the same Git object IDs as successful Ubuntu five-gate run `31116047265` at `a3890b8`. They were
not executed through an emulation layer on Windows under the no-WSL constraint.

### Step 2.2: Implementation

**Reference**: [03-03 §Process Identity Contract](03-03-state-and-filesystem-safety.md#process-identity-contract) and [§Atomic Write Contract](03-03-state-and-filesystem-safety.md#atomic-write-contract)

- [x] 2.2.1 Add closed versioned Linux/Windows process identity models, backend protocol, and exact legacy-Linux record parser — `scripts/codeops_state_lib/processes.py`, `scripts/codeops_state_lib/models.py` ✅ (completed: 2026-08-06 21:39)
- [x] 2.2.2 Move current `/proc` behavior behind the Linux backend without changing its absence decisions — `scripts/codeops_state_lib/processes.py`, `scripts/codeops_state_lib/transitions.py` ✅ (completed: 2026-08-06 21:41)
- [x] 2.2.3 Implement least-privilege Windows PID/creation-FILETIME probing with guaranteed handle cleanup and fail-closed uncertainty — `scripts/codeops_state_lib/processes_windows.py`, `scripts/codeops_state_lib/processes.py` ✅ (completed: 2026-08-06 21:42)
- [x] 2.2.4 Implement canonical durable paths, safe legacy reads, NTFS/case/8.3 collision keys, every-existing-component root-to-target reparse rejection, containment, and invalid-component rejection — `scripts/codeops_state_lib/paths.py` ✅ (completed: 2026-08-06 21:44)
- [x] 2.2.5 Implement shared same-directory atomic writes with the fixed WinError 32/33 retry schedule, immediate filesystem revalidation, and no delete fallback — `scripts/codeops_state_lib/filesystem.py` ✅ (completed: 2026-08-06 21:45)
- [x] 2.2.6 Integrate the registered mutation preflight and process/filesystem adapters into the direct state CLI, transition, journal, lock, rollback, replacement, and recovery boundaries — `scripts/codeops_state.py`, `scripts/codeops_state_lib/transitions.py`, `scripts/codeops_state_lib/filesystem.py` ✅ (completed: 2026-08-06 21:53)
- [x] 2.2.7 Integrate canonical paths and shared writes into graph migration and rendering, then run Phase-2 specification cases green — `scripts/codeops_state_lib/migration.py`, `scripts/codeops_state_lib/rendering.py` ✅ (completed: 2026-08-06 21:58)

### Step 2.3: Implementation Tests and Hardening

**Reference**: [03-03 §Error Handling](03-03-state-and-filesystem-safety.md#error-handling)

- [x] 2.3.1 Add Windows API failure/cleanup, foreign backend, NTFS alias/reparse grammar, exact retry classification/schedule, command-boundary gate, and every write-boundary fault-injection case — `tests/conformance/test_windows_state_impl.py` ✅ (completed: 2026-08-06 22:00)
- [x] 2.3.2 Add native integration helpers for real concurrent owners, stale processes, PID reuse where controllable, interruption, and recovery; skip only with explicit non-Windows reason — `tests/conformance/test_windows_state_native.py` ✅ (completed: 2026-08-06 22:02)
- [x] 2.3.3 Run all Windows/Linux state suites and the confirmed five-command full verification gate; retain issue-#2 closure evidence — `tests/evidence/windows-state-issue-2.json` ✅ (completed: 2026-08-06 22:44)

**Verify**: run all five commands confirmed in AR-14.

Native Phase-2 verification passed 252/252 repository conformance tests,
plus plugin, all 16 skill manifests, local Markdown links, retained scenario parity, compilation,
documentation-release text, and Codex-native terminology checks. No Windows command used WSL,
Git Bash, or Bash. Current-tree Ubuntu run `31127808294` passed the exact five repository commands
at implementation commit `1f6ca26`; the native portable equivalents remain owned by Phase 3.
Issue-#2 implementation evidence is retained in `tests/evidence/windows-state-issue-2.json`.

### Phase 2 Quality Review

The independent phase reviewer, security auditor, and recovery auditor reviewed the strict Phase-2
tree. Auto-design selected a technical correction for every critical/major finding; no risk was
waived. Current-tree Ubuntu CI proved the exact five-command gate after the single permitted
re-review and its required corrections.

| Finding | Severity | Decision | State |
|---|---|---|---|
| RV2-001: persisted and returned graph paths used host separators | MAJOR | Canonicalize every durable and public graph path to `/` | Fixed; direct verification passed |
| RV2-002 / RV2-002R: migration/conformance subprocesses depended on absent or stale ambient plugin authority | MAJOR | Unconditionally install isolated native test authority, restore the original environment at exit, and make the direct launcher establish its repository import root | Fixed after re-review; hostile-ambient verification passed |
| RV2-003: the five-command gate claim used an older Ubuntu tree | MAJOR | Add a manual trigger to the unchanged Ubuntu workflow and require a current-tree run | Fixed; run `31127808294` passed |
| RV2-004: durable path grammar applied Windows-invalid-name rejection only on Windows | MAJOR | Enforce the portable durable-name grammar on every host while retaining Windows-only legacy backslash reads | Fixed; cross-host specification verification passed |
| P2-SEC-001 / RC-003: recovery mutated journal/locks before validating the complete path set | MAJOR | Validate journal identity, regular-file existence, all graph/image paths, containment, reparse state, and NTFS alias collisions before takeover mutation | Fixed after re-review; missing-file and fault-injection verification passed |
| P2-SEC-002: direct state-module execution bypassed mutation preflight | MAJOR | Disable the internal module entry point; retain the public preflighted launcher as the sole CLI | Fixed; byte-identical refusal verification passed |
| RC-001: `BaseException` after replacement deleted recovery evidence | CRITICAL | Preserve the published journal, locks, and images unless success or rollback is proven | Fixed for single- and multi-graph paths; interruption verification passed |
| RC-002: completed recovery replay retained transaction debris | MAJOR | Make completed replay perform idempotent owned-artifact cleanup, including journal-missing crash windows, with images removed before the journal | Fixed after re-review; crash-window replay verification passed |

Native correction verification passed 44/44 focused migration/state tests in a shell without
`PLUGIN_ROOT`, `PLUGIN_DATA`, or `PYTHONPATH`, and 250/250 repository conformance tests with the
certified interpreter in UTF-8 mode. No verification command used WSL, Git Bash, or Bash.
The capped re-review cleared RV2-001, RV2-004, P2-SEC-002, RC-001, and RC-003; it reopened
RV2-002R, P2-SEC-001, and RC-002 for the exact edge cases recorded above. Those final corrections
passed 46/46 focused tests with deliberately invalid ambient plugin variables. Per the review cap,
no third review was run.

## Phase 3: Portable Utility Control Layer

> **Phase baseline tree**: `c8a618afec4ac54390062bee70aeac7bea2000cd`
> **Scope mode**: strict
> **Expected modification set**: `tests/conformance/test_portable_utilities_spec.py`,
> `tests/conformance/test_portable_utilities_impl.py`,
> `tests/conformance/test_state_test_collection.py`, `scripts/codeops_platform/subprocesses.py`,
> `scripts/codeops_migrate.py`, `scripts/codeops_migrate_lib/`, `scripts/codeops_roadmap.py`,
> `scripts/codeops_roadmap_lib/`, `scripts/codeops_worktree.py`, `scripts/codeops_worktree_lib/`,
> `scripts/codeops_verify.py`, `scripts/codeops_verify_lib/`, `scripts/codeops-migrate.sh`,
> `scripts/codeops-roadmap-sync.sh`, `scripts/codeops-roadmap-compact.sh`,
> `bin/codeops-worktree`, `scripts/validate-codex.sh`, `scripts/docs-check.sh`,
> `scripts/migration-check.sh`, `scripts/roadmap-sync-check.sh`, `scripts/compact-check.sh`,
> `scripts/codeops-verify.ps1`, this execution plan, and the feature traceability graph.
> **Authorized command-boundary correction:** Phase 3 may extend the closed mutation-entrypoint
> registry in `scripts/codeops_windows_preflight.py` for the migration, roadmap, and worktree
> commands introduced by this phase. Their prerequisite policy remains unchanged.

### Step 3.1: Specification Tests

**Reference**: [03-02](03-02-portable-control-layer.md) · ST-31–ST-38 · AR-2, AR-8,
AR-11, AR-14

- [x] 3.1.1 [spec-author] Add layout migration and roadmap sync/compact cross-host specification cases using existing fixtures and canonical outputs — `tests/conformance/test_portable_utilities_spec.py` ✅ (completed: 2026-08-06 22:50)
- [x] 3.1.2 [spec-author] Add native worktree, hook, outcome, agent, and hostile-argument/path specification cases — `tests/conformance/test_portable_utilities_spec.py` ✅ (completed: 2026-08-06 22:53)
- [x] 3.1.3 [spec-author] Add portable five-gate verifier and Unix compatibility-launcher specification cases — `tests/conformance/test_portable_utilities_spec.py` ✅ (completed: 2026-08-06 22:54)
- [x] 3.1.4 Run the Phase-3 specification module red while existing migration, roadmap, compact, worktree, agent, outcome, and hook suites remain green — `tests/conformance/test_portable_utilities_spec.py` ✅ (completed: 2026-08-06 22:56)

### Step 3.2: Implementation

**Reference**: [03-02 §Modules and Public Commands](03-02-portable-control-layer.md#modules-and-public-commands)

- [x] 3.2.1 Add the shared argument-array subprocess/evidence adapter, then extract layout discovery, preview, path mapping, and validation into the Python migration command — `scripts/codeops_platform/subprocesses.py`, `scripts/codeops_migrate.py`, `scripts/codeops_migrate_lib/model.py` ✅ (completed: 2026-08-06 23:01)
- [x] 3.2.2 Implement mutation-gated authorized migration apply, clean-tree proof, native Git moves, marker-last commit state, idempotence, and recovery-safe failures — `scripts/codeops_migrate.py`, `scripts/codeops_migrate_lib/apply.py` ✅ (completed: 2026-08-06 23:06)
- [x] 3.2.3 Extract roadmap layout parsing, derived stage/status calculation, and deterministic rendering to Python — `scripts/codeops_roadmap.py`, `scripts/codeops_roadmap_lib/model.py` ✅ (completed: 2026-08-06 23:14)
- [x] 3.2.4 Implement roadmap sync/compact check/write modes with command-boundary mutation gates and shared atomic writes — `scripts/codeops_roadmap.py`, `scripts/codeops_roadmap_lib/rendering.py` ✅ (completed: 2026-08-06 23:18)
- [x] 3.2.5 Implement Python worktree parsing, topic/name validation, repository/default-branch discovery, and list behavior — `scripts/codeops_worktree.py`, `scripts/codeops_worktree_lib/model.py` ✅ (completed: 2026-08-06 23:24)
- [x] 3.2.6 Implement mutation-gated worktree new/remove plus dry-run/launch using the shared native Git/Codex subprocess adapter — `scripts/codeops_worktree.py`, `scripts/codeops_worktree_lib/commands.py` ✅ (completed: 2026-08-06 23:29)
- [x] 3.2.7 Implement the portable validation/docs logical gates and deterministic aggregate reporter — `scripts/codeops_verify.py`, `scripts/codeops_verify_lib/core.py` ✅ (completed: 2026-08-06 23:36)
- [x] 3.2.8 Implement portable migration/roadmap/compact logical gates by reusing Python commands and fixtures — `scripts/codeops_verify.py`, `scripts/codeops_verify_lib/fixtures.py` ✅ (completed: 2026-08-06 23:11)
- [x] 3.2.9 Convert migration and roadmap shell files to thin strict argument-forwarding Unix launchers — `scripts/codeops-migrate.sh`, `scripts/codeops-roadmap-sync.sh`, `scripts/codeops-roadmap-compact.sh` ✅ (completed: 2026-08-06 23:16)
- [x] 3.2.10 Convert the worktree binary and five verification shell files to thin Unix launchers; add native PowerShell verification launcher — `bin/codeops-worktree`, `scripts/validate-codex.sh`, `scripts/codeops-verify.ps1` ✅ (completed: 2026-08-06 23:20)
- [x] 3.2.11 Complete remaining four verification launchers and run all Phase-3 specification cases green — `scripts/docs-check.sh`, `scripts/migration-check.sh`, `scripts/roadmap-sync-check.sh` ✅ (completed: 2026-08-06 23:28)

### Step 3.3: Implementation Tests and Hardening

**Reference**: [03-02 §Error Handling](03-02-portable-control-layer.md#error-handling)

> **Temporary execution-order recovery:** GitHub Actions run `31128295160`, pinned to Task 3.3.2
> implementation commit `a763b24`, remained queued during a hosted-runner incident. Independent
> native Task 3.3.3 may checkpoint while 3.3.2 remains `[~]`; Phase 3 cannot close until the
> retained-Unix characterization run passes.

- [x] 3.3.1 Complete compact launcher extraction and add parser, output/exit, injection, containment, Git failure, and deterministic rendering implementation tests — `scripts/compact-check.sh`, `tests/conformance/test_portable_utilities_impl.py` ✅ (completed: 2026-08-06 23:33)
- [x] 3.3.2 Run characterization comparisons proving retained Unix launchers match approved behavior on migration, roadmap, compact, worktree, hook, agent, and outcome fixtures — `tests/conformance/test_portable_utilities_impl.py` ✅ (completed: 2026-08-07 00:05)
- [x] 3.3.3 Assert every declared Windows/runtime test module is collected and no shipped Windows path contains Bash/WSL delegation — `tests/conformance/test_state_test_collection.py`, `tests/conformance/test_portable_utilities_impl.py` ✅ (completed: 2026-08-06 23:49)
- [x] 3.3.4 Run portable `all`, every legacy public launcher, and the confirmed five-command full verification gate — `scripts/codeops_verify.py` ✅ (completed: 2026-08-07 00:05)

**Verify**: run all five commands confirmed in AR-14.

### Phase 3 Quality Review

The independent reviewer, security auditor, and recovery/compatibility auditor reviewed the
strict Phase-3 tree. Auto-design selected a technical correction for every critical/major
finding; no risk was waived. The single permitted re-review cleared the reviewer's original set
and exposed the remaining transaction/recovery edges below. Those edges were corrected and
verified without a third review, as required by the review cap.

| Finding | Severity | Decision | State |
|---|---|---|---|
| P3-RV-001 / P3-SEC-002 / P3-RC-001: migration could overwrite/delete destinations or leave a false marker after interruption | CRITICAL | Refuse every generated collision, validate marker semantics, register cleanup before writes, and make cleanup/Git rollback non-short-circuiting | Fixed; collision, malformed-marker, post-marker, and cleanup-failure regressions passed |
| P3-RV-002 / P3-RC-003 / P3-RC-005: portable validation lost retained groups and depended on ambient encoding | MAJOR | Port every former logical contract/scenario check, bind trusted validator paths, and force UTF-8 for every child/capture | Fixed; ambient-free native `all` passed |
| P3-SEC-004: PowerShell forwarded-root and argparse abbreviations could rebind trusted validation | MAJOR | Reject explicit root forwarding, disable argparse abbreviation, and resolve validator scripts from the trusted plugin tree | Fixed; `--root`, `--root=`, `--ro`, and `--r` regressions passed |
| P3-RV-003: roadmap sync no longer validated authoritative traceability | MAJOR | Run the authoritative state validator before every sync mode when schema-2 graphs exist | Fixed; invalid-graph refusal passed byte-identically |
| P3-RV-004 / P3-RC-002: roadmap dates no longer followed owned-change semantics | MAJOR | Apply the injected date only when an owned feature/portfolio value changes and recompute stable output deterministically | Fixed; drift/stability regression passed |
| P3-SEC-001 / P3-RV-005: worktree preflight omitted the sibling target/common Git metadata | MAJOR | Gate the deduplicated common Git directory, checkout metadata, and sibling worktree under their common boundary | Fixed; complete-target regression passed |
| P3-RC-004 / P3-RC-006: retained worktree output and explicit force-delete semantics changed; second-command failure was partially mutating | MAJOR | Delegate human list output to native Git, retain explicit `-D`, and restore the removed worktree if branch deletion fails | Fixed; golden-output, unmerged-delete, and rollback regressions passed |
| P3-SEC-003 / P3-RC-007 / P3-RC-008: multi-roadmap writes lacked safe set recovery and recomputation | MAJOR | Add an OS-owned exclusive lock, closed/hash-bound canonical journal, journal-first commit cleanup, complete rollback, and retry-after-recovery recomputation | Fixed; partial-crash, hostile-journal, concurrency, and later-write failure regressions passed |

Native correction verification passed 292 repository tests with four explicit platform skips, all
five logical gates, restored scenario/contract checks, and no ambient UTF-8 variables. No Windows
command used WSL, Git Bash, or Bash. Ubuntu run `31128730695` passed the exact five retained public
launchers at fixed commit `b9c14fe`. The reviewer re-review was clear; the security and recovery
re-reviews identified the final transaction edges recorded above, which were fixed under the
no-third-review cap.

## Phase 4: Workflow Integration and Native Verification

> **Phase baseline tree**: `c4626d86426d98f0a0f0bcf1e515ae283750f441`
> **Scope mode**: strict
> **Expected modification set**: `tests/conformance/test_windows_workflows_spec.py`,
> `tests/conformance/test_windows_workflows_impl.py`, `_shared/native-runtime.md`, the skill and
> reference files named by Tasks 4.2.1–4.2.8, `scripts/codeops_windows_preflight.py`,
> `scripts/codeops_outcomes.py`, `scripts/codeops_worktree_snapshot.py`, `scripts/install_agents.py`,
> `docs/installation.md`, `docs/troubleshooting.md`, `docs/migration.md`, `docs/tutorial.md`,
> `docs/concepts.md`, `README.md`, this execution plan, and the feature traceability graph.
> **Necessary command-registry correction:** Phase 4 may register the defense-in-depth skill gate
> and the outcome, snapshot, and agent mutation entrypoints required by Tasks 4.2.1–4.2.9.

### Step 4.1: Specification Tests

**Reference**: [03-01 §Hook Integration](03-01-runtime-preflight-and-hooks.md#hook-integration),
[03-02 §Compatibility Launchers](03-02-portable-control-layer.md#compatibility-launchers) ·
ST-12, ST-39, ST-40 with regression reuse of ST-35 and ST-36 · AR-3–AR-8, AR-14

- [x] 4.1.1 [spec-author] Add ST-12 command-contract cases proving direct CLIs own mutation gates, every mutating skill invokes defense-in-depth preflight, and every workflow uses Python 3.10+ through the certified interpreter — `tests/conformance/test_windows_workflows_spec.py` ✅ (completed: 2026-08-07 00:09)
- [x] 4.1.2 [spec-author] Add installed-plugin path-with-spaces lifecycle, no-WSL/Git-Bash command-capture, outcomes, agents, and native full-verification specification cases — `tests/conformance/test_windows_workflows_spec.py` ✅ (completed: 2026-08-07 00:12)
- [x] 4.1.3 Run Phase-4 workflow specification cases red while all earlier Windows and Unix suites remain green — `tests/conformance/test_windows_workflows_spec.py` ✅ (completed: 2026-08-07 00:17)

### Step 4.2: Implementation

**Reference**: [03-01 §Hook Integration](03-01-runtime-preflight-and-hooks.md#hook-integration),
[03-02 §Repository Verification](03-02-portable-control-layer.md#repository-verification)

- [x] 4.2.1 Add the common prerequisite invocation contract to requirements, retro-requirements, planning, preflight, execution, and upgrade workflows — `skills/make-requirements/SKILL.md`, `skills/retro-requirements/SKILL.md`, `skills/make-plan/SKILL.md` ✅ (completed: 2026-08-07 00:21)
- [x] 4.2.2 Complete prerequisite integration for preflight, exec-plan, upgrade-plan, setup-codeops, and roadmap mutations — `skills/preflight/SKILL.md`, `skills/exec-plan/SKILL.md`, `skills/upgrade-plan/SKILL.md` ✅ (completed: 2026-08-07 00:19)
- [x] 4.2.3 Complete prerequisite integration for setup-codeops, roadmap, and setup-routing mutations — `skills/setup-codeops/SKILL.md`, `skills/roadmap/SKILL.md`, `skills/setup-routing/SKILL.md` ✅ (completed: 2026-08-07 00:22)
- [x] 4.2.4 Complete prerequisite integration for techdocs, analyze-project, and clean-comments mutations — `skills/techdocs/SKILL.md`, `skills/analyze-project/SKILL.md`, `skills/clean-comments/SKILL.md` ✅ (completed: 2026-08-07 00:24)
- [x] 4.2.5 Complete prerequisite integration for git-commit and audit every remaining skill so no project-mutating path lacks the gate — `skills/git-commit/SKILL.md`, `tests/conformance/test_windows_workflows_spec.py` ✅ (completed: 2026-08-07 00:26)
- [x] 4.2.6 Replace hardcoded `python3` runtime examples with the host-neutral interpreter contract in requirements, planning, and preflight skills — `skills/make-requirements/SKILL.md`, `skills/make-plan/SKILL.md`, `skills/preflight/SKILL.md` ✅ (completed: 2026-08-07 00:28)
- [x] 4.2.7 Replace hardcoded `python3` runtime examples with the host-neutral interpreter contract in roadmap, routing, and upgrade skills — `skills/roadmap/SKILL.md`, `skills/setup-routing/SKILL.md`, `skills/upgrade-plan/SKILL.md` ✅ (completed: 2026-08-07 00:30)
- [x] 4.2.8 Replace remaining runtime command examples in execution, setup, and artifact references without changing their workflow semantics — `skills/exec-plan/SKILL.md`, `skills/setup-codeops/SKILL.md`, `references/artifacts/traceability.md` ✅ (completed: 2026-08-07 00:34)
- [x] 4.2.9 Integrate registered mutation gates plus shared canonical paths/atomic writes into outcomes, worktree snapshots, and optional-agent installation — `scripts/codeops_outcomes.py`, `scripts/codeops_worktree_snapshot.py`, `scripts/install_agents.py` ✅ (completed: 2026-08-07 00:31)
- [x] 4.2.10 Add native Windows developer commands and pre-certification documentation that accurately says support is pending evidence — `docs/installation.md`, `docs/troubleshooting.md`, `README.md` ✅ (completed: 2026-08-07 00:35)
- [x] 4.2.11 Update migration/tutorial/concepts documentation for native command selection, WSL-installed versus WSL-running behavior, Python 3.10+, and fixed-local-NTFS constraints — `docs/migration.md`, `docs/tutorial.md`, `docs/concepts.md` ✅ (completed: 2026-08-07 00:38)
- [x] 4.2.12 Run all Phase-4 specification cases green without changing their expectations — `tests/conformance/test_windows_workflows_spec.py` ✅ (completed: 2026-08-07 00:39)

### Step 4.3: Implementation Tests and Hardening

**Reference**: [03-01 §Error Handling](03-01-runtime-preflight-and-hooks.md#error-handling),
[03-02 §Error Handling](03-02-portable-control-layer.md#error-handling)

- [x] 4.3.1 Add skill command-surface, installed-path, command-capture, outcome/agent/snapshot, docs wording, and interpreter-policy implementation tests — `tests/conformance/test_windows_workflows_impl.py` ✅ (completed: 2026-08-07 00:44)
- [x] 4.3.2 Run all Windows workflow suites and the confirmed five-command full verification gate — `scripts/codeops_verify.py`, `scripts/validate-codex.sh` ✅ (completed: 2026-08-07 01:07)

### Phase 4 Quality Review

The independent reviewer, security auditor, and recovery/compatibility auditor found no critical
issues and converged on the major workflow-boundary gaps below. Auto-design selected the listed
technical corrections; no risk was waived. Files outside the original expected set were changed
only where the audit proved that shared command capture or legacy test harnesses owned part of the
necessary correction.

| Finding | Severity | Decision | State |
|---|---|---|---|
| P4-RV-001 / P4-SEC-001 / P4-RC-002: linked-worktree snapshots used the checkout as root and omitted the predictable index lock | MAJOR | Use the primary worktree's parent as the common sibling boundary; gate the common directory, objects, temporary index, and index lock; clean both temporary paths | Fixed; real linked-worktree regression passed |
| P4-SEC-002 / P4-RC-001: concurrent outcome read/replace lost successful events | MAJOR | Serialize the complete read-and-atomic-replace operation with a process-owned per-path OS lock | Fixed; eight-process native concurrency regression retained every event |
| P4-RC-003 / P4-SEC-006: multi-role agent installation could partially apply, and duplicate requested roles could make its recovery journal invalid | MAJOR | Deduplicate roles before planning, then publish a closed hash-bound multi-file transaction with process locking, rollback, journal-first cleanup, and restart recovery | Fixed; duplicate-role, later-write rollback, and interrupted-restart regressions passed |
| P4-RV-002 / P4-SEC-003: command evidence captured only test-owned top-level wrappers | MAJOR | Add an explicit inherited absolute evidence sink to the shared argument-array adapter, serialize its writers, and prove nested Git capture plus trace-free ordinary operation | Fixed; nested capture/default-no-trace regressions passed |
| P4-RV-003 / P4-SEC-003: ST-40 did not execute the required installed spaces-path lifecycle and initially accepted a no-op roadmap result | MAJOR | Run the copied installed plugin's requirements, planning, execution preflight, state-transition, roadmap, and migration CLIs through real native command gates; require durable roadmap changes, an in-sync follow-up, final state validation, and captured nested commands | Fixed; installed native sequential lifecycle and roadmap post-state regression passed |
| P4-RV-004: shared quality instructions retained a hardcoded `python3` command | MAJOR | Use `<CODEOPS_PYTHON>` and add the shared file to both interpreter inventories | Fixed; complete surface scan passed |
| P4-SEC-004: recorded Phase-4 baseline hash was not a real commit | MAJOR | Replace it with the resolved Phase-3 closure commit | Fixed; baseline resolves to `c4626d86426d98f0a0f0bcf1e515ae283750f441` |
| P4-SEC-005: the generic project root could not contain linked-worktree Git metadata for guarded commits | MAJOR | Define the Git-specific common sibling boundary and closed index/object/ref/log/HEAD/message target set, rerun before staging and commit | Fixed; guarded-commit contract regression passed |

The single permitted re-review cleared all recovery findings plus the original linked-worktree,
command-capture, interpreter, baseline, and Git-boundary findings. It exposed the duplicate-role
journal edge and a roadmap false-positive in ST-40. Those exact residuals were corrected and
verified directly without requesting a third review, honoring the review cap.

Final Phase-4 native verification passed 315 repository tests with four explicit platform skips,
all five logical gates, real installed-plugin mutation preflights in paths with spaces, and no
ambient UTF-8 variables. No Windows command used WSL, Git Bash, or Bash. Ubuntu authority run
`31129821708` passed the exact five retained public launchers at fixed commit `4c9abb6`.

**Verify**: run all five commands confirmed in AR-14.

## Phase 5: Windows Certification and Release Claim

> **Phase baseline tree**: `db55e80264839d6d60e6a16b300339be4f711ddf`
> **Scope mode**: strict
> **Expected modification set**: `.github/workflows/ci.yml`,
> `tests/conformance/test_windows_certification_spec.py`,
> `tests/conformance/test_windows_certification_impl.py`, `tests/windows-evidence.schema.json`,
> `tests/fixtures/windows-evidence/`, `tests/evidence/`, `scripts/capture_windows_evidence.py`,
> `scripts/validate_windows_evidence.py`, `scripts/codeops_verify_lib/core.py`,
> `scripts/validate_plugin.py`, `.codex-plugin/plugin.json`, `README.md`,
> `docs/installation.md`, `docs/migration.md`, `docs/tutorial.md`, `docs/troubleshooting.md`,
> `docs/concepts.md`, `CHANGELOG.md`, release documentation, this execution plan, and the feature
> traceability graph.

### Step 5.1: Specification Tests

**Reference**: [03-04](03-04-certification-and-release.md) · ST-46–ST-54 · AR-12–AR-14

- [x] 5.1.1 [spec-author] Add explicit Windows 11 runner, Python 3.10+, native-command, and prohibited-runtime specification cases — `tests/conformance/test_windows_certification_spec.py` ✅ (completed: 2026-08-07 01:12)
- [x] 5.1.2 [spec-author] Add capture/supporting-record hash binding, sanitization, evidence schema, completeness, failure, version binding, CLI/desktop provenance, and support-claim cases — `tests/conformance/test_windows_certification_spec.py`, `tests/fixtures/windows-evidence/` ✅ (completed: 2026-08-07 01:16)
- [x] 5.1.3 Run Phase-5 certification cases red while all functional Windows/Unix suites remain green — `tests/conformance/test_windows_certification_spec.py` ✅ (completed: 2026-08-07 01:25)

The red gate collected all nine certification specifications at the missing CI/evidence owners.
The prior functional inventory passed 281 tests with four platform skips. That inventory exposed
a transient Windows access-denied race around the outcome store; the correction retains the
shared atomic-writer contract and applies a bounded outcome-specific retry while holding the
exclusive store lock. Three consecutive eight-process regressions passed.

### Step 5.2: Implementation

**Reference**: [03-04 §CI Contract](03-04-certification-and-release.md#ci-contract),
[§Evidence Manifest](03-04-certification-and-release.md#evidence-manifest)

- [x] 5.2.1 Add Ubuntu and explicit `windows-11-arm` CI jobs with one Python 3.10+ each and native Windows bootstrap/test/verification commands — `.github/workflows/ci.yml` ✅ (completed: 2026-08-07 01:29)
- [x] 5.2.2 Add the closed Windows evidence schema, compact capture runner, and deterministic supporting-record/version/commit/scenario/native-runtime validator — `tests/windows-evidence.schema.json`, `scripts/capture_windows_evidence.py`, `scripts/validate_windows_evidence.py` ✅ (completed: 2026-08-07 01:30)
- [x] 5.2.3 Add synthetic valid/invalid CLI/desktop/supporting-record fixtures, the declared implementation-boundary suite, and portable/full evidence validation — `tests/fixtures/windows-evidence/`, `tests/conformance/test_windows_certification_impl.py`, `scripts/codeops_verify_lib/core.py` ✅ (completed: 2026-08-07 01:34)
- [x] 5.2.4 Add documentation/release-claim guards that require matching CI, CLI, and desktop evidence before support wording — `scripts/validate_plugin.py`, `scripts/validate_windows_evidence.py` ✅ (completed: 2026-08-07 01:36)
- [x] 5.2.5 Run Phase-5 specification/implementation cases green and obtain passing Ubuntu plus explicit native Windows 11 CI for the release-candidate commit — `.github/workflows/ci.yml` ✅ (completed: 2026-08-07 02:14)

Release-candidate verification: GitHub Actions run `31133716364` passed both the Ubuntu authority
job and the native `windows-11-arm` job at commit `90bd435`; Windows completed the conformance
suite and the native PowerShell aggregate of all five logical gates.

### Step 5.3: Real-Host Evidence and Hardening

**Reference**: [03-04 §Evidence Manifest](03-04-certification-and-release.md#evidence-manifest),
[§Documentation and Release Gate](03-04-certification-and-release.md#documentation-and-release-gate)

- [x] 5.3.1 Run the capture command against the packed candidate on a real native Windows 11 Codex CLI host and retain the version-matched manifest, command trace, and sanitized hash-bound scenario records — `tests/evidence/windows-native-<version>.json`, `tests/evidence/windows-native-<version>/` ✅ (completed: 2026-08-07 02:32)
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
