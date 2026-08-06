"""Implementation and hostile-boundary tests for the portable control layer."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
MIGRATE = ROOT / "scripts" / "codeops_migrate.py"


class PortableParserAndProcessTests(unittest.TestCase):
    def test_unknown_option_exits_two_without_creating_layout(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = subprocess.run(
                [sys.executable, str(MIGRATE), "preview", "--root", str(root), "--unknown"],
                text=True,
                capture_output=True,
                check=False,
                shell=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)
            self.assertFalse((root / "codeops").exists())

    def test_subprocess_adapter_keeps_hostile_argument_as_data(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        hostile = "topic & whoami | $(touch nope)"
        completed = SimpleNamespace(returncode=7, stdout="out", stderr="err")
        with mock.patch("subprocess.run", return_value=completed) as invoked:
            result = run_command(("git", "branch", hostile), cwd=ROOT)

        self.assertEqual(result.exit_code, 7)
        arguments, keywords = invoked.call_args
        self.assertEqual(arguments[0], ["git", "branch", hostile])
        self.assertIs(keywords["shell"], False)
        self.assertEqual(keywords["cwd"], ROOT)

    def test_subprocess_adapter_rejects_nul_before_execution(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with mock.patch("subprocess.run") as invoked:
            with self.assertRaisesRegex(ValueError, "without NUL"):
                run_command(("git", "bad\0argument"), cwd=ROOT)
        invoked.assert_not_called()


class PortableContainmentAndFailureTests(unittest.TestCase):
    def test_worktree_path_must_be_distinct_sibling(self) -> None:
        from scripts.codeops_worktree_lib.model import contained_worktree_path

        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw)
            main = parent / "project"
            main.mkdir()
            self.assertEqual(
                contained_worktree_path(main, parent / "project-topic"),
                (parent / "project-topic").resolve(),
            )
            for escaped in (main, main / "nested", parent.parent / "escaped"):
                with self.subTest(path=escaped):
                    with self.assertRaises(ValueError):
                        contained_worktree_path(main, escaped)

    def test_migration_git_failure_rolls_back_and_never_writes_marker(self) -> None:
        from scripts.codeops_migrate_lib.apply import apply_preview
        from scripts.codeops_migrate_lib.model import MigrationPreview, Move

        preview = MigrationPreview(
            "feature",
            "test",
            (
                Move("requirements", "codeops/features/feature/requirements"),
                Move("plans/feature", "codeops/features/feature/plans/feature"),
            ),
            (),
        )
        git_results = iter(
            (
                (0, "ROOT", ""),
                (0, "", ""),
                (0, "", ""),
                (1, "", "simulated git mv failure"),
                (0, "", ""),
            )
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()

            def fake_git(_root: Path, *arguments: str) -> tuple[int, str, str]:
                code, stdout, stderr = next(git_results)
                return code, str(root) if arguments[:2] == ("rev-parse", "--show-toplevel") else stdout, stderr

            with mock.patch("scripts.codeops_migrate_lib.apply._git", side_effect=fake_git), mock.patch(
                "scripts.codeops_migrate_lib.apply.run_mutation_preflight", return_value=0
            ):
                code, payload = apply_preview(root, preview)

            self.assertEqual(code, 1)
            self.assertEqual(payload["result"], "refused")
            self.assertIn("simulated git mv failure", payload["error"])
            self.assertFalse((root / "codeops" / ".codeops.yml").exists())


class PortableRenderingAndReportingTests(unittest.TestCase):
    def test_roadmap_rendering_is_byte_deterministic(self) -> None:
        from scripts.codeops_roadmap_lib.model import synchronize
        from scripts.codeops_roadmap_lib.rendering import compact

        fixture = ROOT / "tests" / "fixtures" / "roadmap" / "nested"
        first_sync = synchronize(fixture, "2025-06-01")
        second_sync = synchronize(fixture, "2099-01-01")
        self.assertEqual(first_sync.drift, second_sync.drift)
        self.assertEqual(first_sync.rendered, second_sync.rendered)
        first_compact = compact(fixture)
        second_compact = compact(fixture)
        self.assertEqual(first_compact.rendered, second_compact.rendered)
        self.assertEqual(
            json.dumps(first_compact.to_json(fixture), sort_keys=True),
            json.dumps(second_compact.to_json(fixture), sort_keys=True),
        )

    def test_aggregate_reports_all_checks_after_failure_in_closed_order(self) -> None:
        from scripts.codeops_verify_lib.core import CHECK_NAMES, CheckResult, run_checks

        calls: list[str] = []

        def check(name: str, exit_code: int):
            def invoke(_root: Path) -> CheckResult:
                calls.append(name)
                return CheckResult(name, exit_code, stderr=f"{name}-diagnostic\n")

            return invoke

        checks = {
            name: check(name, 1 if name == "docs" else 0)
            for name in CHECK_NAMES
        }
        results = run_checks(ROOT, checks)
        self.assertEqual(calls, list(CHECK_NAMES))
        self.assertEqual([item.name for item in results], list(CHECK_NAMES))
        self.assertEqual([item.exit_code for item in results], [0, 1, 0, 0, 0])

    def test_all_unix_compatibility_launchers_are_thin(self) -> None:
        launchers = (
            "scripts/codeops-migrate.sh",
            "scripts/codeops-roadmap-sync.sh",
            "scripts/codeops-roadmap-compact.sh",
            "bin/codeops-worktree",
            "scripts/validate-codex.sh",
            "scripts/docs-check.sh",
            "scripts/migration-check.sh",
            "scripts/roadmap-sync-check.sh",
            "scripts/compact-check.sh",
        )
        for relative in launchers:
            with self.subTest(launcher=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                executable = [
                    line for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                ]
                self.assertIn("set -euo pipefail", text)
                self.assertIn('"$@"', text)
                self.assertLessEqual(len(executable), 12)


if __name__ == "__main__":
    unittest.main()
