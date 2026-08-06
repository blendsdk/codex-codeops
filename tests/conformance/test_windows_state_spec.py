#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PATH_CASES = ROOT / "tests" / "fixtures" / "windows-state" / "path-cases.json"


def contract() -> tuple[Any, Any]:
    """Load only the planned portable process-identity contract."""
    models = importlib.import_module("scripts.codeops_state_lib.models")
    processes = importlib.import_module("scripts.codeops_state_lib.processes")
    return models, processes


def filesystem_contract() -> tuple[Any, Any]:
    """Load only the planned durable-path and atomic-write modules."""
    paths = importlib.import_module("scripts.codeops_state_lib.paths")
    filesystem = importlib.import_module("scripts.codeops_state_lib.filesystem")
    return paths, filesystem


def path_cases() -> dict[str, list[object]]:
    return json.loads(PATH_CASES.read_text(encoding="utf-8"))


class FakeProcessBackend:
    """Deterministic host boundary for owner-presence decisions."""

    def __init__(
        self,
        models: Any,
        backend_name: str,
        current: dict[int, object] | None = None,
        *,
        uncertain: bool = False,
    ) -> None:
        self.models = models
        self.backend_name = backend_name
        self.current = dict(current or {})
        self.uncertain = uncertain
        self.identified: list[int] = []
        self.checked: list[object] = []

    def identify(self, pid: int) -> object | None:
        self.identified.append(pid)
        if self.uncertain:
            raise OSError("process query unavailable")
        return self.current.get(pid)

    def absence(self, identity: object) -> object:
        self.checked.append(identity)
        if self.uncertain:
            return self.models.AbsenceState.UNKNOWN
        current = self.identify(identity.pid)
        if current is None:
            return self.models.AbsenceState.ABSENT
        if current == identity:
            return self.models.AbsenceState.PRESENT
        return self.models.AbsenceState.ABSENT


class FakePathProbe:
    """Deterministic Windows namespace and volume boundary."""

    is_windows = True

    def __init__(
        self,
        volume: object,
        *,
        reparses: set[str] | None = None,
        long_names: dict[str, str] | None = None,
        identities: dict[str, tuple[int, int]] | None = None,
    ) -> None:
        self.volume = volume
        self.reparses = {value.casefold() for value in reparses or set()}
        self.long_names = {
            key.casefold(): value for key, value in (long_names or {}).items()
        }
        self.identities = {
            key.casefold(): value for key, value in (identities or {}).items()
        }

    def canonical(self, path: Path) -> Path:
        return path.absolute()

    def volume_info(self, path: Path) -> object:
        del path
        return self.volume

    def existing_components(self, root: Path, target: Path) -> tuple[Path, ...]:
        components = [root]
        relative = target.relative_to(root)
        current = root
        for part in relative.parts:
            current = current / part
            if current.exists():
                components.append(current)
        return tuple(components)

    def is_reparse_point(self, path: Path) -> bool:
        return path.name.casefold() in self.reparses

    def long_name(self, path: Path) -> str:
        return self.long_names.get(path.name.casefold(), str(path))

    def file_identity(self, path: Path) -> tuple[int, int] | None:
        return self.identities.get(path.name.casefold())


class FakeAtomicWriteOps:
    """Scripted durable-writer boundary with observable policy calls."""

    def __init__(
        self,
        replace_outcomes: list[BaseException | None] | None = None,
        *,
        interrupt_stage: str | None = None,
    ) -> None:
        self.replace_outcomes = list(replace_outcomes or [None])
        self.interrupt_stage = interrupt_stage
        self.events: list[object] = []
        self.temporary: Path | None = None

    def write_temporary_sibling(self, path: Path, data: bytes) -> Path:
        self.events.append("write-temporary")
        temporary = path.with_name(f".{path.name}.spec.tmp")
        temporary.write_bytes(data)
        self.temporary = temporary
        return temporary

    def revalidate(self, path: Path, temporary: Path) -> None:
        del path, temporary
        self.events.append("revalidate")
        if self.interrupt_stage == "revalidate":
            raise KeyboardInterrupt("interrupted during revalidation")

    def replace(self, temporary: Path, path: Path) -> None:
        self.events.append("replace")
        if self.interrupt_stage == "replace":
            raise KeyboardInterrupt("interrupted during replacement")
        outcome = self.replace_outcomes.pop(0)
        if outcome is not None:
            raise outcome
        os.replace(temporary, path)

    def sync_directory(self, parent: Path) -> None:
        del parent
        self.events.append("sync-directory")

    def sleep(self, delay: float) -> None:
        self.events.append(("sleep", delay))

    def cleanup_temporary(self, temporary: Path) -> None:
        self.events.append("cleanup-temporary")
        temporary.unlink(missing_ok=True)


def windows_error(code: int) -> OSError:
    error = OSError(f"WinError {code}")
    error.winerror = code
    return error


class WindowsProcessIdentitySpecificationTests(unittest.TestCase):
    """Portable owner proof required by transition and recovery code."""

    def test_versioned_owner_payloads_are_closed_and_exact(self) -> None:
        models, processes = contract()
        windows = models.WindowsProcessIdentity(42, "133829001234567890")
        linux = models.LinuxProcessIdentity(42, "123", "boot-uuid")

        self.assertEqual(
            windows.to_payload(),
            {
                "schemaVersion": 1,
                "backend": "windows-filetime",
                "pid": 42,
                "creationFileTime": "133829001234567890",
            },
        )
        self.assertEqual(
            linux.to_payload(),
            {
                "schemaVersion": 1,
                "backend": "linux-proc",
                "pid": 42,
                "startTicks": "123",
                "bootId": "boot-uuid",
            },
        )
        self.assertEqual(processes.parse_process_identity(windows.to_payload()), windows)
        self.assertEqual(processes.parse_process_identity(linux.to_payload()), linux)

    def test_legacy_linux_owner_is_accepted_and_emits_versioned_form(self) -> None:
        models, processes = contract()
        legacy = {"pid": 19, "startTicks": "456", "bootId": "legacy-boot"}
        identity = processes.parse_process_identity(legacy)

        self.assertEqual(
            identity,
            models.LinuxProcessIdentity(19, "456", "legacy-boot"),
        )
        self.assertEqual(identity.to_payload()["backend"], "linux-proc")
        self.assertEqual(identity.to_payload()["schemaVersion"], 1)
        present = FakeProcessBackend(models, "linux-proc", {19: identity})
        different_boot = FakeProcessBackend(
            models,
            "linux-proc",
            {19: models.LinuxProcessIdentity(19, "456", "new-boot")},
        )
        self.assertEqual(
            processes.owner_absence(legacy, present),
            models.AbsenceState.PRESENT,
        )
        self.assertEqual(
            processes.owner_absence(legacy, different_boot),
            models.AbsenceState.ABSENT,
        )

    def test_malformed_or_open_ended_owner_payloads_are_rejected(self) -> None:
        models, processes = contract()
        valid_windows = {
            "schemaVersion": 1,
            "backend": "windows-filetime",
            "pid": 42,
            "creationFileTime": "133829001234567890",
        }
        invalid = (
            {**valid_windows, "extra": True},
            {**valid_windows, "schemaVersion": True},
            {**valid_windows, "schemaVersion": 2},
            {**valid_windows, "backend": "unknown"},
            {**valid_windows, "pid": True},
            {**valid_windows, "pid": 0},
            {**valid_windows, "pid": -1},
            {**valid_windows, "creationFileTime": ""},
            {**valid_windows, "creationFileTime": "12.5"},
            {**valid_windows, "creationFileTime": "-1"},
            {
                "schemaVersion": 1,
                "backend": "linux-proc",
                "pid": 42,
                "startTicks": "not-decimal",
                "bootId": "boot",
            },
            {"pid": 42, "startTicks": "123", "bootId": "", "extra": "x"},
            None,
            [],
        )

        for payload in invalid:
            with self.subTest(payload=payload):
                self.assertIsNone(processes.parse_process_identity(payload))
                self.assertEqual(
                    processes.owner_absence(
                        payload,
                        FakeProcessBackend(models, "windows-filetime"),
                    ),
                    models.AbsenceState.UNKNOWN,
                )

    def test_current_process_identity_uses_the_selected_backend(self) -> None:
        models, processes = contract()
        current = models.WindowsProcessIdentity(321, "10000001")
        backend = FakeProcessBackend(
            models,
            "windows-filetime",
            {321: current},
        )

        self.assertEqual(processes.current_process_identity(backend, 321), current)
        self.assertEqual(backend.identified, [321])
        self.assertIsNone(
            processes.current_process_identity(
                FakeProcessBackend(models, "windows-filetime", uncertain=True),
                321,
            )
        )

    def test_missing_pid_and_reused_pid_prove_the_recorded_owner_absent(self) -> None:
        models, processes = contract()
        recorded = models.WindowsProcessIdentity(700, "100")
        missing = FakeProcessBackend(models, "windows-filetime")
        reused = FakeProcessBackend(
            models,
            "windows-filetime",
            {700: models.WindowsProcessIdentity(700, "101")},
        )

        for backend in (missing, reused):
            with self.subTest(current=backend.current):
                self.assertEqual(
                    processes.owner_absence(recorded.to_payload(), backend),
                    models.AbsenceState.ABSENT,
                )

    def test_same_process_identity_proves_the_recorded_owner_present(self) -> None:
        models, processes = contract()
        recorded = models.WindowsProcessIdentity(701, "200")
        backend = FakeProcessBackend(
            models,
            "windows-filetime",
            {701: recorded},
        )

        self.assertEqual(
            processes.owner_absence(recorded.to_payload(), backend),
            models.AbsenceState.PRESENT,
        )

    def test_uncertain_or_foreign_owner_never_authorizes_takeover(self) -> None:
        models, processes = contract()
        windows = models.WindowsProcessIdentity(702, "300").to_payload()
        linux = models.LinuxProcessIdentity(702, "300", "boot").to_payload()
        uncertain = FakeProcessBackend(
            models,
            "windows-filetime",
            uncertain=True,
        )
        windows_backend = FakeProcessBackend(models, "windows-filetime")
        malformed = {**windows, "creationFileTime": "bad"}

        for payload, backend in (
            (windows, uncertain),
            (linux, windows_backend),
            (malformed, windows_backend),
        ):
            with self.subTest(payload=payload, backend=backend.backend_name):
                self.assertEqual(
                    processes.owner_absence(payload, backend),
                    models.AbsenceState.UNKNOWN,
                )

    def test_concurrent_owner_checks_preserve_one_recovery_decision(self) -> None:
        models, processes = contract()
        live = models.WindowsProcessIdentity(800, "400")
        stale = models.WindowsProcessIdentity(800, "399")
        backend = FakeProcessBackend(
            models,
            "windows-filetime",
            {800: live},
        )
        payloads = [live.to_payload(), stale.to_payload()] * 8

        with ThreadPoolExecutor(max_workers=8) as executor:
            decisions = list(
                executor.map(
                    lambda payload: processes.owner_absence(payload, backend),
                    payloads,
                )
            )

        self.assertEqual(decisions.count(models.AbsenceState.PRESENT), 8)
        self.assertEqual(decisions.count(models.AbsenceState.ABSENT), 8)
        self.assertNotIn(models.AbsenceState.UNKNOWN, decisions)

    def test_recovery_requires_proven_absence_and_exact_owner_binding(self) -> None:
        models, processes = contract()
        expected = models.WindowsProcessIdentity(900, "500")
        reused = FakeProcessBackend(
            models,
            "windows-filetime",
            {900: models.WindowsProcessIdentity(900, "501")},
        )
        uncertain = FakeProcessBackend(
            models,
            "windows-filetime",
            uncertain=True,
        )

        def recovery_is_authorized(payload: object, backend: object) -> bool:
            return (
                payload == expected.to_payload()
                and processes.owner_absence(payload, backend)
                is models.AbsenceState.ABSENT
            )

        self.assertTrue(recovery_is_authorized(expected.to_payload(), reused))
        self.assertFalse(recovery_is_authorized(expected.to_payload(), uncertain))
        self.assertFalse(
            recovery_is_authorized(
                models.WindowsProcessIdentity(900, "499").to_payload(),
                reused,
            )
        )


class WindowsDurablePathSpecificationTests(unittest.TestCase):
    """Closed durable-path grammar and native containment requirements."""

    def test_canonical_paths_use_forward_slashes_and_round_trip_unicode(self) -> None:
        paths, _ = filesystem_contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            for case in path_cases()["canonical"]:
                with self.subTest(case=case):
                    target = root.joinpath(*case["native"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"state")
                    durable = paths.canonical_relative_path(root, target)
                    self.assertEqual(durable, case["durable"])
                    self.assertNotIn("\\", durable)
                    self.assertEqual(paths.resolve_durable_path(root, durable), target)

    @unittest.skipUnless(os.name == "nt", "legacy backslashes are Windows-only")
    def test_safe_legacy_backslashes_resolve_without_rewriting_stored_text(self) -> None:
        paths, _ = filesystem_contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            for case in path_cases()["legacy"]:
                with self.subTest(case=case):
                    stored = case["durable"]
                    target = root.joinpath(*case["native"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"legacy")
                    self.assertEqual(paths.resolve_durable_path(root, stored), target)
                    self.assertIn("\\", stored)

    def test_hostile_or_out_of_root_paths_are_rejected_before_access(self) -> None:
        paths, _ = filesystem_contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            outside = root.parent / "outside-state.json"
            for value in path_cases()["hostile"]:
                with self.subTest(value=value):
                    with self.assertRaises((ValueError, OSError)):
                        paths.resolve_durable_path(root, value)
            with self.assertRaises((ValueError, OSError)):
                paths.canonical_relative_path(root, outside)
            self.assertFalse(outside.exists())

    @unittest.skipUnless(os.name == "nt", "reserved components are Windows-only")
    def test_reserved_device_names_are_rejected_case_insensitively(self) -> None:
        paths, _ = filesystem_contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            for component in path_cases()["reserved"]:
                with self.subTest(component=component):
                    with self.assertRaises((ValueError, OSError)):
                        paths.resolve_durable_path(root, f"state/{component}")

    def test_case_long_name_and_file_identity_aliases_block_the_whole_set(self) -> None:
        paths, _ = filesystem_contract()
        volume = paths.VolumeInfo("volume-1", "NTFS", True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            first = root / "data" / "Report.json"
            second = root / "DATA" / "REPORT.JSON"
            short = root / "reports" / "REPORT~1.JSON"
            long = root / "reports" / "quarterly-report.json"
            identity_a = root / "identity" / "one.json"
            identity_b = root / "identity" / "two.json"
            for path in (first, second, short, long, identity_a, identity_b):
                path.parent.mkdir(parents=True, exist_ok=True)

            probes = (
                FakePathProbe(volume),
                FakePathProbe(
                    volume,
                    long_names={
                        "REPORT~1.JSON": "quarterly-report.json",
                        "quarterly-report.json": "quarterly-report.json",
                    },
                ),
                FakePathProbe(
                    volume,
                    identities={"one.json": (12, 34), "two.json": (12, 34)},
                ),
            )
            pairs = ((first, second), (short, long), (identity_a, identity_b))
            for pair, probe in zip(pairs, probes):
                with self.subTest(pair=pair):
                    with self.assertRaises((ValueError, OSError)):
                        paths.validate_transaction_paths(root, pair, probe=probe)
                    self.assertFalse(any(path.exists() for path in pair))

    def test_non_ntfs_or_nonlocal_volume_refuses_the_complete_transaction(self) -> None:
        paths, _ = filesystem_contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            targets = (root / "one.json", root / "two.json")
            volumes = (
                paths.VolumeInfo("volume-fat", "FAT32", True),
                paths.VolumeInfo("volume-network", "NTFS", False),
            )
            for volume in volumes:
                with self.subTest(volume=volume):
                    with self.assertRaises((ValueError, OSError)):
                        paths.validate_transaction_paths(
                            root,
                            targets,
                            probe=FakePathProbe(volume),
                        )
                    self.assertFalse(any(path.exists() for path in targets))

    def test_transaction_paths_preserve_order_and_reject_any_nested_reparse(self) -> None:
        paths, _ = filesystem_contract()
        volume = paths.VolumeInfo("volume-1", "NTFS", True)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            nested = root / "safe" / "nested"
            nested.mkdir(parents=True)
            targets = (nested / "first.json", root / "second.json")
            clean = FakePathProbe(volume)
            blocked = FakePathProbe(volume, reparses={"nested"})

            self.assertEqual(
                paths.validate_transaction_paths(root, targets, probe=clean),
                targets,
            )
            with self.assertRaises((ValueError, OSError)):
                paths.validate_transaction_paths(root, targets, probe=blocked)
            self.assertFalse(any(path.exists() for path in targets))


class WindowsAtomicWriteSpecificationTests(unittest.TestCase):
    """Exact bounded replacement and interruption policy."""

    def target(self, root: str) -> Path:
        path = Path(root) / "state.json"
        path.write_bytes(b"before")
        return path

    def test_sharing_and_lock_violations_use_the_exact_retry_schedule(self) -> None:
        _, filesystem = filesystem_contract()
        outcomes = [
            windows_error(32),
            windows_error(33),
            windows_error(32),
            windows_error(33),
            windows_error(32),
            None,
        ]
        ops = FakeAtomicWriteOps(outcomes)
        with tempfile.TemporaryDirectory() as raw:
            target = self.target(raw)
            filesystem.atomic_write_bytes(target, b"after", ops=ops)
            result = target.read_bytes()

        self.assertEqual(result, b"after")
        self.assertEqual(
            [event for event in ops.events if isinstance(event, tuple)],
            [
                ("sleep", 0.05),
                ("sleep", 0.10),
                ("sleep", 0.20),
                ("sleep", 0.40),
                ("sleep", 0.75),
            ],
        )
        self.assertEqual(ops.events.count("revalidate"), 6)
        self.assertEqual(ops.events.count("replace"), 6)
        self.assertEqual(ops.events[:2], ["write-temporary", "revalidate"])
        for index, event in enumerate(ops.events):
            if event == "replace":
                self.assertEqual(ops.events[index - 1], "revalidate")

    def test_persistent_sharing_failure_preserves_destination_and_cleans_temp(self) -> None:
        _, filesystem = filesystem_contract()
        ops = FakeAtomicWriteOps([windows_error(32) for _ in range(6)])
        with tempfile.TemporaryDirectory() as raw:
            target = self.target(raw)
            with self.assertRaises(OSError):
                filesystem.atomic_write_bytes(target, b"after", ops=ops)
            self.assertEqual(target.read_bytes(), b"before")
            self.assertFalse(ops.temporary.exists())

        self.assertEqual(ops.events.count("replace"), 6)
        self.assertEqual(ops.events.count("cleanup-temporary"), 1)
        self.assertEqual(
            [event for event in ops.events if isinstance(event, tuple)],
            [("sleep", delay) for delay in (0.05, 0.10, 0.20, 0.40, 0.75)],
        )

    def test_generic_access_denial_is_not_retried_or_deleted_around(self) -> None:
        _, filesystem = filesystem_contract()
        ops = FakeAtomicWriteOps([windows_error(5)])
        with tempfile.TemporaryDirectory() as raw:
            target = self.target(raw)
            with self.assertRaises(OSError):
                filesystem.atomic_write_bytes(target, b"after", ops=ops)
            self.assertEqual(target.read_bytes(), b"before")
            self.assertFalse(ops.temporary.exists())

        self.assertEqual(ops.events.count("replace"), 1)
        self.assertFalse(any(isinstance(event, tuple) for event in ops.events))
        self.assertEqual(ops.events.count("cleanup-temporary"), 1)

    def test_base_exception_propagates_after_best_effort_temp_cleanup(self) -> None:
        _, filesystem = filesystem_contract()
        for stage in ("revalidate", "replace"):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as raw:
                target = self.target(raw)
                ops = FakeAtomicWriteOps(interrupt_stage=stage)
                with self.assertRaises(KeyboardInterrupt):
                    filesystem.atomic_write_bytes(target, b"after", ops=ops)
                self.assertEqual(target.read_bytes(), b"before")
                self.assertFalse(ops.temporary.exists())
                self.assertEqual(ops.events.count("cleanup-temporary"), 1)


if __name__ == "__main__":
    unittest.main()
