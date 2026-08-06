#!/usr/bin/env python3
from __future__ import annotations

import importlib
import unittest
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def contract() -> tuple[Any, Any]:
    """Load only the planned portable process-identity contract."""
    models = importlib.import_module("scripts.codeops_state_lib.models")
    processes = importlib.import_module("scripts.codeops_state_lib.processes")
    return models, processes


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


if __name__ == "__main__":
    unittest.main()
