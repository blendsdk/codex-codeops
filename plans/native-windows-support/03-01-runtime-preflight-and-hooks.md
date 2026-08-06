# Runtime Preflight and Hooks: Native Windows Support

> **Document**: 03-01-runtime-preflight-and-hooks.md
> **Parent**: [Index](00-index.md)

## Overview

This component owns the native Windows bootstrap and deterministic prerequisite gate. It is the
only component allowed to declare the current session ready for Windows CodeOps mutation.

## Architecture

### Current Architecture

SessionStart and PreToolUse execute Bash scripts. Skills call `python3` directly. No shared
runtime result proves native execution, supported Windows, Python, Git, workspace, plugin/hook,
or sandbox capabilities.

### Proposed Changes

`codeops-windows-preflight.ps1` is a minimal bootstrap. It never evaluates project text and never
constructs a shell command from input. It locates a functional interpreter by invoking `py -3`
first and `python` second with an inline major-version probe, then executes the authoritative
`codeops_windows_preflight.py` module using an argument array (AR-3).

The Python checker emits the contract below, stores a session attestation beneath `PLUGIN_DATA`,
and can run in `session`, `read`, or `mutation` mode. Session mode performs the full check. Read
mode accepts a valid session attestation or refreshes it. Mutation mode always rechecks the
current execution host, interpreter, Git, workspace, filesystem, and hook/plugin availability
before a write (AR-5). Hook `commandWindows` fields use the PowerShell bootstrap; Unix `command`
fields keep thin launchers (AR-2, AR-4).

## Implementation Details

### Result Types

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence

class Readiness(str, Enum):
    READY = "READY"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True)
class CheckResult:
    code: str
    status: Readiness
    message: str
    remediation: str | None

@dataclass(frozen=True)
class PreflightResult:
    schema_version: int
    status: Readiness
    session_id: str
    checks: tuple[CheckResult, ...]

def run_preflight(
    *,
    mode: str,
    root: Path,
    plugin_root: Path,
    plugin_data: Path,
    session_id: str,
    environment: Mapping[str, str],
) -> PreflightResult:
    """Evaluate the closed native-runtime prerequisite contract."""
```

JSON uses camelCase field names, schema version `1`, UTF-8, deterministic check order, and no
machine-specific secret values. The aggregate status is the greatest severity. Exit 0 means
READY or WARNING, exit 2 means BLOCKED, and exit 1 means malformed input or an internal checker
failure (AR-6).

### Required Checks

| Order | Stable code | READY/WARNING/BLOCKED rule | AR Ref |
|---:|---|---|---|
| 1 | `native-windows` | READY on native Windows; BLOCKED inside WSL; not applicable on Unix | AR-4 |
| 2 | `windows-version` | READY on Windows 11; BLOCKED on other Windows versions | AR-7 |
| 3 | `python-3` | READY for a functional major version 3; otherwise BLOCKED | AR-3 |
| 4 | `git-for-windows` | READY when native Git executes and reports a Windows build; otherwise BLOCKED | AR-3 |
| 5 | `workspace-local` | READY for a local writable workspace; UNC/network or unwritable is BLOCKED | AR-11 |
| 6 | `codex-native` | READY when required native Codex capabilities are observable; WSL delegation is BLOCKED | AR-4, AR-7 |
| 7 | `sandbox` | READY for elevated native sandbox, WARNING for operational unelevated sandbox, BLOCKED if required operations cannot run | AR-7 |
| 8 | `plugin-enabled` | READY when plugin root/data and manifest identity are coherent; otherwise BLOCKED for mutation | AR-5 |
| 9 | `hooks-available` | READY when expected hooks are loaded/trusted, WARNING for read-only work, BLOCKED for mutation without an alternate enforced entry gate | AR-5 |
| 10 | `path-filesystem` | READY when canonical path and atomic replace capability probes pass locally; otherwise BLOCKED | AR-10, AR-11 |

WSL detection is based on the running kernel/process environment, not whether `wsl.exe` or an
installed distribution exists. The implementation must not probe WSL by launching it (AR-4).

### Session Attestation

The attestation path is `PLUGIN_DATA/preflight/sessions/<safe-session-id>.json`. The session ID
is restricted to a conservative ASCII allowlist and length before use as a path. The record binds
the result to schema version, session ID, plugin semantic version, canonical plugin root,
workspace root, OS identity, Python executable/major, Git executable identity, hook contract
digest, and creation time. It is never accepted for another session or workspace (AR-5, AR-11).

Attestations are cache records, not authority. Mutation mode rechecks the mutable fields and
atomically refreshes the record. Malformed, stale, mismatched, or unreadable records are ignored
and regenerated only after a successful full check (AR-5, AR-10).

### Hook Integration

`hooks/hooks.json` supplies both `command` and `commandWindows` for SessionStart and write guards.
The SessionStart hook reads Codex JSON stdin, forwards only validated common fields, runs session
preflight on Windows, and emits the existing session context only after the check contract is
available. The PreToolUse hook performs mutation mode before applying the existing marker guard
(AR-2, AR-5).

Skill instructions that can mutate the project invoke the shared preflight entry before their
first write. This protects sessions where hooks were not approved or were unavailable; it does
not treat hooks as a complete security boundary (AR-5).

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Neither `py -3` nor `python` runs Python 3 | Emit an actionable BLOCKED message and stop before mutation; never install software | AR-3, AR-6 |
| CodeOps is executing in WSL | BLOCKED with guidance to launch native Windows Codex; do not inspect or alter installed WSL | AR-4 |
| Windows capability cannot be established | BLOCKED for mutation; no guessed compatibility | AR-7 |
| Attestation is missing or invalid | Run full preflight; accept only a newly valid result | AR-5 |
| Session ID or path is hostile | Reject input before filesystem access | AR-6, AR-11 |
| Sandbox is operational but unelevated | WARNING and continue | AR-7 |
| Hook is untrusted/unavailable | Read-only may warn; mutation blocks unless the mutating skill's enforced preflight succeeds | AR-5 |
| Internal checker exception | Stable exit 1 with sanitized diagnostic; no attestation and no mutation | AR-6 |

## Testing Requirements

- Specification tests cover ST-1–ST-12 and ST-28–ST-30.
- Implementation tests isolate subprocess and Windows capability adapters rather than mocking the
  orchestration contract.
- Hook fixtures cover both Unix `command` and Windows `commandWindows` definitions.
- Security cases cover command injection, session path traversal, hostile environment values, and
  attestation substitution.
