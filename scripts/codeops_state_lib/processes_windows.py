"""Native Windows process identity through least-privilege kernel APIs."""

from __future__ import annotations

import ctypes
import os
from typing import Protocol

from .models import AbsenceState, WindowsProcessIdentity


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_PARAMETER = 87
ERROR_NOT_FOUND = 1168


class ProcessMissingError(OSError):
    """The queried PID no longer identifies a process."""


class WindowsProcessApi(Protocol):
    """Narrow injectable Windows API boundary used by the owner backend."""

    def creation_file_time(self, pid: int) -> str: ...


class FILETIME(ctypes.Structure):
    _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]


class CtypesWindowsProcessApi:
    """ctypes binding that always closes an opened process handle."""

    def __init__(self, kernel32: object | None = None) -> None:
        if kernel32 is None:
            if os.name != "nt":
                raise OSError("Windows process APIs are unavailable on this host")
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel32 = kernel32
        self._configure_signatures()

    def _configure_signatures(self) -> None:
        try:
            self._kernel32.OpenProcess.argtypes = [
                ctypes.c_uint32,
                ctypes.c_int,
                ctypes.c_uint32,
            ]
            self._kernel32.OpenProcess.restype = ctypes.c_void_p
            self._kernel32.GetProcessTimes.argtypes = [
                ctypes.c_void_p,
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
                ctypes.POINTER(FILETIME),
            ]
            self._kernel32.GetProcessTimes.restype = ctypes.c_int
            self._kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            self._kernel32.CloseHandle.restype = ctypes.c_int
        except AttributeError:
            # Injectable test doubles may expose ordinary Python callables.
            pass

    @staticmethod
    def _last_error() -> int:
        getter = getattr(ctypes, "get_last_error", None)
        return int(getter()) if getter is not None else 0

    @staticmethod
    def _raise_api_error(operation: str, code: int) -> None:
        if code in {ERROR_INVALID_PARAMETER, ERROR_NOT_FOUND}:
            raise ProcessMissingError(code, f"{operation} could not find the process")
        raise OSError(code, f"{operation} failed")

    def creation_file_time(self, pid: int) -> str:
        handle = self._kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            pid,
        )
        if not handle:
            self._raise_api_error("OpenProcess", self._last_error())
        creation = FILETIME()
        exit_time = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        try:
            succeeded = self._kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation),
                ctypes.byref(exit_time),
                ctypes.byref(kernel),
                ctypes.byref(user),
            )
            if not succeeded:
                self._raise_api_error("GetProcessTimes", self._last_error())
            value = (int(creation.high) << 32) | int(creation.low)
            return str(value)
        finally:
            self._kernel32.CloseHandle(handle)


class WindowsProcessBackend:
    """Fail-closed Windows presence and PID-reuse decisions."""

    backend_name = "windows-filetime"

    def __init__(self, api: WindowsProcessApi | None = None) -> None:
        self.api = api if api is not None else CtypesWindowsProcessApi()

    def identify(self, pid: int) -> WindowsProcessIdentity | None:
        if type(pid) is not int or pid <= 0:
            return None
        try:
            creation_time = self.api.creation_file_time(pid)
        except (ProcessMissingError, OSError):
            return None
        if not creation_time or not creation_time.isascii() or not creation_time.isdecimal():
            return None
        return WindowsProcessIdentity(pid, creation_time)

    def absence(self, identity: object) -> AbsenceState:
        if not isinstance(identity, WindowsProcessIdentity):
            return AbsenceState.UNKNOWN
        try:
            current = self.api.creation_file_time(identity.pid)
        except ProcessMissingError:
            return AbsenceState.ABSENT
        except OSError:
            return AbsenceState.UNKNOWN
        if not current or not current.isascii() or not current.isdecimal():
            return AbsenceState.UNKNOWN
        if current == identity.creation_file_time:
            return AbsenceState.PRESENT
        return AbsenceState.ABSENT
