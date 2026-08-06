#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = ROOT / "scripts" / "codeops-windows-preflight.ps1"
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


def contract() -> tuple[Any, Any]:
    """Load only the planned public orchestration and result-model modules."""
    preflight = importlib.import_module("scripts.codeops_windows_preflight")
    models = importlib.import_module("scripts.codeops_windows_lib.models")
    return preflight, models


class FakeDependencies:
    """Deterministic dependency implementation used by the specification oracle."""

    def __init__(
        self,
        models: Any,
        *,
        host: str = "native-windows",
        statuses: Mapping[str, str] | None = None,
        attestation: Mapping[str, object] | None = None,
    ) -> None:
        self.models = models
        self.host = host
        self.statuses = dict(statuses or {})
        self.attestation = attestation
        self.classifications: list[Mapping[str, str]] = []
        self.check_calls: list[str] = []
        self.stored: list[tuple[Mapping[str, object], object]] = []
        self.cleanup_calls = 0

    def classify_host(self, environment: Mapping[str, str]) -> str:
        self.classifications.append(dict(environment))
        return self.host

    def evaluate_check(
        self,
        code: str,
        request: Mapping[str, object],
    ) -> object:
        del request
        self.check_calls.append(code)
        status = self.models.Readiness(self.statuses.get(code, "READY"))
        return self.models.CheckResult(code, status, f"{code}: {status.value}", None)

    def load_attestation(
        self,
        request: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        del request
        return self.attestation

    def store_attestation(
        self,
        request: Mapping[str, object],
        result: object,
    ) -> None:
        self.stored.append((dict(request), result))

    def cleanup_attestations(self) -> None:
        self.cleanup_calls += 1


class NativePreflightSpecificationTests(unittest.TestCase):
    """Executable contract for session, read, and mutation preflight behavior."""

    def run_preflight(
        self,
        dependencies: FakeDependencies,
        *,
        mode: str = "session",
        entrypoint_code: str | None = None,
        targets: tuple[Path, ...] = (),
        session_id: str = "session-1",
        environment: Mapping[str, str] | None = None,
    ) -> object:
        preflight, _ = contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            plugin_root = root / "plugin root"
            plugin_data = root / "plugin data"
            plugin_root.mkdir()
            plugin_data.mkdir()
            normalized_targets = tuple(
                root / target if not target.is_absolute() else target
                for target in targets
            )
            return preflight.run_preflight(
                mode=mode,
                entrypoint_code=entrypoint_code,
                targets=normalized_targets,
                root=root,
                plugin_root=plugin_root,
                plugin_data=plugin_data,
                session_id=session_id,
                environment=dict(environment or {}),
                dependencies=dependencies,
            )

    def test_ready_session_is_ordered_and_persisted(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(models)
        result = self.run_preflight(dependencies)
        self.assertEqual(result.schema_version, 1)
        self.assertEqual(result.status, models.Readiness.READY)
        self.assertEqual(tuple(item.code for item in result.checks), CHECK_CODES)
        self.assertEqual(dependencies.check_calls, list(CHECK_CODES[1:]))
        self.assertEqual(len(dependencies.stored), 1)
        self.assertEqual(dependencies.cleanup_calls, 1)

    @unittest.skipUnless(os.name == "nt", "PowerShell bootstrap is native-Windows only")
    def test_bootstrap_falls_back_to_python_3_10_or_newer(self) -> None:
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "pwsh is required on the certified Windows host")
        self.assertTrue(BOOTSTRAP.is_file())
        with tempfile.TemporaryDirectory() as raw:
            commands = Path(raw)
            (commands / "py.cmd").write_text("@exit /b 1\n", encoding="utf-8")
            (commands / "python.cmd").write_text(
                f'@"{sys.executable}" %*\n',
                encoding="utf-8",
            )
            environment = dict(os.environ)
            environment["PATH"] = str(commands)
            result = subprocess.run(
                [pwsh, "-NoProfile", "-File", str(BOOTSTRAP), "-ResolvePython"],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.strip().lower().endswith("python.cmd"))

    @unittest.skipUnless(os.name == "nt", "PowerShell bootstrap is native-Windows only")
    def test_bootstrap_blocks_when_no_supported_python_exists(self) -> None:
        pwsh = shutil.which("pwsh")
        self.assertIsNotNone(pwsh, "pwsh is required on the certified Windows host")
        self.assertTrue(BOOTSTRAP.is_file())
        with tempfile.TemporaryDirectory() as raw:
            commands = Path(raw)
            for name in ("py.cmd", "python.cmd"):
                (commands / name).write_text("@exit /b 1\n", encoding="utf-8")
            environment = dict(os.environ)
            environment["PATH"] = str(commands)
            result = subprocess.run(
                [pwsh, "-NoProfile", "-File", str(BOOTSTRAP), "-ResolvePython"],
                text=True,
                capture_output=True,
                check=False,
                env=environment,
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Python 3.10", result.stderr)

    def test_installed_wsl_does_not_change_native_readiness(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(models, host="native-windows")
        result = self.run_preflight(
            dependencies,
            environment={"UNRELATED_MACHINE_FACT": "wsl-installed"},
        )
        self.assertEqual(result.status, models.Readiness.READY)
        self.assertEqual(
            dependencies.classifications[0]["UNRELATED_MACHINE_FACT"],
            "wsl-installed",
        )

    def test_wsl_process_is_refused_before_other_probes(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(models, host="wsl")
        result = self.run_preflight(
            dependencies,
            mode="mutation",
            entrypoint_code="state-transition",
            targets=(Path("traceability.json"),),
        )
        self.assertEqual(result.status, models.Readiness.BLOCKED)
        self.assertEqual(tuple(item.code for item in result.checks), ("native-windows",))
        self.assertEqual(dependencies.check_calls, [])
        self.assertEqual(dependencies.stored, [])

    def test_non_windows_11_host_blocks(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(
            models,
            statuses={"windows-version": "BLOCKED"},
        )
        result = self.run_preflight(dependencies)
        self.assertEqual(result.status, models.Readiness.BLOCKED)
        self.assertEqual(dependencies.stored, [])

    def test_unelevated_operational_sandbox_warns(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(models, statuses={"sandbox": "WARNING"})
        result = self.run_preflight(dependencies)
        self.assertEqual(result.status, models.Readiness.WARNING)
        sandbox = next(item for item in result.checks if item.code == "sandbox")
        self.assertEqual(sandbox.status, models.Readiness.WARNING)
        self.assertEqual(len(dependencies.stored), 1)

    def test_unsupported_workspace_blocks_before_persistence(self) -> None:
        _, models = contract()
        for code in ("workspace-local", "path-filesystem"):
            with self.subTest(code=code):
                dependencies = FakeDependencies(models, statuses={code: "BLOCKED"})
                result = self.run_preflight(dependencies)
                self.assertEqual(result.status, models.Readiness.BLOCKED)
                self.assertEqual(dependencies.stored, [])

    def test_mismatched_attestation_is_replaced_only_after_full_check(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(
            models,
            attestation={"schemaVersion": 1, "sessionId": "another-session"},
        )
        result = self.run_preflight(dependencies, mode="read")
        self.assertEqual(result.status, models.Readiness.READY)
        self.assertEqual(dependencies.check_calls, list(CHECK_CODES[1:]))
        self.assertEqual(len(dependencies.stored), 1)

    def test_mutation_rechecks_changed_conditions_despite_cache(self) -> None:
        _, models = contract()
        dependencies = FakeDependencies(
            models,
            statuses={"git-for-windows": "BLOCKED"},
            attestation={"schemaVersion": 1, "sessionId": "session-1"},
        )
        result = self.run_preflight(
            dependencies,
            mode="mutation",
            entrypoint_code="state-transition",
            targets=(Path("traceability.json"),),
        )
        self.assertEqual(result.status, models.Readiness.BLOCKED)
        self.assertEqual(dependencies.check_calls, list(CHECK_CODES[1:]))
        self.assertEqual(dependencies.stored, [])

    def test_closed_input_rejects_malformed_combinations(self) -> None:
        preflight, models = contract()
        cases = (
            {"mode": "unknown"},
            {"mode": "session", "entrypoint_code": "state-transition"},
            {"mode": "read", "targets": (Path("unexpected.json"),)},
            {"mode": "mutation", "entrypoint_code": None, "targets": (Path("a"),)},
            {"mode": "mutation", "entrypoint_code": "unknown", "targets": (Path("a"),)},
            {"mode": "mutation", "entrypoint_code": "state-transition", "targets": ()},
            {
                "mode": "mutation",
                "entrypoint_code": "state-transition",
                "targets": (Path("a"), Path("a")),
            },
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                dependencies = FakeDependencies(models)
                with self.assertRaises(preflight.PreflightInputError):
                    self.run_preflight(dependencies, **overrides)
                self.assertEqual(dependencies.check_calls, [])
                self.assertEqual(dependencies.stored, [])


if __name__ == "__main__":
    unittest.main()
