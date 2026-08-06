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
first and `python` second with an inline `sys.version_info >= (3, 10)` probe, then executes the authoritative
`codeops_windows_preflight.py` module using an argument array. Its `-ResolvePython` mode prints only
the validated executable path for subsequent argument-array invocation (AR-3).

The Python checker emits the contract below, stores a session attestation beneath `PLUGIN_DATA`,
and can run in `session`, `read`, or `mutation` mode. Session mode performs the full check. Read
mode accepts a valid session attestation or refreshes it. Mutation mode is invoked by each actual
mutating command boundary and reruns every safety-affecting check immediately before its first
write; path/filesystem validation repeats at every atomic write or recovery boundary (AR-5).
Hook `commandWindows` fields use the PowerShell bootstrap; Unix `command` fields keep thin
launchers and do not run the Windows-only checker (AR-2, AR-4).

## Implementation Details

### Result Types

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Protocol, Sequence

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

class PreflightDependencies(Protocol):
    """Provide host facts, ordered probes, clock access, and attestation persistence."""

    def classify_host(self, environment: Mapping[str, str]) -> str: ...
    def evaluate_check(self, code: str, request: Mapping[str, object]) -> CheckResult: ...
    def load_attestation(self, request: Mapping[str, object]) -> Mapping[str, object] | None: ...
    def store_attestation(self, request: Mapping[str, object], result: PreflightResult) -> None: ...
    def cleanup_attestations(self) -> None: ...

def run_preflight(
    *,
    mode: str,
    entrypoint_code: str | None,
    targets: tuple[Path, ...],
    root: Path,
    plugin_root: Path,
    plugin_data: Path,
    session_id: str,
    environment: Mapping[str, str],
    dependencies: PreflightDependencies,
) -> PreflightResult:
    """Evaluate the closed native-runtime prerequisite contract."""
```

`dependencies` is required. The production command constructs the native implementation; tests
provide an in-memory implementation. CLI input cannot select or configure this dependency object,
and the evaluator never reads hidden test-mode environment variables (AR-16).

JSON uses camelCase field names, schema version `1`, UTF-8, deterministic check order, and no
machine-specific secret values. The aggregate status is the greatest severity. Exit 0 means
READY or WARNING, exit 2 means BLOCKED, and exit 1 means malformed input or an internal checker
failure (AR-6).

### Required Checks

| Order | Stable code | READY/WARNING/BLOCKED rule | AR Ref |
|---:|---|---|---|
| 1 | `native-windows` | READY on native Windows; BLOCKED inside WSL or another non-native host | AR-4 |
| 2 | `windows-version` | READY on Windows 11; BLOCKED on other Windows versions | AR-7 |
| 3 | `python-3` | READY for functional Python 3.10 or newer; otherwise BLOCKED | AR-3 |
| 4 | `git-for-windows` | READY when native Git executes and reports a Windows build; otherwise BLOCKED | AR-3 |
| 5 | `workspace-local` | READY for a writable fixed local NTFS workspace; removable/UNC/network/unwritable is BLOCKED | AR-11 |
| 6 | `codex-native` | READY when required native Codex capabilities are observable; WSL delegation is BLOCKED | AR-4, AR-7 |
| 7 | `sandbox` | READY for elevated native sandbox, WARNING for operational unelevated sandbox, BLOCKED if required operations cannot run | AR-7 |
| 8 | `plugin-enabled` | READY when plugin root/data and manifest identity are coherent; otherwise BLOCKED in every mode | AR-5 |
| 9 | `hooks-available` | READY when the current trusted hook is executing; WARNING when a registered command boundary supplies the mutation gate; otherwise BLOCKED for mutation | AR-5 |
| 10 | `path-filesystem` | READY when the root is fixed local NTFS and its existing components are reparse-free; mutation additionally validates every existing root-to-target component, collision key, and replace capability at the write boundary | AR-10, AR-11 |

Before Windows/Unix dispatch, every mutating command passively classifies the current process host
from already available environment/kernel facts. An actual WSL process is refused before mutation.
The discriminator never invokes `wsl.exe`, launches a distribution, translates `/mnt` paths, or
uses WSL as a probe, fallback, test host, or certification host (AR-4).

### Mode and Input Contract

The ten-check readiness contract is Windows-only. The shared passive host discriminator runs first
at every mutating boundary; ordinary Unix launchers then preserve their existing dependency checks
without emitting a synthetic Windows readiness result.

| Mode | Attestation use | Checks executed | Hook rule | Exit rule |
|---|---|---|---|---|
| `session` | Never trusted as input; successful result replaces it | All ten root/workspace checks; transaction-only collision/replace subchecks are not applicable until a target exists | `entrypoint_code` is null and `targets` is empty; the executing trusted SessionStart hook proves hook availability | `0` READY/WARNING; `2` BLOCKED |
| `read` | A matching same-session record may be reused; otherwise run all checks | All ten root/workspace checks on refresh; transaction-only subchecks are not applicable | `entrypoint_code` is null and `targets` is empty; missing hook proof is WARNING | `0` READY/WARNING; `2` BLOCKED |
| `mutation` | Cache supplies diagnostics only | Passive host rejection, then all ten root/workspace checks immediately before the command's first write; check 10 validates the declared targets and repeats at each atomic write/recovery boundary | A closed registered `entrypoint_code` and the complete nonempty durable `targets` set prove the command-level gate; missing hook trust is WARNING | `0` READY/WARNING; `2` BLOCKED |

Mode, registered entrypoint code, complete normalized target set, root, plugin paths, and session ID
are a closed input object. Session/read reject an entrypoint or targets; mutation requires one known
entrypoint and a nonempty, duplicate-free target set wholly contained by the root. Every writer
rejects a path absent from that declared set. Unknown fields, unknown modes/entrypoints, missing or
hostile targets, type errors, and hostile path/session values are malformed input and exit `1`. A
well-formed environmental prerequisite failure is BLOCKED and exits `2`. Internal failures also
exit `1` with sanitized diagnostics and no write.

### Session Attestation

The attestation path is `PLUGIN_DATA/preflight/sessions/<safe-session-id>.json`. The session ID
is restricted to a conservative ASCII allowlist and length before use as a path. The record binds
the result to schema version, session ID, plugin semantic version, canonical plugin root,
workspace root, OS identity, Python executable/version, Git executable identity, hook contract
digest, and creation time. It is never accepted for another session or workspace (AR-5, AR-11).

Attestations are same-session cache records, not authority. They have no within-session TTL;
mutation mode reruns all ten checks and atomically refreshes the record. A creation time more than
five minutes in the future is invalid. SessionStart removes orphan records older than seven days
as retention cleanup only; age never upgrades authority. Malformed, mismatched, or unreadable
records are ignored and regenerated only after a successful full check (AR-5, AR-10).

### Hook Integration

`hooks/hooks.json` supplies both `command` and `commandWindows` for SessionStart and write guards.
The SessionStart hook reads Codex JSON stdin, forwards only validated common fields, runs session
preflight on Windows, and emits the existing session context only after the check contract is
available. The PreToolUse hook performs mutation mode before applying the existing marker guard
(AR-2, AR-5).

Every shipped mutating command invokes mutation mode at its command boundary. Skill instructions
and PreToolUse hooks invoke the same gate as defense in depth; neither is treated as the authority
for a direct CLI mutation. Shared atomic writers repeat the path/filesystem portion immediately
before replacement or recovery (AR-5).

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Neither `py -3` nor `python` runs Python 3.10+ | Emit an actionable BLOCKED message and stop before mutation; never install software | AR-3, AR-6 |
| CodeOps is executing in WSL | BLOCKED with guidance to launch native Windows Codex; do not inspect or alter installed WSL | AR-4 |
| Windows capability cannot be established | BLOCKED for mutation; no guessed compatibility | AR-7 |
| Attestation is missing or invalid | Run full preflight; accept only a newly valid result | AR-5 |
| Session ID or path is hostile | Reject input before filesystem access | AR-6, AR-11 |
| Sandbox is operational but unelevated | WARNING and continue | AR-7 |
| Hook is untrusted/unavailable | Read-only may warn; only a successful registered command-boundary gate can authorize mutation, never a skill check alone | AR-5 |
| Internal checker exception | Stable exit 1 with sanitized diagnostic; no attestation and no mutation | AR-6 |

## Testing Requirements

- Specification tests cover ST-1–ST-11 and ST-28–ST-30; Phase 4 owns ST-12's workflow-wide proof.
- Implementation tests isolate subprocess and Windows capability adapters rather than mocking the
  orchestration contract.
- Hook fixtures cover both Unix `command` and Windows `commandWindows` definitions.
- Security cases cover command injection, session path traversal, hostile environment values, and
  attestation substitution.
