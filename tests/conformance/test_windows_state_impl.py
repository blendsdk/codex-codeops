#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"

from scripts.codeops_state_lib.filesystem import atomic_write_bytes
from scripts.codeops_state_lib.models import (
    AbsenceState,
    LinuxProcessIdentity,
    WindowsProcessIdentity,
)
from scripts.codeops_state_lib.paths import VolumeInfo, validate_transaction_paths
from scripts.codeops_state_lib.processes import owner_absence
from scripts.codeops_state_lib.processes_windows import (
    CtypesWindowsProcessApi,
    PROCESS_QUERY_LIMITED_INFORMATION,
    WindowsProcessBackend,
)
from tests.conformance.test_windows_state_spec import (
    FakeAtomicWriteOps,
    FakePathProbe,
    windows_error,
)


class _Function:
    def __init__(self, implementation: object) -> None:
        self.implementation = implementation
        self.calls: list[tuple[object, ...]] = []
        self.argtypes: object = None
        self.restype: object = None

    def __call__(self, *args: object) -> object:
        self.calls.append(args)
        return self.implementation(*args)


class _Kernel:
    def __init__(self, *, query_succeeds: bool = True) -> None:
        self.OpenProcess = _Function(lambda access, inherit, pid: 777)

        def query(
            handle: object,
            creation: object,
            exit_time: object,
            kernel: object,
            user: object,
        ) -> int:
            del handle, exit_time, kernel, user
            creation._obj.low = 0x89ABCDEF
            creation._obj.high = 0x01234567
            return int(query_succeeds)

        self.GetProcessTimes = _Function(query)
        self.CloseHandle = _Function(lambda handle: 1)


class WindowsProcessImplementationTests(unittest.TestCase):
    def test_native_api_uses_least_privilege_and_closes_successful_handle(self) -> None:
        kernel = _Kernel()
        api = CtypesWindowsProcessApi(kernel)

        value = api.creation_file_time(42)

        expected = str((0x01234567 << 32) | 0x89ABCDEF)
        self.assertEqual(value, expected)
        self.assertEqual(
            kernel.OpenProcess.calls,
            [(PROCESS_QUERY_LIMITED_INFORMATION, False, 42)],
        )
        self.assertEqual(kernel.CloseHandle.calls, [(777,)])

    def test_native_api_closes_handle_when_query_fails(self) -> None:
        kernel = _Kernel(query_succeeds=False)
        api = CtypesWindowsProcessApi(kernel)

        with mock.patch.object(api, "_last_error", return_value=5):
            with self.assertRaises(OSError):
                api.creation_file_time(42)

        self.assertEqual(kernel.CloseHandle.calls, [(777,)])

    def test_foreign_backend_and_access_failure_remain_unknown(self) -> None:
        class AccessDenied:
            def creation_file_time(self, pid: int) -> str:
                del pid
                raise OSError(5, "access denied")

        backend = WindowsProcessBackend(AccessDenied())
        linux = LinuxProcessIdentity(42, "10", "boot").to_payload()
        windows = WindowsProcessIdentity(42, "10").to_payload()

        self.assertIs(owner_absence(linux, backend), AbsenceState.UNKNOWN)
        self.assertIs(owner_absence(windows, backend), AbsenceState.UNKNOWN)


class WindowsPathImplementationTests(unittest.TestCase):
    def test_alias_and_reparse_checks_run_before_any_target_exists(self) -> None:
        volume = VolumeInfo("volume", "NTFS", True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            nested = root / "safe" / "junction"
            nested.mkdir(parents=True)
            first = nested / "Report.json"
            alias = nested / "REPORT.JSON"
            probe = FakePathProbe(volume, reparses={"junction"})

            with self.assertRaises(OSError):
                validate_transaction_paths(root, (first, alias), probe=probe)

            self.assertFalse(first.exists())
            self.assertFalse(alias.exists())

    def test_8dot3_and_file_identity_collisions_are_independent(self) -> None:
        volume = VolumeInfo("volume", "NTFS", True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            short = root / "REPORT~1.JSON"
            long = root / "quarterly-report.json"
            identity_a = root / "one.json"
            identity_b = root / "two.json"
            probes = (
                FakePathProbe(
                    volume,
                    long_names={
                        short.name: long.name,
                        long.name: long.name,
                    },
                ),
                FakePathProbe(
                    volume,
                    identities={identity_a.name: (4, 9), identity_b.name: (4, 9)},
                ),
            )
            for pair, probe in zip(
                ((short, long), (identity_a, identity_b)),
                probes,
            ):
                with self.subTest(pair=pair), self.assertRaises(ValueError):
                    validate_transaction_paths(root, pair, probe=probe)


class AtomicWriteImplementationTests(unittest.TestCase):
    def test_only_winerror_32_and_33_retry(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            for code in (5, 87, 123, None):
                with self.subTest(code=code):
                    target = Path(raw) / f"state-{code}.json"
                    target.write_bytes(b"before")
                    error = OSError("generic") if code is None else windows_error(code)
                    ops = FakeAtomicWriteOps([error])
                    with self.assertRaises(OSError):
                        atomic_write_bytes(target, b"after", ops=ops)
                    self.assertEqual(ops.events.count("replace"), 1)
                    self.assertFalse(
                        any(isinstance(event, tuple) for event in ops.events)
                    )

    def test_each_retry_revalidates_and_uses_the_fixed_schedule(self) -> None:
        outcomes = [windows_error(32), windows_error(33), None]
        ops = FakeAtomicWriteOps(outcomes)
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "state.json"
            target.write_bytes(b"before")
            atomic_write_bytes(target, b"after", ops=ops)

        self.assertEqual(ops.events.count("revalidate"), 3)
        self.assertEqual(
            [event for event in ops.events if isinstance(event, tuple)],
            [("sleep", 0.05), ("sleep", 0.10)],
        )

    def test_faults_at_every_atomic_boundary_cleanup_without_delete_fallback(self) -> None:
        class BoundaryOps(FakeAtomicWriteOps):
            def __init__(self, boundary: str) -> None:
                super().__init__()
                self.boundary = boundary

            def write_temporary_sibling(self, path: Path, data: bytes) -> Path:
                if self.boundary == "temporary":
                    raise OSError("temporary failed")
                return super().write_temporary_sibling(path, data)

            def revalidate(self, path: Path, temporary: Path) -> None:
                super().revalidate(path, temporary)
                if self.boundary == "revalidate":
                    raise OSError("validation failed")

            def replace(self, temporary: Path, path: Path) -> None:
                if self.boundary == "replace":
                    self.events.append("replace")
                    raise OSError("replacement failed")
                super().replace(temporary, path)

            def sync_directory(self, parent: Path) -> None:
                super().sync_directory(parent)
                if self.boundary == "sync":
                    raise OSError("directory sync failed")

        with tempfile.TemporaryDirectory() as raw:
            for boundary in ("temporary", "revalidate", "replace", "sync"):
                with self.subTest(boundary=boundary):
                    target = Path(raw) / f"{boundary}.json"
                    target.write_bytes(b"before")
                    ops = BoundaryOps(boundary)
                    with self.assertRaises(OSError):
                        atomic_write_bytes(target, b"after", ops=ops)
                    if ops.temporary is not None:
                        self.assertFalse(ops.temporary.exists())
                    expected = b"after" if boundary == "sync" else b"before"
                    self.assertEqual(target.read_bytes(), expected)


class StateCommandBoundaryImplementationTests(unittest.TestCase):
    def test_direct_mutation_without_plugin_authority_blocks_before_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            request = root / "request.json"
            request.write_text(
                json.dumps({"schema": 1, "operationId": "blocked"}),
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment.pop("PLUGIN_ROOT", None)
            environment.pop("PLUGIN_DATA", None)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "transition",
                    "--root",
                    str(root),
                    "--request",
                    str(request),
                ],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "CodeOps state mutation prerequisites are unavailable.\n",
            )
            self.assertFalse((root / "codeops").exists())


if __name__ == "__main__":
    unittest.main()
