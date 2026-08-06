#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest


ROOT = Path(__file__).resolve().parents[2]

from scripts.codeops_state_lib.filesystem import atomic_write_bytes
from scripts.codeops_state_lib.models import AbsenceState
from scripts.codeops_state_lib.processes import owner_absence
from scripts.codeops_state_lib.processes_windows import WindowsProcessBackend
from scripts.codeops_state_lib.transitions import recover


@unittest.skipUnless(os.name == "nt", "native process and NTFS integration requires Windows")
class NativeWindowsStateIntegrationTests(unittest.TestCase):
    def child(self, seconds: int = 30) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [sys.executable, "-c", f"import time; time.sleep({seconds})"],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def assert_owner_eventually_absent(
        self,
        payload: dict[str, object],
        backend: WindowsProcessBackend,
    ) -> None:
        deadline = time.monotonic() + 3
        observed = owner_absence(payload, backend)
        while observed is not AbsenceState.ABSENT and time.monotonic() < deadline:
            time.sleep(0.05)
            observed = owner_absence(payload, backend)
        self.assertIs(observed, AbsenceState.ABSENT)

    def test_real_concurrent_process_owners_are_present_then_absent(self) -> None:
        backend = WindowsProcessBackend()
        children = [self.child() for _ in range(3)]
        identities = []
        try:
            for child in children:
                identity = backend.identify(child.pid)
                self.assertIsNotNone(identity)
                identities.append(identity)
            for identity in identities:
                self.assertIs(
                    owner_absence(identity.to_payload(), backend),
                    AbsenceState.PRESENT,
                )
        finally:
            for child in children:
                child.terminate()
            for child in children:
                child.wait(timeout=10)
                child._handle.Close()
        for identity in identities:
            self.assert_owner_eventually_absent(identity.to_payload(), backend)

    def test_real_stale_owner_allows_recovery_takeover(self) -> None:
        backend = WindowsProcessBackend()
        child = self.child()
        identity = backend.identify(child.pid)
        self.assertIsNotNone(identity)
        child.terminate()
        child.wait(timeout=10)
        child._handle.Close()
        self.assert_owner_eventually_absent(identity.to_payload(), backend)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            state = root / "codeops" / ".state-transactions"
            state.mkdir(parents=True)
            operation = "native-stale-owner"
            nonce = "native-nonce"
            lock = state / f"{operation}.lock"
            lock.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "operationId": operation,
                        "nonce": nonce,
                        "owner": identity.to_payload(),
                    }
                ),
                encoding="utf-8",
            )
            request = root / "recovery.json"
            request.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "operationId": operation,
                        "direction": "roll-forward",
                        "expectedLock": nonce,
                        "expectedOwner": identity.to_payload(),
                        "graphs": [],
                    }
                ),
                encoding="utf-8",
            )

            code, result = recover(root, request)

            self.assertEqual(code, 0, result)
            self.assertEqual(result["result"], "recovered")
            self.assertFalse(lock.exists())
            self.assertTrue((state / f"{operation}.completed.json").is_file())

    def test_abrupt_writer_termination_never_tears_destination(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "state.bin"
            before = b"before-state"
            target.write_bytes(before)
            payload_size = 2 * 1024 * 1024
            code = (
                "from pathlib import Path\n"
                "from scripts.codeops_state_lib.filesystem import atomic_write_bytes\n"
                f"p=Path({str(target)!r})\n"
                f"data=b'x'*{payload_size}\n"
                "for _ in range(100): atomic_write_bytes(p,data)\n"
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT)
            child = subprocess.Popen(
                [sys.executable, "-c", code],
                env=environment,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.05)
            child.terminate()
            child.wait(timeout=10)

            observed = target.read_bytes()
            self.assertTrue(
                observed == before
                or (len(observed) == payload_size and set(observed) == {ord("x")})
            )

    def test_concurrent_real_file_writers_publish_only_complete_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            targets = tuple(root / f"state-{index}.bin" for index in range(6))
            values = tuple(bytes([65 + index]) * 131072 for index in range(6))
            errors: list[BaseException] = []

            def write(path: Path, value: bytes) -> None:
                try:
                    atomic_write_bytes(path, value)
                except BaseException as exc:
                    errors.append(exc)

            threads = [
                threading.Thread(target=write, args=pair)
                for pair in zip(targets, values)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=15)

            self.assertFalse(errors)
            self.assertEqual(
                tuple(path.read_bytes() for path in targets),
                values,
            )


if __name__ == "__main__":
    unittest.main()
