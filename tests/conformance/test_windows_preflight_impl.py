#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codeops_platform.hosts import HostKind, classify_process_host
from scripts.codeops_windows_lib.attestation import AttestationStore
from scripts.codeops_windows_lib.models import CheckResult, PreflightResult, Readiness
from scripts.codeops_windows_lib.probes import NativeProbeDependencies
from scripts.codeops_windows_preflight import PreflightInputError, run_preflight


CHECK_CODES = (
    "native-windows",
    "windows-version",
    "python-3",
    "git-for-windows",
    "workspace-local",
    "codex-native",
    "sandbox",
    "plugin-enabled",
    "hooks-available",
    "path-filesystem",
)


class ReadyDependencies:
    """Minimal successful dependency used to prove input rejection boundaries."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def classify_host(self, environment: dict[str, str]) -> str:
        del environment
        self.calls.append("classify")
        return "native-windows"

    def evaluate_check(self, code: str, request: dict[str, object]) -> CheckResult:
        del request
        self.calls.append(code)
        return CheckResult(code, Readiness.READY, code, None)

    def load_attestation(self, request: dict[str, object]) -> None:
        del request
        return None

    def store_attestation(
        self,
        request: dict[str, object],
        result: PreflightResult,
    ) -> None:
        del request, result
        self.calls.append("store")

    def cleanup_attestations(self, request: dict[str, object]) -> None:
        del request
        self.calls.append("cleanup")


class WindowsPreflightImplementationTests(unittest.TestCase):
    """Implementation-level checks for adapters, storage, and hostile inputs."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="codeops-preflight-")
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / "workspace"
        self.plugin_root = self.base / "plugin"
        self.plugin_data = self.base / "plugin data"
        self.root.mkdir()
        self.plugin_data.mkdir()
        (self.plugin_root / ".codex-plugin").mkdir(parents=True)
        (self.plugin_root / "hooks").mkdir()
        (self.plugin_root / ".codex-plugin" / "plugin.json").write_text(
            json.dumps({"name": "codeops", "version": "1.2.3"}),
            encoding="utf-8",
        )
        (self.plugin_root / "hooks" / "hooks.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        event: [
                            {
                                "hooks": [
                                    {
                                        "command": (
                                            '"${PLUGIN_ROOT}/scripts/hook_session_context.sh"'
                                            if event == "SessionStart"
                                            else '"${PLUGIN_ROOT}/scripts/hook_marker_guard.sh"'
                                        ),
                                        "commandWindows": (
                                            'powershell.exe -NoProfile -File '
                                            '"$env:PLUGIN_ROOT/scripts/codeops-windows-hook.ps1" '
                                            f'-Event {event}'
                                        ),
                                    }
                                ]
                            }
                        ]
                        for event in ("SessionStart", "PreToolUse")
                    }
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, *, session_id: str = "session-1") -> dict[str, object]:
        return {
            "mode": "session",
            "entrypointCode": None,
            "hookEvent": "SessionStart",
            "targets": (),
            "root": self.root,
            "pluginRoot": self.plugin_root,
            "pluginData": self.plugin_data,
            "sessionId": session_id,
            "environment": {},
        }

    def result(self, *, session_id: str = "session-1") -> PreflightResult:
        checks = tuple(
            CheckResult(code, Readiness.READY, code, None) for code in CHECK_CODES
        )
        return PreflightResult(1, Readiness.READY, session_id, checks)

    def call(self, dependencies: ReadyDependencies, **overrides: object) -> PreflightResult:
        arguments: dict[str, object] = {
            "mode": "session",
            "entrypoint_code": None,
            "hook_event": "SessionStart",
            "targets": (),
            "root": self.root,
            "plugin_root": self.plugin_root,
            "plugin_data": self.plugin_data,
            "session_id": "session-1",
            "environment": {},
            "dependencies": dependencies,
        }
        arguments.update(overrides)
        return run_preflight(**arguments)  # type: ignore[arg-type]

    def test_host_classifier_is_passive_and_ignores_installed_wsl_facts(self) -> None:
        hostile = {"WSL_DISTRO_NAME": "Ubuntu; Remove-Item C:\\important"}
        with patch("subprocess.run") as run:
            native = classify_process_host(
                hostile,
                os_name="nt",
                system="Windows",
                release="11",
            )
            wsl = classify_process_host(
                hostile,
                os_name="posix",
                system="Linux",
                release="microsoft-standard-WSL2",
            )
        self.assertEqual(native, HostKind.NATIVE_WINDOWS)
        self.assertEqual(wsl, HostKind.WSL)
        run.assert_not_called()

    def test_closed_matrix_rejects_types_paths_and_unknown_fields_before_probes(self) -> None:
        cases = (
            {"mode": []},
            {"hook_event": []},
            {"entrypoint_code": []},
            {"targets": []},
            {"root": Path("relative")},
            {"environment": {"PATH": 7}},
            {"session_id": "../escape"},
            {"session_id": "x" * 129},
            {"mode": "mutation", "entrypoint_code": "state-transition", "targets": ()},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                dependencies = ReadyDependencies()
                with self.assertRaises(PreflightInputError):
                    self.call(dependencies, **overrides)
                self.assertEqual(dependencies.calls, [])
        with self.assertRaises(TypeError):
            self.call(ReadyDependencies(), unexpected=True)

    def test_attestation_binds_session_workspace_plugin_and_hook_contract(self) -> None:
        now = datetime(2026, 8, 6, 18, 0, tzinfo=UTC)
        store = AttestationStore(lambda: now)
        request = self.request()
        store.store(request, self.result())
        self.assertIsNotNone(store.load(request))

        other_workspace = self.base / "other workspace"
        other_workspace.mkdir()
        self.assertIsNone(store.load(dict(request, root=other_workspace)))
        self.assertIsNone(store.load(dict(request, sessionId="other-session")))

        manifest = self.plugin_root / ".codex-plugin" / "plugin.json"
        manifest.write_text(
            json.dumps({"name": "codeops", "version": "1.2.4"}),
            encoding="utf-8",
        )
        self.assertIsNone(store.load(request))
        manifest.write_text(
            json.dumps({"name": "codeops", "version": "1.2.3"}),
            encoding="utf-8",
        )
        hooks = self.plugin_root / "hooks" / "hooks.json"
        hooks.write_text("{}", encoding="utf-8")
        self.assertIsNone(store.load(request))

    def test_attestation_rejects_future_and_malformed_records(self) -> None:
        now = datetime(2026, 8, 6, 18, 0, tzinfo=UTC)
        store = AttestationStore(lambda: now)
        request = self.request()
        store.store(request, self.result())
        path = self.plugin_data / "preflight" / "sessions" / "session-1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["createdAt"] = (now + timedelta(minutes=6)).isoformat()
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.assertIsNone(store.load(request))
        path.write_text("not-json", encoding="utf-8")
        self.assertIsNone(store.load(request))

    def test_attestation_cleanup_and_atomic_refresh_are_contained(self) -> None:
        clock = [datetime(2026, 8, 6, 18, 0, tzinfo=UTC)]
        store = AttestationStore(lambda: clock[0])
        request = self.request()
        store.store(request, self.result())
        sessions = self.plugin_data / "preflight" / "sessions"
        current = sessions / "session-1.json"
        orphan = sessions / "orphan.json"
        orphan.write_text("{}", encoding="utf-8")
        old = (clock[0] - timedelta(days=8)).timestamp()
        os.utime(orphan, (old, old))
        store.cleanup(request)
        self.assertFalse(orphan.exists())
        self.assertTrue(current.exists())

        clock[0] += timedelta(hours=1)
        store.store(request, self.result())
        payload = json.loads(current.read_text(encoding="utf-8"))
        self.assertEqual(payload["createdAt"], "2026-08-06T19:00:00Z")
        self.assertEqual(list(sessions.glob("*.tmp")), [])
        self.assertEqual(list(sessions.glob("*.json")), [current])

    def test_workspace_adapter_requires_fixed_ntfs(self) -> None:
        dependencies = NativeProbeDependencies()
        with patch(
            "scripts.codeops_windows_lib.probes._windows_volume",
            return_value=("C:\\", "NTFS", 3),
        ):
            ready = dependencies.evaluate_check("workspace-local", self.request())
        with patch(
            "scripts.codeops_windows_lib.probes._windows_volume",
            return_value=("D:\\", "exFAT", 2),
        ):
            blocked = dependencies.evaluate_check("workspace-local", self.request())
        self.assertEqual(ready.status, Readiness.READY)
        self.assertEqual(blocked.status, Readiness.BLOCKED)

    def test_reparse_adapter_blocks_the_path_filesystem_check(self) -> None:
        dependencies = NativeProbeDependencies()
        with patch(
            "scripts.codeops_windows_lib.probes._has_reparse_component",
            side_effect=(False, True),
        ):
            ready = dependencies.evaluate_check("path-filesystem", self.request())
            blocked = dependencies.evaluate_check("path-filesystem", self.request())
        self.assertEqual(ready.status, Readiness.READY)
        self.assertEqual(blocked.status, Readiness.BLOCKED)

    @unittest.skipUnless(os.name == "nt", "junction integration check is Windows-only")
    def test_mutation_blocks_an_in_root_junction_target(self) -> None:
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        destination = self.root / "real"
        junction = self.root / "linked"
        destination.mkdir()
        (destination / "target.txt").write_text("safe", encoding="utf-8")
        junction_environment = dict(os.environ)
        junction_environment["CODEOPS_JUNCTION_PATH"] = str(junction)
        junction_environment["CODEOPS_JUNCTION_TARGET"] = str(destination)
        created = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-Command",
                (
                    "New-Item -ItemType Junction -Path $env:CODEOPS_JUNCTION_PATH "
                    "-Target $env:CODEOPS_JUNCTION_TARGET | Out-Null"
                ),
            ],
            text=True,
            capture_output=True,
            check=False,
            env=junction_environment,
        )
        self.assertEqual(created.returncode, 0, created.stderr)

        native = NativeProbeDependencies()

        class TargetAwareDependencies(ReadyDependencies):
            def evaluate_check(
                self,
                code: str,
                request: dict[str, object],
            ) -> CheckResult:
                if code == "path-filesystem":
                    return native.evaluate_check(code, request)
                return super().evaluate_check(code, request)

        result = self.call(
            TargetAwareDependencies(),
            mode="mutation",
            entrypoint_code="state-transition",
            hook_event="PreToolUse",
            targets=(junction / "target.txt",),
        )
        self.assertEqual(result.status, Readiness.BLOCKED)
        path_check = next(check for check in result.checks if check.code == "path-filesystem")
        self.assertEqual(path_check.status, Readiness.BLOCKED)

    def test_subprocess_adapter_uses_an_argument_array_without_a_shell(self) -> None:
        from scripts.codeops_windows_lib import probes

        completed = subprocess.CompletedProcess(["git", "--version"], 0, "ok", "")
        with patch("scripts.codeops_windows_lib.probes.subprocess.run", return_value=completed) as run:
            observed = probes._run(("git", "--version; Remove-Item C:\\important"))
        self.assertIs(observed, completed)
        arguments, options = run.call_args
        self.assertEqual(
            arguments[0],
            ["git", "--version; Remove-Item C:\\important"],
        )
        self.assertNotIn("shell", options)
        self.assertEqual(options["stdin"], subprocess.DEVNULL)

    @unittest.skipUnless(os.name == "nt", "PowerShell injection check is Windows-only")
    def test_bootstrap_never_evaluates_hostile_forwarded_arguments(self) -> None:
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        marker = self.base / "must-not-exist.txt"
        hostile = f"; Set-Content -LiteralPath '{marker}' -Value owned"
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-File",
                str(ROOT / "scripts" / "codeops-windows-preflight.ps1"),
                hostile,
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertIn(result.returncode, (0, 1, 2))
        self.assertFalse(marker.exists())

    @unittest.skipUnless(os.name == "nt", "native launcher integration is Windows-only")
    def test_valid_launcher_emits_ordered_checks_and_attestation(self) -> None:
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        attestation_request = {
            "mode": "read",
            "entrypointCode": None,
            "hookEvent": None,
            "targets": (),
            "root": self.root,
            "pluginRoot": ROOT,
            "pluginData": self.plugin_data,
            "sessionId": "launcher-session",
            "environment": {},
        }
        AttestationStore().store(
            attestation_request,
            self.result(session_id="launcher-session"),
        )
        result = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-File",
                str(ROOT / "scripts" / "codeops-windows-preflight.ps1"),
                "--mode",
                "read",
                "--root",
                str(self.root),
                "--plugin-root",
                str(ROOT),
                "--plugin-data",
                str(self.plugin_data),
                "--session-id",
                "launcher-session",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(tuple(check["code"] for check in payload["checks"]), CHECK_CODES)
        attestation = (
            self.plugin_data / "preflight" / "sessions" / "launcher-session.json"
        )
        self.assertTrue(attestation.is_file())

    @unittest.skipUnless(os.name == "nt", "native hook integration is Windows-only")
    def test_registered_hook_runs_from_a_hostile_legal_plugin_path(self) -> None:
        powershell = shutil.which("powershell.exe")
        self.assertIsNotNone(powershell)
        plugin_root = self.base / "plugin $(New-Item injected.txt) ' with spaces"
        (plugin_root / "scripts").mkdir(parents=True)
        for name in ("codeops-windows-hook.ps1", "codeops-windows-preflight.ps1"):
            shutil.copy2(ROOT / "scripts" / name, plugin_root / "scripts" / name)
        (plugin_root / "scripts" / "codeops_hooks.py").write_text(
            (
                "import argparse, json, sys\n"
                "p=argparse.ArgumentParser(); p.add_argument('--event', required=True)\n"
                "a=p.parse_args(); payload=json.loads(sys.stdin.read().lstrip('\\ufeff'))\n"
                "assert payload['hook_event_name'] == a.event\n"
                "print('Coding standards')\n"
            ),
            encoding="utf-8",
        )
        shutil.copytree(ROOT / "hooks", plugin_root / "hooks")
        plugin_data = self.base / "hostile plugin data"
        plugin_data.mkdir()
        manifest = json.loads(
            (plugin_root / "hooks" / "hooks.json").read_text(encoding="utf-8")
        )
        command = manifest["hooks"]["SessionStart"][0]["hooks"][0]["commandWindows"]
        payload = {
            "session_id": "hostile-path-session",
            "cwd": str(self.root),
            "hook_event_name": "SessionStart",
            "source": "startup",
        }
        environment = dict(os.environ)
        environment["PLUGIN_ROOT"] = str(plugin_root)
        environment["PLUGIN_DATA"] = str(plugin_data)
        result = subprocess.run(
            [powershell, "-NoProfile", "-Command", command],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            cwd=self.base,
            env=environment,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("Coding standards", result.stdout)
        self.assertFalse((self.base / "injected.txt").exists())

    def test_hook_probe_rejects_an_unrelated_native_command(self) -> None:
        manifest = self.plugin_root / "hooks" / "hooks.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["hooks"]["PreToolUse"][0]["hooks"][0][
            "commandWindows"
        ] = "powershell.exe safe.ps1"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        result = NativeProbeDependencies().evaluate_check("hooks-available", self.request())
        self.assertEqual(result.status, Readiness.BLOCKED)

    def test_hook_probe_rejects_matcher_type_and_cardinality_substitution(self) -> None:
        manifest = self.plugin_root / "hooks" / "hooks.json"
        original = json.loads(manifest.read_text(encoding="utf-8"))
        mutants: list[dict[str, object]] = []
        for mutation in ("matcher", "type", "extra"):
            payload = json.loads(json.dumps(original))
            event = payload["hooks"]["PreToolUse"][0]
            if mutation == "matcher":
                event["matcher"] = "never"
            elif mutation == "type":
                event["hooks"][0]["type"] = "not-command"
            else:
                event["hooks"].append(dict(event["hooks"][0]))
            mutants.append(payload)

        for payload in mutants:
            with self.subTest(payload=payload):
                manifest.write_text(json.dumps(payload), encoding="utf-8")
                result = NativeProbeDependencies().evaluate_check(
                    "hooks-available",
                    self.request(),
                )
                self.assertEqual(result.status, Readiness.BLOCKED)


if __name__ == "__main__":
    unittest.main()
