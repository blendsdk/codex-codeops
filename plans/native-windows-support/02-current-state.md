# Current State: Native Windows Support

> **Document**: 02-current-state.md
> **Parent**: [Index](00-index.md)

## Existing Implementation

### What Exists

The state graph, outcome recorder, agent installer, and worktree snapshot logic are primarily
Python and already use the standard library. The state transition engine has strong fail-closed
locking, journaling, recovery, and portfolio validation, but its process proof is Linux-specific.
Migration, roadmap, compaction, hooks, worktree management, and the repository verification gate
still enter through Bash. CI currently exercises Ubuntu only.

### Relevant Files

| File | Purpose | Changes Needed |
|---|---|---|
| `hooks/hooks.json` | Session and mutation hooks | Add native `commandWindows` launchers and prerequisite enforcement |
| `scripts/hook_session_context.sh` | Session context injection | Move reusable behavior to Python; retain Unix launcher |
| `scripts/hook_marker_guard.sh` | Write guard | Move reusable behavior to Python; add native Windows launch path |
| `scripts/codeops_state_lib/transitions.py` | Locking, ownership, atomic transitions, recovery | Replace `/proc` coupling with platform backends; certify Windows replacement semantics |
| `scripts/codeops_state_lib/migration.py` | Traceability upgrades | Canonicalize serialized paths and use portable atomic primitives |
| `scripts/codeops-migrate.sh` | Layout migration | Move behavior to Python and keep a thin Unix launcher |
| `scripts/codeops-roadmap-sync.sh` | Roadmap derivation | Move behavior to shared Python roadmap module |
| `scripts/codeops-roadmap-compact.sh` | Roadmap compaction | Move behavior to shared Python roadmap module |
| `bin/codeops-worktree` | Worktree CLI | Provide a native Python command and retain Unix compatibility launcher |
| `scripts/*-check.sh` | Repository verification | Expose one portable Python verification dispatcher and native launchers |
| `skills/**/SKILL.md` | Runtime command guidance | Replace `python3` assumptions with the certified interpreter contract |
| `.github/workflows/ci.yml` | Automated validation | Add native Windows job using one current Python 3.x |
| `README.md`, `docs/` | Platform contract | Replace unsupported claim only after certification evidence exists |

### Code Analysis

- `scripts/codeops_state_lib/transitions.py:297-341` reads `/proc/<pid>/stat` and Linux boot ID.
  On native Windows, ownership creation fails and mutation is refused.
- `hooks/hooks.json:3-23` defines only shell commands. There is no `commandWindows` path.
- `.github/workflows/ci.yml:10-22` runs only `ubuntu-latest` and invokes Bash verification scripts.
- `scripts/codeops-migrate.sh`, `scripts/codeops-roadmap-sync.sh`, and
  `scripts/codeops-roadmap-compact.sh` combine orchestration and business rules in Bash/Python
  heredocs, preventing direct native Windows execution.
- Durable paths in transition and migration results use `str(Path.relative_to(...))`; that stores
  host separators and can make state non-portable.
- Multiple skill and documentation examples invoke `python3`, while a normal native Windows
  installation commonly exposes Python through `py -3` or `python`.

## Gaps Identified

### Gap 1: No bootstrap before Python

**Current Behavior:** CodeOps assumes an interpreter command already works.
**Required Behavior:** RD-022 and 03-01 define a native probe before any Windows mutation.
**Fix Required:** Add the PowerShell bootstrap, authoritative Python checker, hook integration,
and session attestation (AR-3, AR-5, AR-6).

### Gap 2: Linux-only owner proof

**Current Behavior:** PID reuse and stale-owner decisions depend on Linux `/proc`.
**Required Behavior:** 03-03 defines compatible Linux and native Windows identity backends.
**Fix Required:** Isolate process identity, add Windows API handling, version records, and preserve
fail-closed recovery (AR-9).

### Gap 3: Bash owns shipped behavior

**Current Behavior:** Core utilities and verification orchestration require Bash.
**Required Behavior:** 03-02 defines Python-owned behavior with thin host launchers.
**Fix Required:** Extract and test migration, roadmap, worktree, hook, and verification logic
without changing their public outcomes (AR-2, AR-8).

### Gap 4: Windows path and replacement behavior is uncertified

**Current Behavior:** host separators are serialized and Windows sharing violations have no
specified retry boundary.
**Required Behavior:** 03-03 defines canonical paths, hostile-name rejection, bounded retries,
and recoverable failure.
**Fix Required:** Centralize path serialization/validation and atomic replacement (AR-10, AR-11).

### Gap 5: No native evidence

**Current Behavior:** CI is Linux-only and documentation states Windows is unsupported.
**Required Behavior:** 03-04 defines the claim gate.
**Fix Required:** Add native Windows CI and retain version-matched CLI/desktop evidence before
updating the support claim (AR-12, AR-13).

## Dependencies

### Internal Dependencies

- Existing transition and recovery invariants in `scripts/codeops_state_lib/transitions.py`.
- Existing migration, roadmap, hook, outcome, agent, and worktree conformance tests.
- Codex plugin hook schema and `PLUGIN_ROOT`/`PLUGIN_DATA` host integration.
- Governing port requirements and release evidence conventions.

### External Dependencies

- Native Windows 11.
- A functional Python 3.x interpreter.
- Git for Windows and native Codex.
- PowerShell available as the Windows bootstrap host.
- GitHub Actions native Windows runners for automated certification.

## Risks and Concerns

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Windows process API access is denied or ambiguous | Medium | High | Return unknown, refuse stale-owner takeover, retain recovery state (AR-9) |
| Antivirus/indexers temporarily hold replaced files | Medium | High | Retry only allowlisted sharing failures within the 03-03 budget (AR-10) |
| Python extraction changes mature Bash behavior | Medium | High | Characterization/spec tests before each extraction; thin compatibility launchers (AR-2) |
| Hook trust is absent | Medium | High | Block mutation until prerequisite enforcement is available; skill entrypoints also enforce it (AR-5) |
| CI passes while installed product fails | Medium | High | Real installed-plugin CLI evidence and desktop smoke are separate release gates (AR-13) |
| Legacy path or owner records are unsafe | Low | High | Read only validated compatible forms; never guess or silently rewrite (AR-9, AR-11) |
