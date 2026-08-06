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

```python
@dataclass(frozen=True)
class ProcessIdentity:
    schema_version: int
    backend: str
    pid: int
    started_at: str
    host_epoch: str

class ProcessProbe(Protocol):
    def current(self) -> ProcessIdentity | None:
        """Return a stable identity or None when it cannot be proven."""

    def is_absent(self, identity: ProcessIdentity) -> bool | None:
        """Return True only when absence or PID reuse is proven."""
```

New records serialize `{schemaVersion, backend, pid, startedAt, hostEpoch}`. Linux reads the
existing unversioned `{pid,startTicks,bootId}` shape as a legacy Linux identity and continues to
write the versioned form after rollout. Windows uses the process creation timestamp returned by
`GetProcessTimes`; a boot/session epoch is derived from native system uptime plus current wall
clock and stored in a stable normalized representation. Handles are opened with the least access
needed and always closed. Access denied, malformed values, clock ambiguity, API failure, or
backend mismatch returns unknown rather than absent (AR-9).

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
attempt the strongest supported directory durability operation. Windows retries only known
sharing/access violations caused by a transient handle conflict. The policy uses a small fixed
attempt schedule owned by one constant and is bounded to at most two seconds total. Exhaustion
leaves the transaction journal/recovery images intact and raises a stable recoverable failure
(AR-10).

Permission-policy failures, invalid paths, nonexistent required parents, validation failures, and
unknown OS errors are never retried. No implementation falls back to delete-then-rename (AR-10).

### Path Contract

Durable project-relative paths always use `/`, Unicode is preserved, and input must be a relative
nonempty path within the canonical root. On Windows, each component rejects ASCII control
characters, `<>:"/\|?*`, trailing space/dot, and reserved device basenames including extensions
(`CON`, `PRN`, `AUX`, `NUL`, `COM1`-`COM9`, `LPT1`-`LPT9`) case-insensitively. Absolute, drive,
device, alternate-data-stream, traversal, and root-escape forms are rejected (AR-11).

Legacy backslash strings are accepted only on Windows, only when unambiguously relative, and only
after the same component and containment validation. They are normalized on the next authorized
write, never through an unsolicited migration. Existing invalid durable state blocks with an
actionable diagnostic (AR-11).

### Integration Points

- `transitions.py` delegates owner creation/absence and all atomic writes to the adapters.
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
| Atomic replacement is unsupported on probed filesystem | Preflight BLOCKED before mutation | AR-10 |
| Durable path is unsafe or platform-invalid | Reject before filesystem access; do not rewrite | AR-11 |
| Directory durability operation is unavailable | Record the certified platform behavior; never report stronger durability than was achieved | AR-10 |

## Testing Requirements

- Specification tests cover ST-13–ST-20 and ST-37–ST-45.
- Windows API tests use a narrow injectable adapter; native Windows CI executes real current,
  absent, PID-reuse, concurrent-owner, and recovery scenarios.
- Existing Linux state specification tests stay immutable and green.
- Concurrency tests use multiple real processes and real local files rather than mocks.
- Fault injection covers every boundary before/after temporary write, replace, journal update,
  validation, cleanup, and recovery takeover.
