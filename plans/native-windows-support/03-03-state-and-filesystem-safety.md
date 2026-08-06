# State and Filesystem Safety: Native Windows Support

> **Document**: 03-03-state-and-filesystem-safety.md
> **Parent**: [Index](00-index.md)

## Overview

This component closes GitHub issue #2 and certifies state mutation on native Windows without
weakening owner proof, recovery, atomicity, validation, or Linux compatibility.

## Architecture

### Current Architecture

`transitions.py` combines the transition protocol with Linux `/proc` process identity. Atomic
replacement uses `os.replace`, while directory fsync errors are ignored for portability. Durable
relative paths are rendered with host separators. These choices work in the current Ubuntu gate
but are not a defined Windows contract.

### Proposed Changes

Introduce platform-neutral process and filesystem adapter modules. Transition and migration code
depend only on those public contracts. Linux retains `/proc` semantics. Windows process identity
uses native APIs through standard-library `ctypes`; filesystem replacement uses the common atomic
writer with an allowlisted, bounded Windows retry policy (AR-9, AR-10).

### Process Identity Contract

Records use two closed backend-specific shapes:

```json
{"schemaVersion": 1, "backend": "linux-proc", "pid": 42, "startTicks": "123", "bootId": "uuid"}
{"schemaVersion": 1, "backend": "windows-filetime", "pid": 42, "creationFileTime": "133829001234567890"}
```

Linux reads the existing unversioned `{pid,startTicks,bootId}` shape as a legacy Linux identity
and preserves the current exact boot-ID/start-tick absence rules. Windows opens the process with
`PROCESS_QUERY_LIMITED_INFORMATION`, reads the exact unsigned 64-bit creation `FILETIME` from
`GetProcessTimes`, serializes it as a base-10 string, and closes the handle on every path. A
missing PID or a different creation `FILETIME` proves the recorded process absent. Access denied,
malformed values, API failure, or backend mismatch returns unknown rather than absent. Windows
does not derive or compare a boot epoch (AR-9).

The portable Python contract is:

```python
class AbsenceState(str, Enum):
    ABSENT = "absent"
    PRESENT = "present"
    UNKNOWN = "unknown"

@dataclass(frozen=True, slots=True)
class LinuxProcessIdentity:
    pid: int
    start_ticks: str
    boot_id: str
    def to_payload(self) -> dict[str, object]: ...

@dataclass(frozen=True, slots=True)
class WindowsProcessIdentity:
    pid: int
    creation_file_time: str
    def to_payload(self) -> dict[str, object]: ...

ProcessIdentity = LinuxProcessIdentity | WindowsProcessIdentity

class ProcessBackend(Protocol):
    backend_name: str
    def identify(self, pid: int) -> ProcessIdentity | None: ...
    def absence(self, identity: ProcessIdentity) -> AbsenceState: ...

def parse_process_identity(payload: object) -> ProcessIdentity | None: ...
def current_process_identity(backend: ProcessBackend, pid: int) -> ProcessIdentity | None: ...
def owner_absence(payload: object, backend: ProcessBackend) -> AbsenceState: ...
```

`parse_process_identity` accepts exactly the two versioned shapes above plus the exact legacy
Linux `{pid,startTicks,bootId}` shape. Unknown fields, bool-as-int PIDs, nonpositive PIDs, empty
identity strings, malformed decimals, and unknown schema/backend values return no identity.
`owner_absence` returns UNKNOWN for malformed input, failed identification, or backend mismatch;
the backend owns only same-backend presence/absence decisions (AR-21).

### Atomic Write Contract

```python
def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Durably replace a contained local file or raise without discarding recovery evidence."""

def canonical_relative_path(root: Path, path: Path) -> str:
    """Return a validated project-relative path serialized with forward slashes."""

def resolve_durable_path(root: Path, value: str) -> Path:
    """Resolve a canonical or safely compatible legacy path within root."""
```

Writes create a same-directory temporary file, flush it, atomically replace the destination, and
attempt the strongest supported directory durability operation. Windows retries only WinError 32
(`ERROR_SHARING_VIOLATION`) and 33 (`ERROR_LOCK_VIOLATION`) using the single delay schedule
`(0.05, 0.10, 0.20, 0.40, 0.75)` seconds. Exhaustion leaves the transaction journal/recovery
images intact and raises a stable recoverable failure (AR-10).

Generic `ACCESS_DENIED`, permission-policy failures, invalid paths, nonexistent required parents,
validation failures, and unknown OS errors are never retried. No implementation falls back to
delete-then-rename (AR-10).

### Path Contract

Durable project-relative paths always use `/`, Unicode is preserved, and input must be a relative
nonempty path within the canonical root. Native Windows mutation is certified only on a fixed
local NTFS volume where every existing component from the workspace root through the target,
target parent, temporary sibling, or recovery-image path is not a reparse point. The current local
developer and deliberately launched processes are trusted; hostile concurrent local reparse
substitution is outside the certified threat model. Containment, volume, NTFS, and root-to-target
reparse checks repeat immediately before every atomic write and recovery action.

On Windows, each component rejects ASCII control
characters, `<>:"/\|?*`, trailing space/dot, and reserved device basenames including extensions
(`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`) case-insensitively. Absolute, drive,
device, alternate-data-stream, traversal, and root-escape forms are rejected (AR-11).

Within one transaction, every durable path also receives an NTFS-aware collision key: volume
identity, case-insensitive long-name parent path, and case-insensitive final component. Existing
targets that resolve to the same file identity or long-name form collide even when their serialized
strings differ. A collision blocks before mutation. This rule covers case aliases and 8.3 aliases
without creating a general-purpose Windows namespace abstraction.

Legacy backslash strings are accepted only on Windows, only when unambiguously relative, and only
after the same component and containment validation. They are normalized on the next authorized
write, never through an unsolicited migration. Existing invalid durable state blocks with an
actionable diagnostic (AR-11).

### Integration Points

- `transitions.py` delegates owner creation/absence and all atomic writes to the adapters.
- `codeops_state.py` and each other shipped mutating command run the shared mutation preflight at
  the command boundary; the filesystem adapter repeats check 10 at replacement/recovery time.
- `migration.py`, roadmap, outcomes, attestations, and other JSON/Markdown writers use the same
  atomic path.
- Generated feature, plan, worktree, and evidence names use the same component validator.
- Recovery request schemas accept legacy owner records but emit the versioned form (AR-9).

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Native process cannot be opened or queried | Return unknown; refuse stale takeover/recovery | AR-9 |
| PID exists with different creation identity | Prove prior owner absent through PID reuse | AR-9 |
| Legacy Linux owner is read on Linux | Validate using existing boot ID/start tick semantics | AR-9 |
| Owner backend does not match current native host | Return unknown; do not claim absence | AR-9 |
| Allowlisted Windows sharing failure persists | Exhaust bounded retry, retain recovery state, fail closed | AR-10 |
| Workspace is not fixed local NTFS or has a reparse component | Preflight BLOCKED before mutation | AR-10, AR-11 |
| Durable path is unsafe, platform-invalid, or aliases another transaction path | Reject before filesystem access; do not rewrite | AR-11 |
| Directory durability operation is unavailable | Record the certified platform behavior; never report stronger durability than was achieved | AR-10 |

## Testing Requirements

- Specification tests cover ST-13–ST-27, ST-37, and ST-41–ST-45.
- Windows API tests use a narrow injectable adapter; native Windows CI executes real current,
  absent, PID-reuse, concurrent-owner, and recovery scenarios.
- Existing Linux state specification tests stay immutable and green.
- Concurrency tests use multiple real processes and real local files rather than mocks.
- Fault injection covers every boundary before/after temporary write, replace, journal update,
  validation, cleanup, and recovery takeover.
