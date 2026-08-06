"""Portable process-owner identity contract for state recovery decisions."""

from __future__ import annotations

from pathlib import Path
import os
from typing import Protocol, runtime_checkable

from .models import (
    AbsenceState,
    LinuxProcessIdentity,
    WindowsProcessIdentity,
)


ProcessIdentity = LinuxProcessIdentity | WindowsProcessIdentity


@runtime_checkable
class ProcessBackend(Protocol):
    """Host adapter that proves presence or absence for one identity backend."""

    backend_name: str

    def identify(self, pid: int) -> ProcessIdentity | None: ...

    def absence(self, identity: ProcessIdentity) -> AbsenceState: ...


class LinuxProcBackend:
    """Linux owner proof using the existing procfs start-tick and boot-ID rules."""

    backend_name = "linux-proc"

    def __init__(self, proc_root: Path = Path("/proc")) -> None:
        self.proc_root = proc_root

    def identify(self, pid: int) -> LinuxProcessIdentity | None:
        if _positive_pid(pid) is None:
            return None
        stat = self.proc_root / str(pid) / "stat"
        boot = self.proc_root / "sys/kernel/random/boot_id"
        try:
            fields = stat.read_text(encoding="utf-8").split()
            return LinuxProcessIdentity(
                pid,
                fields[21],
                boot.read_text(encoding="utf-8").strip(),
            )
        except (OSError, IndexError):
            return None

    def absence(self, identity: ProcessIdentity) -> AbsenceState:
        if not isinstance(identity, LinuxProcessIdentity):
            return AbsenceState.UNKNOWN
        if not self.proc_root.is_dir():
            return AbsenceState.UNKNOWN
        try:
            boot_id = (self.proc_root / "sys/kernel/random/boot_id").read_text(
                encoding="utf-8"
            ).strip()
        except OSError:
            return AbsenceState.UNKNOWN
        if boot_id != identity.boot_id:
            return AbsenceState.ABSENT
        stat = self.proc_root / str(identity.pid) / "stat"
        try:
            fields = stat.read_text(encoding="utf-8").split()
        except FileNotFoundError:
            return AbsenceState.ABSENT
        except OSError:
            return AbsenceState.UNKNOWN
        try:
            if fields[21] != identity.start_ticks:
                return AbsenceState.ABSENT
        except IndexError:
            return AbsenceState.UNKNOWN
        return AbsenceState.PRESENT


def _positive_pid(value: object) -> int | None:
    if type(value) is not int or value <= 0:
        return None
    return value


def _decimal(value: object) -> str | None:
    if not isinstance(value, str) or not value or not value.isascii():
        return None
    if not value.isdecimal():
        return None
    return value


def _nonempty_text(value: object) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return value


def parse_process_identity(payload: object) -> ProcessIdentity | None:
    """Parse the exact versioned identity shapes or the exact legacy Linux shape."""

    if not isinstance(payload, dict):
        return None
    keys = set(payload)
    legacy_keys = {"pid", "startTicks", "bootId"}
    linux_keys = {"schemaVersion", "backend", *legacy_keys}
    windows_keys = {
        "schemaVersion",
        "backend",
        "pid",
        "creationFileTime",
    }
    pid = _positive_pid(payload.get("pid"))
    if pid is None:
        return None
    if keys == legacy_keys:
        start_ticks = _decimal(payload.get("startTicks"))
        boot_id = _nonempty_text(payload.get("bootId"))
        if start_ticks is None or boot_id is None:
            return None
        return LinuxProcessIdentity(pid, start_ticks, boot_id)
    if type(payload.get("schemaVersion")) is not int:
        return None
    if payload.get("schemaVersion") != 1:
        return None
    backend = payload.get("backend")
    if keys == linux_keys and backend == "linux-proc":
        start_ticks = _decimal(payload.get("startTicks"))
        boot_id = _nonempty_text(payload.get("bootId"))
        if start_ticks is None or boot_id is None:
            return None
        return LinuxProcessIdentity(pid, start_ticks, boot_id)
    if keys == windows_keys and backend == "windows-filetime":
        creation_time = _decimal(payload.get("creationFileTime"))
        if creation_time is None:
            return None
        return WindowsProcessIdentity(pid, creation_time)
    return None


def current_process_identity(
    backend: ProcessBackend,
    pid: int,
) -> ProcessIdentity | None:
    """Identify a process through the selected backend, closing failures to no identity."""

    if _positive_pid(pid) is None:
        return None
    try:
        identity = backend.identify(pid)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(identity, (LinuxProcessIdentity, WindowsProcessIdentity)):
        return None
    if identity.pid != pid:
        return None
    return identity


def owner_absence(payload: object, backend: ProcessBackend) -> AbsenceState:
    """Return absence only when the matching host backend proves it."""

    identity = parse_process_identity(payload)
    expected_backend = {
        LinuxProcessIdentity: "linux-proc",
        WindowsProcessIdentity: "windows-filetime",
    }
    if identity is None or backend.backend_name != expected_backend[type(identity)]:
        return AbsenceState.UNKNOWN
    try:
        result = backend.absence(identity)
    except (OSError, ValueError, TypeError):
        return AbsenceState.UNKNOWN
    if not isinstance(result, AbsenceState):
        return AbsenceState.UNKNOWN
    return result


def native_process_backend() -> ProcessBackend:
    """Return the process backend for the current native host."""

    if os.name == "nt":
        from .processes_windows import WindowsProcessBackend

        return WindowsProcessBackend()
    return LinuxProcBackend()
