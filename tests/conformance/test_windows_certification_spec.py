#!/usr/bin/env python3
"""Specification contracts for native Windows certification and support claims."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re
import stat
import subprocess
import tempfile
import unittest
import zipfile

import yaml


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_SCENARIOS = (
    "installation", "enablement", "session-preflight", "requirements", "planning",
    "preflight-audit", "execution-transition-recovery", "migration", "roadmap",
    "worktree", "agent-install-check", "outcomes", "verification",
)
DESKTOP_CHECKS = ("installation", "enablement", "hook-review", "preflight", "requirements-to-plan")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_candidate_evidence(root: Path) -> tuple[Path, Path, str, str]:
    """Create a fully bound synthetic candidate for adversarial specification mutations."""

    version = "0.4.0"
    commit = "a" * 40
    records = root / "records"
    records.mkdir(parents=True)
    scenarios: list[dict[str, object]] = []
    commands: list[dict[str, object]] = []
    for scenario in REQUIRED_SCENARIOS:
        record = records / f"{scenario}.json"
        record.write_text(json.dumps({
            "schemaVersion": 1,
            "scenarioId": scenario,
            "result": "pass",
            "commandClass": "native-python",
            "timestamp": "2026-08-07T00:00:00Z",
            "summary": "synthetic passing result",
        }, sort_keys=True) + "\n", encoding="utf-8")
        scenarios.append({
            "id": scenario, "status": "pass",
            "record": record.relative_to(root).as_posix(), "sha256": _sha256(record),
        })
        markers = {
            "installation": ["plugin", "add"],
            "enablement": ["plugin", "list"],
            "session-preflight": ["codeops-windows-preflight.ps1"],
            "requirements": ["exec", "make-requirements"],
            "planning": ["exec", "make-plan"],
            "preflight-audit": ["exec", "preflight"],
            "execution-transition-recovery": ["transition", "transition-recover"],
            "migration": ["codeops_migrate.py", "apply"],
            "roadmap": ["codeops_roadmap.py", "sync"],
            "worktree": ["codeops_worktree.py"],
            "agent-install-check": ["install_agents.py", "--check"],
            "outcomes": ["codeops_outcomes.py", "emit", "report"],
            "verification": ["codeops_verify.py", "all"],
        }[scenario]
        commands.append({
            "scenarioId": scenario,
            "executable": "C:/Program Files/Python/python.exe",
            "arguments": markers,
            "exitClass": "success",
        })
    trace = records / "commands.json"
    trace.write_text(json.dumps(commands, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    common = {
        "schemaVersion": 1,
        "pluginVersion": version,
        "commit": commit,
        "candidateSha256": "b" * 64,
        "reviewer": {"github": "octocat", "timestamp": "2026-08-07T00:00:00Z"},
    }
    cli = root / "windows-native.json"
    cli.write_text(json.dumps({
        **common,
        "kind": "cli",
        "host": {
            "edition": "Windows 11", "build": 26100, "architecture": "ARM64", "native": True,
        },
        "tools": {
            "python": "3.12.4", "git": "git version 2.50.0.windows.1", "codex": "codex-cli 1.0.0",
        },
        "ci": {"runId": "12345", "commit": commit, "conclusion": "success", "runner": "windows-11-arm"},
        "captureVersion": 1,
        "assertions": {"wslInvoked": False, "gitBashInvoked": False},
        "commandTrace": {"path": trace.relative_to(root).as_posix(), "sha256": _sha256(trace)},
        "scenarios": scenarios,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    desktop = root / "windows-desktop.json"
    desktop.write_text(json.dumps({
        **common,
        "kind": "desktop",
        "tools": {"codex": "codex-desktop 1.0.0"},
        "assertions": {"nativeWindows": True, "wslInvoked": False, "gitBashInvoked": False},
        "checklist": [{"id": item, "status": "pass"} for item in DESKTOP_CHECKS],
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return cli, desktop, version, commit


def validate_set(
    root: Path,
    cli: Path | None,
    desktop: Path | None,
    version: str,
    commit: str,
    *,
    support_claimed: bool = False,
) -> list[str]:
    from scripts.validate_windows_evidence import validate_evidence_set

    return validate_evidence_set(
        root,
        cli_path=cli,
        desktop_path=desktop,
        expected_version=version,
        expected_commit=commit,
        support_claimed=support_claimed,
    )


class CertificationCISpecification(unittest.TestCase):
    def test_release_archive_excludes_only_self_referential_windows_evidence(self) -> None:
        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertNotIn("tests/evidence/** export-ignore", attributes)
        for path in (
            "tests/evidence/windows-native-0.5.0.json",
            "tests/evidence/windows-native-0.5.0/**",
            "tests/evidence/windows-desktop-0.5.0.json",
            "tests/evidence/windows-release-0.5.0.json",
        ):
            self.assertIn(f"{path} export-ignore", attributes)

    def test_st_46_ci_has_explicit_ubuntu_and_windows_11_arm_native_jobs(self) -> None:
        workflow = ROOT / ".github/workflows/ci.yml"
        payload = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        jobs = payload["jobs"]
        package = jobs["package-release-artifact"]
        ubuntu = jobs["validate-ubuntu"]
        windows = jobs["validate-windows-11-arm"]
        self.assertEqual(ubuntu["needs"], "package-release-artifact")
        self.assertEqual(windows["needs"], "package-release-artifact")
        self.assertEqual(ubuntu["runs-on"], "ubuntu-latest")
        self.assertEqual(windows["runs-on"], "windows-11-arm")

        package_steps = "\n".join(
            str(step.get("run", "")) for step in package["steps"] if isinstance(step, dict)
        )
        self.assertIn("scripts/package_release.py", package_steps)
        self.assertIn("sourceCommit", package_steps)
        self.assertIn("sha256sum --check --strict", package_steps)
        self.assertIn("evidence_ref", workflow.read_text(encoding="utf-8"))
        self.assertIn("test \"$GITHUB_SHA\" = \"$source_commit\"", package_steps)
        self.assertIn("authority=tests/evidence/windows-release-0.5.0.json", package_steps)
        self.assertLess(
            package_steps.index("source_commit=$(python"),
            package_steps.index("scripts/package_release.py"),
        )
        self.assertLess(
            package_steps.index("scripts/package_release.py"),
            package_steps.index("sha256sum --check --strict"),
        )
        for job, retained_path in (
            (ubuntu, "tests/evidence"),
            (windows, "tests\\evidence"),
        ):
            evidence_steps = "\n".join(
                str(step.get("run", "")) for step in job["steps"] if isinstance(step, dict)
            )
            self.assertIn(retained_path, evidence_steps)
            self.assertIn("certification-evidence", evidence_steps)
        self.assertTrue(any(
            str(step.get("uses", "")).startswith("actions/upload-artifact@")
            for step in package["steps"] if isinstance(step, dict)
        ))

        def python_versions(job: dict[str, object]) -> list[str]:
            return [
                str(step["with"]["python-version"])
                for step in job["steps"]
                if isinstance(step, dict)
                and str(step.get("uses", "")).startswith("actions/setup-python@")
            ]

        for job in (ubuntu, windows):
            versions = python_versions(job)
            self.assertEqual(len(versions), 1)
            self.assertGreaterEqual(tuple(map(int, re.match(r"^(\d+)\.(\d+)", versions[0]).groups())), (3, 10))

        windows_steps = "\n".join(
            str(step.get("run", "")) for step in windows["steps"] if isinstance(step, dict)
        ).casefold()
        self.assertIn("source with spaces", str(windows).casefold())
        self.assertIn("codeops-windows-preflight.ps1", windows_steps)
        self.assertIn("codeops-verify.ps1", windows_steps)
        self.assertIn("release-artifact", windows_steps)
        self.assertIn("expand-archive", windows_steps)
        self.assertNotRegex(windows_steps, r"(?:^|\s)(?:bash|wsl)(?:\.exe)?(?:\s|$)")
        self.assertNotIn(".sh", windows_steps)

        ubuntu_steps = "\n".join(
            str(step.get("run", "")) for step in ubuntu["steps"] if isinstance(step, dict)
        )
        for launcher in (
            "./scripts/validate-codex.sh", "./scripts/docs-check.sh",
            "./scripts/migration-check.sh", "./scripts/roadmap-sync-check.sh",
            "./scripts/compact-check.sh",
        ):
            self.assertIn(launcher, ubuntu_steps)
        self.assertIn("release-artifact", ubuntu_steps)
        self.assertIn("unzip -q", ubuntu_steps)
        self.assertIn("test -x", ubuntu_steps)

    def test_release_packaging_is_byte_reproducible_and_preserves_modes(self) -> None:
        from scripts.package_release import package

        with tempfile.TemporaryDirectory() as raw:
            fixture = Path(raw) / "fixture"
            fixture.mkdir()
            (fixture / ".gitattributes").write_text(
                "ignored.txt export-ignore\n", encoding="utf-8", newline="\n"
            )
            (fixture / "ignored.txt").write_text("excluded\n", encoding="utf-8", newline="\n")
            (fixture / "run.sh").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8", newline="\n")
            subprocess.run(["git", "init", str(fixture)], check=True, capture_output=True)
            subprocess.run(
                ["git", "-C", str(fixture), "config", "user.name", "CodeOps Test"], check=True
            )
            subprocess.run(
                ["git", "-C", str(fixture), "config", "user.email", "codeops@example.invalid"],
                check=True,
            )
            subprocess.run(["git", "-C", str(fixture), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(fixture), "update-index", "--chmod=+x", "run.sh"], check=True
            )
            subprocess.run(
                ["git", "-C", str(fixture), "commit", "-m", "fixture"],
                check=True,
                capture_output=True,
            )
            first = Path(raw) / "first.zip"
            second = Path(raw) / "second.zip"
            package(fixture, "HEAD", first)
            package(fixture, "HEAD", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                names = set(archive.namelist())
                self.assertNotIn("ignored.txt", names)
                self.assertEqual(archive.read("run.sh"), b"#!/bin/sh\nexit 0\n")
                mode = archive.getinfo("run.sh").external_attr >> 16
                self.assertEqual(mode, stat.S_IFREG | 0o755)


class CertificationEvidenceSpecification(unittest.TestCase):
    def test_st_47_missing_or_failed_scenario_blocks_certification(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            payload = json.loads(cli.read_text(encoding="utf-8"))
            payload["scenarios"] = payload["scenarios"][1:]
            cli.write_text(json.dumps(payload), encoding="utf-8")
            missing = validate_set(root, cli, desktop, version, commit)
            payload = json.loads(cli.read_text(encoding="utf-8"))
            payload["scenarios"][0]["status"] = "fail"
            cli.write_text(json.dumps(payload), encoding="utf-8")
            failing = validate_set(root, cli, desktop, version, commit)
        self.assertTrue(any("required scenario" in error for error in missing), missing)
        self.assertTrue(any("failing scenario" in error for error in failing), failing)

    def test_st_48_version_or_commit_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            version_errors = validate_set(root, cli, desktop, "0.5.0", commit)
            commit_errors = validate_set(root, cli, desktop, version, "c" * 40)
        self.assertTrue(any("version" in error for error in version_errors), version_errors)
        self.assertTrue(any("commit" in error for error in commit_errors), commit_errors)

    def test_st_49_prohibited_runtime_in_command_trace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            payload = json.loads(cli.read_text(encoding="utf-8"))
            trace = root / payload["commandTrace"]["path"]
            commands = json.loads(trace.read_text(encoding="utf-8"))
            commands[0]["executable"] = "C:/Windows/System32/wsl.exe"
            trace.write_text(json.dumps(commands), encoding="utf-8")
            payload["commandTrace"]["sha256"] = _sha256(trace)
            cli.write_text(json.dumps(payload), encoding="utf-8")
            errors = validate_set(root, cli, desktop, version, commit)
        self.assertTrue(any("prohibited runtime" in error for error in errors), errors)

    def test_st_50_cli_manifest_recomputes_every_supporting_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            self.assertEqual(validate_set(root, cli, desktop, version, commit), [])
            payload = json.loads(cli.read_text(encoding="utf-8"))
            record = root / payload["scenarios"][0]["record"]
            record.write_text(record.read_text(encoding="utf-8") + " ", encoding="utf-8")
            errors = validate_set(root, cli, desktop, version, commit)
        self.assertTrue(any("hash" in error for error in errors), errors)

    def test_st_51_desktop_evidence_requires_reviewer_provenance_and_complete_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            self.assertEqual(validate_set(root, cli, desktop, version, commit), [])
            payload = json.loads(desktop.read_text(encoding="utf-8"))
            del payload["reviewer"]["github"]
            payload["checklist"] = payload["checklist"][:-1]
            desktop.write_text(json.dumps(payload), encoding="utf-8")
            errors = validate_set(root, cli, desktop, version, commit)
        self.assertTrue(any("reviewer" in error for error in errors), errors)
        self.assertTrue(any("desktop checklist" in error for error in errors), errors)

    def test_st_52_support_claim_requires_matching_ci_cli_and_desktop_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            cli, desktop, version, commit = write_candidate_evidence(root)
            self.assertEqual(
                validate_set(root, cli, desktop, version, commit, support_claimed=True),
                [],
            )
            errors = validate_set(root, cli, None, version, commit, support_claimed=True)
        self.assertTrue(any("desktop evidence" in error for error in errors), errors)

    def test_st_53_documentation_rejects_old_or_patch_pinned_python_and_wsl_removal(self) -> None:
        from scripts.validate_windows_evidence import validate_documentation_policy

        for text in (
            "Windows requires Python 3.9.",
            "Windows requires Python 3.12.4.",
            "Uninstall WSL before using CodeOps.",
        ):
            self.assertTrue(validate_documentation_policy({"README.md": text}, support_claimed=False), text)

    def test_st_54_support_claim_is_forbidden_without_valid_evidence(self) -> None:
        from scripts.validate_windows_evidence import validate_documentation_policy

        supported = {"README.md": "CodeOps supports native Windows 11."}
        pending = {"README.md": "Native Windows 11 remains unsupported pending certification evidence."}
        self.assertTrue(validate_documentation_policy(supported, support_claimed=False))
        self.assertEqual(validate_documentation_policy(pending, support_claimed=False), [])
        with tempfile.TemporaryDirectory() as raw:
            errors = validate_set(Path(raw), None, None, "0.4.0", "a" * 40, support_claimed=True)
        self.assertTrue(any("CLI evidence" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
