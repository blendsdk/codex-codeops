#!/usr/bin/env python3
"""Capture sanitized native Windows CLI certification evidence for a packed candidate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from typing import Sequence
import zipfile

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_platform.subprocesses import run_command
from scripts.validate_windows_evidence import REQUIRED_SCENARIOS, validate_evidence_set


SCENARIO_TESTS = {
    "installation": "tests.conformance.test_windows_workflows_impl",
    "enablement": "tests.conformance.test_windows_workflows_spec",
    "session-preflight": "tests.conformance.test_windows_preflight_impl",
    "requirements": "tests.conformance.test_targeted_workflows_spec",
    "planning": "tests.conformance.test_targeted_workflows_spec",
    "preflight-audit": "tests.conformance.test_windows_preflight_spec",
    "execution-transition-recovery": "tests.conformance.test_state_migration_impl",
    "migration": "tests.conformance.test_state_migration_spec",
    "roadmap": "tests.conformance.test_portable_utilities_impl",
    "worktree": "tests.conformance.test_windows_workflows_impl",
    "agent-install-check": "tests.conformance.test_windows_workflows_impl",
    "outcomes": "tests.conformance.test_windows_workflows_impl",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--candidate", type=Path, required=True, help="Packed plugin ZIP")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer", required=True, help="Reviewer GitHub identity")
    parser.add_argument("--ci-run-id", required=True)
    parser.add_argument("--ci-commit", required=True)
    parser.add_argument("--ci-conclusion", choices=("success",), required=True)
    parser.add_argument("--codex-version", required=True)
    return parser


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _prepare_output(output: Path, version: str) -> tuple[Path, Path]:
    """Create a version-owned record directory without disturbing retained evidence."""

    records_root = output / f"windows-native-{version}"
    manifest_path = output / f"windows-native-{version}.json"
    if records_root.exists() or manifest_path.exists():
        raise RuntimeError(f"evidence already exists for version {version}")
    output.mkdir(parents=True, exist_ok=True)
    records_root.mkdir()
    return records_root, manifest_path


def _discard_capture(records_root: Path, manifest_path: Path) -> None:
    """Remove only artifacts owned by the current failed capture."""

    manifest_path.unlink(missing_ok=True)
    if records_root.exists():
        shutil.rmtree(records_root)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    result = run_command(("git", *arguments), cwd=root)
    if result.exit_code:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(arguments)} failed")
    return result.stdout.strip()


def _candidate_root(extracted: Path) -> Path:
    direct = extracted / ".codex-plugin" / "plugin.json"
    if direct.is_file():
        return extracted
    matches = list(extracted.glob("*/.codex-plugin/plugin.json"))
    if len(matches) != 1:
        raise RuntimeError("candidate ZIP must contain exactly one plugin root")
    return matches[0].parents[1]


def _normalized(value: str, plugin_root: Path) -> str:
    return value.replace(str(plugin_root), "<PLUGIN_ROOT>").replace(str(plugin_root).replace("\\", "/"), "<PLUGIN_ROOT>")


def capture(args: argparse.Namespace) -> Path:
    root = args.root.resolve()
    candidate = args.candidate.resolve()
    output = args.output.resolve()
    if os.name != "nt" or platform.release() != "11" or sys.platform != "win32":
        raise RuntimeError("capture requires native Windows 11")
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        raise RuntimeError("capture refuses WSL execution")
    if _git(root, "status", "--porcelain"):
        raise RuntimeError("capture requires a clean repository")
    head = _git(root, "rev-parse", "HEAD")
    if args.ci_commit != head:
        raise RuntimeError("CI commit must match HEAD")
    if not candidate.is_file() or not zipfile.is_zipfile(candidate):
        raise RuntimeError("candidate must be a readable plugin ZIP")

    with tempfile.TemporaryDirectory(prefix="codeops-windows-candidate-") as raw:
        extracted = Path(raw)
        with zipfile.ZipFile(candidate) as archive:
            archive.extractall(extracted)
        plugin_root = _candidate_root(extracted)
        manifest = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        version = manifest.get("version")
        source_manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        if not isinstance(version, str) or version != source_manifest.get("version"):
            raise RuntimeError("packed candidate version must match the source manifest")
        if not (plugin_root / "scripts" / "codeops_verify.py").is_file():
            raise RuntimeError("packed candidate is missing portable verification tooling")

        records_root, manifest_path = _prepare_output(output, version)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        environment = dict(os.environ)
        environment.update({"PLUGIN_ROOT": str(plugin_root), "PLUGIN_DATA": str(records_root / "plugin-data"), "PYTHONUTF8": "1"})
        scenarios: list[dict[str, str]] = []
        trace: list[dict[str, object]] = []
        for scenario in REQUIRED_SCENARIOS:
            if scenario == "verification":
                argv = (
                    sys.executable,
                    str(plugin_root / "scripts" / "codeops_verify.py"),
                    "all",
                    "--root",
                    str(plugin_root),
                )
            else:
                argv = (sys.executable, "-m", "unittest", SCENARIO_TESTS[scenario])
            result = run_command(argv, cwd=plugin_root, environment=environment)
            status = "pass" if result.exit_code == 0 else "fail"
            record = records_root / f"{scenario}.json"
            _write_json(record, {
                "schemaVersion": 1, "scenarioId": scenario, "result": status,
                "commandClass": "native-python", "timestamp": timestamp,
                "summary": "native command completed successfully" if status == "pass" else "native command failed",
            })
            scenarios.append({
                "id": scenario, "status": status,
                "record": record.relative_to(output).as_posix(), "sha256": _sha256(record),
            })
            trace.append({
                "scenarioId": scenario,
                "executable": _normalized(argv[0], plugin_root),
                "arguments": [_normalized(item, plugin_root) for item in argv[1:]],
                "exitClass": "success" if result.exit_code == 0 else "expected-failure",
            })
        trace_path = records_root / "commands.json"
        _write_json(trace_path, trace)
        git_version = _git(root, "--version")
        build = int(platform.version().split(".")[-1])
        architecture = platform.machine().upper()
        _write_json(manifest_path, {
            "schemaVersion": 1, "pluginVersion": version, "commit": head,
            "candidateSha256": _sha256(candidate),
            "reviewer": {"github": args.reviewer, "timestamp": timestamp}, "kind": "cli",
            "host": {"edition": "Windows 11", "build": build, "architecture": architecture, "native": True},
            "tools": {"python": platform.python_version(), "git": git_version, "codex": args.codex_version},
            "ci": {"runId": args.ci_run_id, "commit": args.ci_commit, "conclusion": args.ci_conclusion, "runner": "windows-11-arm"},
            "captureVersion": 1,
            "assertions": {"wslInvoked": False, "gitBashInvoked": False},
            "commandTrace": {"path": trace_path.relative_to(output).as_posix(), "sha256": _sha256(trace_path)},
            "scenarios": scenarios,
        })
        errors = validate_evidence_set(output, cli_path=manifest_path, desktop_path=None, expected_version=version, expected_commit=head)
        if errors:
            _discard_capture(records_root, manifest_path)
            raise RuntimeError("captured evidence failed validation: " + "; ".join(errors))
        return manifest_path


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = capture(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"Windows evidence capture failed: {error}", file=sys.stderr)
        return 1
    print(f"Windows evidence captured: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
