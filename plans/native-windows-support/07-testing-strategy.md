# Testing Strategy: Native Windows Support

> **Document**: 07-testing-strategy.md
> **Parent**: [Index](00-index.md)

## Testing Overview

### Coverage Goals

| Code type | Target |
|---|---:|
| Preflight, process identity, path safety, atomic state, and recovery | 95% branch coverage |
| Migration, roadmap, worktree, hooks, and verification modules | 90% branch coverage |
| Thin host launchers and CI/configuration glue | Complete contract/scenario coverage |

Specification tests are written from the cases below before implementation. Existing Linux state
specification tests remain an immutable regression oracle. Integration tests use real local files,
Git repositories, processes, and native Windows CI whenever feasible.

## 🚨 Specification Test Cases

### Runtime Preflight and Hooks

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-1 | SessionStart on native Windows 11 with functional `py -3`, native Git, writable local workspace, enabled plugin, trusted hooks, and operational sandbox | Exit 0; schema-1 JSON status is READY; ordered checks are all READY; a session/workspace-bound attestation is atomically stored | RD-022; 03-01 §Result Types, §Session Attestation |
| ST-2 | `py -3` is absent, but `python` runs any Python major version 3 | Bootstrap selects `python`, exits 0, and records the observed interpreter without requiring a specific minor/patch | RD-022; AR-3; 03-01 §Proposed Changes |
| ST-3 | Both interpreter commands are absent, broken, or report a major version other than 3 | Exit 2 with BLOCKED `python-3`, actionable install/configuration guidance, no auto-install attempt, no attestation, and no project mutation | RD-022; AR-3; 03-01 §Error Handling |
| ST-4 | WSL is installed/enabled but the hook process is native Windows | WSL does not affect readiness; no `wsl.exe`, distribution, or WSL filesystem command is executed | RD-022; AR-4; 03-01 §Required Checks |
| ST-5 | Preflight process is actually running under WSL | Exit 2 with BLOCKED `native-windows`, guidance to launch native Codex, and no mutation | RD-022; AR-4; 03-01 §Error Handling |
| ST-6 | Native Windows version is not Windows 11 | Exit 2 with BLOCKED `windows-version` and no attestation/mutation | RD-022; 03-01 §Required Checks |
| ST-7 | Native sandbox is operational but unelevated | Exit 0 with aggregate WARNING and a `sandbox` WARNING; other valid checks remain visible | RD-022; 03-01 §Required Checks |
| ST-8 | Workspace root is UNC, network-backed, outside containment, or not writable | Exit 2 with the corresponding BLOCKED local-workspace/path check before mutation | RD-022; AR-11; 03-01 §Required Checks |
| ST-9 | Session attestation belongs to another session, workspace, plugin version, or hook digest | Ignore it, run a full check, and replace it only if the new check succeeds | AR-5; 03-01 §Session Attestation |
| ST-10 | Mutation mode receives a valid session attestation but Git/workspace/plugin conditions changed | Recheck detects the change and returns BLOCKED before write | RD-022; AR-5; 03-01 §Proposed Changes |
| ST-11 | Hook stdin contains hostile session ID/path text or extra unrecognized contract fields | Reject with exit 1 or BLOCKED as specified by input class; perform no path escape, command execution, attestation write, or project mutation | AR-6, AR-11; 03-01 §Session Attestation, §Error Handling |
| ST-12 | Hook is not trusted/available and a mutating skill starts | The skill-level enforced preflight must succeed before the first write; otherwise mutation is BLOCKED | RD-022; AR-5; 03-01 §Hook Integration |

### Process Ownership, Paths, and Atomic State

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-13 | A transition begins on native Windows with a queryable current process | Journal/lock owner uses the versioned Windows backend, PID, creation identity, and host epoch; transition can proceed | RD-022; AR-9; 03-03 §Process Identity Contract |
| ST-14 | Recorded Windows PID no longer exists | Absence is proven and authorized stale-owner recovery may claim the transaction | RD-022; AR-9; 03-03 §Error Handling |
| ST-15 | Recorded PID exists but has a different creation identity | PID reuse proves the recorded owner absent; recovery may proceed under the existing protocol | RD-022; AR-9; 03-03 §Process Identity Contract |
| ST-16 | Windows process query returns access denied, malformed data, backend mismatch, or API uncertainty | Owner absence is unknown; transition/recovery refuses takeover and preserves state | RD-022; AR-9; 03-03 §Error Handling |
| ST-17 | Existing unversioned Linux owner record is processed on Linux | Existing boot-ID/start-tick semantics remain accepted; Linux regression cases stay green | AR-9; 03-03 §Process Identity Contract |
| ST-18 | Two native Windows processes attempt the same transition concurrently | Exactly one owns the lock; the other receives a deterministic refusal; committed graph/journal remains valid | RD-022; 03-03 §Testing Requirements |
| ST-19 | Windows transition is interrupted at each journal/write/replace/validation boundary | Rerun reports recovery-required or safely rolls back/forward according to existing protocol; no false completion or silent loss | RD-022; 03-03 §Integration Points |
| ST-20 | A stale Windows transaction is recovered after PID reuse | Recovery validates expected owner and journal binding, performs one authorized outcome, and removes state only after validation | RD-022; AR-9; 03-03 §Integration Points |
| ST-21 | A project-relative durable path is emitted on Windows | Stored JSON uses `/` separators and round-trips to the contained native path | RD-022; AR-11; 03-03 §Path Contract |
| ST-22 | A safe legacy backslash-relative record is read on Windows | It resolves within root and is normalized only during the next separately authorized write | AR-11; 03-03 §Path Contract |
| ST-23 | Input contains traversal, drive/UNC/device/ADS syntax, invalid characters, reserved device basename, or trailing dot/space | Reject before filesystem access; existing state is not silently rewritten | RD-022; AR-11; 03-03 §Path Contract |
| ST-24 | Atomic replace receives one or more allowlisted transient Windows sharing violations and then succeeds within two seconds | Retry according to the single bounded schedule, commit valid bytes, and preserve protocol ordering | AR-10; 03-03 §Atomic Write Contract |
| ST-25 | Sharing violation persists past the bounded budget | Fail with recovery state intact; never delete destination as fallback | AR-10; 03-03 §Atomic Write Contract |
| ST-26 | Replacement fails for validation, path safety, permission policy, or an unknown OS error | Do not retry; fail closed with the original destination/recovery evidence protected | AR-10, AR-11; 03-03 §Atomic Write Contract |
| ST-27 | Preflight atomic capability probe runs on unsupported/network filesystem | Return BLOCKED before a workflow mutation starts | RD-022; 03-01 §Required Checks; 03-03 §Atomic Write Contract |

### Portable Utilities and Hooks

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-28 | Hook manifest is validated | SessionStart and PreToolUse expose Unix `command` and native `commandWindows` paths, with no WSL/Git Bash command | RD-022; AR-2, AR-4; 03-01 §Hook Integration |
| ST-29 | Native Windows SessionStart hook runs from a plugin path containing spaces | Argument boundaries remain intact; preflight and context succeed without shell evaluation | 03-01 §Hook Integration |
| ST-30 | PreToolUse receives a protected artifact edit after a valid session check | Mutation preflight runs first, then the existing marker guard returns its unchanged allow/warn behavior | AR-5; 03-01 §Hook Integration |
| ST-31 | Layout migration `preview` and authorized `apply` run on equivalent Unix and native Windows fixture repositories | Preview, moved paths, marker-last ordering, idempotence, and final bytes are behaviorally equivalent using canonical paths | RD-022; 03-02 §Migration |
| ST-32 | Roadmap `sync` and `compact` run on flat/nested fixtures on Unix and Windows | Check/write exit statuses and rendered UTF-8 bytes match except explicitly injected date data | RD-022; 03-02 §Roadmap |
| ST-33 | Native worktree `new/list/remove` runs with spaces in repo path and a safe topic | It uses native Git, preserves current behavior, and never launches a shell/WSL/Git Bash | RD-022; AR-4; 03-02 §Worktrees |
| ST-34 | Worktree/migration/roadmap receives hostile option, topic, branch, or path input | Closed parsing and shared path rules reject it before Git or filesystem mutation | AR-11; 03-02 §Error Handling |
| ST-35 | Outcome storage and optional-agent installation/check run natively on Windows | Existing output/state contracts pass with canonical paths and atomic writes | RD-022; 03-02 §Modules and Public Commands |
| ST-36 | Portable verifier runs `all` on Windows | It executes equivalents of all five AR-14 gates natively, reports deterministic per-gate results, and exits nonzero if any gate fails | AR-8, AR-14; 03-02 §Repository Verification |

### Cross-Platform Regression, Certification, and Claims

| # | Input / Scenario | Expected Output / Behavior | Source |
|---|---|---|---|
| ST-37 | Existing Linux transition specification suite runs after adapter extraction | All immutable expectations remain green and new owner records remain recovery-compatible | AR-9; 03-03 §Testing Requirements |
| ST-38 | Existing migration, roadmap, hook, agent, outcome, worktree, and target-workflow suites run via Unix launchers | Public outputs, exit classes, and repository results remain green | AR-2; 03-02 §Compatibility Launchers |
| ST-39 | Windows test captures every spawned command during representative workflows | No executable/argument invokes `bash`, Git Bash, `wsl`, a distribution, or `/mnt` translation | RD-022; AR-4; 03-04 §CI Contract |
| ST-40 | Native Windows requirements, planning, preflight, execution state, migration, and roadmap flows run sequentially in a path with spaces | Each completes using only native PowerShell/Python/Git/Codex and passes post-state validation | RD-023; 03-04 §Evidence Manifest |
| ST-41 | Windows filesystem/process integration suite runs with real processes and interruptions | Concurrency, stale-owner, PID-reuse, interrupted-write, and recovery cases satisfy ST-13–ST-26 | RD-023; 03-03 §Testing Requirements |
| ST-42 | Generated identifiers include every reserved Windows device name with mixed case and extensions | Every invalid identifier is rejected before a directory/file is created | RD-022; AR-11; 03-03 §Path Contract |
| ST-43 | Unicode and long-but-supported contained paths run through state, migration, roadmap, and worktree commands | Paths round-trip canonically or fail with a deterministic platform-capability diagnostic; no truncation/collision occurs | RD-022; 03-03 §Path Contract |
| ST-44 | Recovery record created on one supported host backend is presented on another backend | Absence remains unknown and recovery refuses takeover; no host reinterprets foreign identity fields | AR-9; 03-03 §Error Handling |
| ST-45 | Mutation-sensitive prerequisite changes between preflight and atomic write | Final before-write validation refuses the mutation and preserves prior state | RD-022; AR-5; 03-01 §Proposed Changes; 03-03 §Integration Points |
| ST-46 | CI configuration is validated | Ubuntu and native Windows jobs each use one Python 3.x; Windows commands are PowerShell/Python and both run all five logical gates | AR-12, AR-14; 03-04 §CI Contract |
| ST-47 | Windows evidence omits a required scenario or has a failing result | Evidence validator fails and documentation continues to state Windows unsupported | RD-023; AR-13; 03-04 §Evidence Manifest |
| ST-48 | Windows evidence version or commit differs from the release candidate | Evidence validator rejects it as stale/mismatched | RD-023; AR-13; 03-04 §Evidence Manifest |
| ST-49 | Evidence reports WSL/Git Bash invocation despite otherwise successful scenarios | Certification fails | RD-023; AR-4, AR-13; 03-04 §Error Handling |
| ST-50 | Valid version-matched Windows 11 CLI installed-plugin evidence covers all required scenarios | CLI evidence gate passes | RD-023; AR-13; 03-04 §Evidence Manifest |
| ST-51 | Valid version-matched Windows desktop installation/hook/representative-workflow smoke is retained | Desktop evidence gate passes | RD-023; AR-13; 03-04 §Evidence Manifest |
| ST-52 | CI, CLI evidence, and desktop evidence all pass for the same release candidate | Documentation/release validation permits the Windows support claim | RD-023; AR-13; 03-04 §Documentation and Release Gate |
| ST-53 | Documentation pins one Python minor/patch or says WSL must be uninstalled | Documentation validation fails | RD-022; AR-3, AR-4; 03-04 §Documentation and Release Gate |
| ST-54 | Documentation and metadata are scanned before valid evidence exists | Any claim that Windows is supported fails validation; unsupported/planned wording remains required | RD-023; AR-13; 03-04 §Documentation and Release Gate |

## Test Categories

### Specification Tests

| Test File | ST Cases Covered | Component |
|---|---|---|
| `tests/conformance/test_windows_preflight_spec.py` | ST-1–ST-12, ST-28–ST-30 | Preflight and hooks |
| `tests/conformance/test_windows_state_spec.py` | ST-13–ST-27, ST-37, ST-41–ST-45 | State and filesystem |
| `tests/conformance/test_portable_utilities_spec.py` | ST-31–ST-40 | Portable control layer |
| `tests/conformance/test_windows_certification_spec.py` | ST-46–ST-54 | Certification and claims |

### Implementation Tests

| Test File | Description | Priority |
|---|---|---|
| `tests/conformance/test_windows_preflight_impl.py` | Probe adapters, attestation validation, ordered rendering, hostile input | High |
| `tests/conformance/test_windows_state_impl.py` | Native API edge cases, retry boundaries, path grammar, fault injection | High |
| `tests/conformance/test_portable_utilities_impl.py` | Parser, launcher, Git invocation, parity, module boundaries | High |
| `tests/conformance/test_windows_certification_impl.py` | Evidence schema, version binding, docs/CI policy | High |

### Integration Tests

| Test | Components | Description |
|---|---|---|
| Native transition/recovery | Preflight + state + filesystem | Real Windows processes, locks, interruptions, and recovery |
| Native installed plugin | Hooks + skills + all utilities | Windows 11 CLI workflow from plugin installation through verification |
| Unix compatibility | Shell launchers + Python modules | Existing Ubuntu fixtures and gates remain behaviorally equivalent |

### End-to-End Tests

| Scenario | Steps | Expected Result |
|---|---|---|
| Windows CLI certification | Install/enable plugin, approve hooks, run representative lifecycle and recovery/migration/roadmap/full verify | Version-matched evidence passes with no WSL/Git Bash invocation |
| Windows desktop smoke | Install/enable plugin, review hooks, run preflight and representative requirements-to-plan workflow | Desktop evidence passes for the same release candidate |

## Test Data

### Fixtures Needed

- Synthetic native/preflight environments and attestation records.
- Legacy Linux and Windows owner records, malformed/foreign owner records, and interrupted journals.
- Safe/unsafe Windows path component corpus, including mixed-case device names.
- Existing migration/roadmap fixtures copied into paths containing spaces and Unicode.
- Valid, missing, stale, mismatched, WSL-tainted, CLI, and desktop evidence manifests.

### Mock Requirements

Mock only platform boundaries unavailable on the current host: Windows API calls, Codex capability
reporting, and transient OS error injection. Use real subprocesses, Git repositories, local files,
and native Windows APIs in integration/CI tests.

## Verification Checklist

- [ ] Every ST case is implemented in a `*_spec.py` module before production changes.
- [ ] New specification tests are recorded red while the existing Linux oracle remains green.
- [ ] Implementation tests cover internal/error boundaries after green specification behavior.
- [ ] Native Windows CI passes all five logical repository gates.
- [ ] Ubuntu passes the five confirmed `AGENTS.md` commands.
- [ ] Real Windows 11 CLI and desktop evidence is valid and version-matched.
- [ ] No Windows path invokes WSL or Git Bash.
