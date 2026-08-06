#!/usr/bin/env python3
"""Cross-host contracts for portable CodeOps utility commands."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "scripts" / "fixtures"
MIGRATE = ROOT / "scripts" / "codeops_migrate.py"
ROADMAP = ROOT / "scripts" / "codeops_roadmap.py"
WORKTREE = ROOT / "scripts" / "codeops_worktree.py"
HOOKS = ROOT / "scripts" / "codeops_hooks.py"
OUTCOMES = ROOT / "scripts" / "codeops_outcomes.py"
AGENTS = ROOT / "scripts" / "install_agents.py"
VERIFY = ROOT / "scripts" / "codeops_verify.py"


def run_cli(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def initialize_git(root: Path) -> None:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if not any(path.name != ".git" for path in root.iterdir()):
        (root / ".fixture").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "config", "user.name", "CodeOps Test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "codeops@example.invalid"],
        check=True,
    )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "fixture"], check=True)


class PortableMigrationSpecification(unittest.TestCase):
    def test_st_31_preview_has_canonical_move_map_and_does_not_mutate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "billing-platform"
            shutil.copytree(FIXTURES / "flat-repo", project)
            initialize_git(project)
            before = subprocess.run(
                ["git", "-C", str(project), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

            result = run_cli(MIGRATE, "preview", "--root", str(project), "--json")
            payload = json.loads(result.stdout)
            after = subprocess.run(
                ["git", "-C", str(project), "status", "--porcelain=v1"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["feature"], "billing-platform")
        self.assertEqual(
            payload["moves"],
            [
                {"source": "requirements", "target": "codeops/features/billing-platform/requirements"},
                {"source": "plans/invoicing", "target": "codeops/features/billing-platform/plans/invoicing"},
                {"source": "plans/00-roadmap.md", "target": "codeops/features/billing-platform/00-roadmap.md"},
                {"source": "plans/_archive/billing-v1", "target": "codeops/_archive/billing-v1"},
            ],
        )
        self.assertIn("plans/legacy", "\n".join(payload["warnings"]))
        self.assertEqual(before, after)


class PortableRoadmapSpecification(unittest.TestCase):
    def test_st_32_nested_sync_preserves_annotations_and_reports_no_drift(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "roadmap"
            shutil.copytree(FIXTURES / "roadmap-repo" / "nested", project)
            result = run_cli(
                ROADMAP,
                "sync",
                "--root",
                str(project),
                "--check",
                "--date",
                "2025-06-01",
                "--json",
            )
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["layout"], "nested")
        self.assertEqual(payload["drift"], [])
        self.assertTrue(payload["held"])

    def test_st_33_compact_write_matches_canonical_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "bloated"
            shutil.copytree(FIXTURES / "bloated-repo" / "nested", project)
            result = run_cli(
                ROADMAP,
                "compact",
                "--root",
                str(project),
                "--write",
                "--json",
            )
            payload = json.loads(result.stdout)
            pairs = [
                (
                    project / "codeops" / "00-roadmap.md",
                    FIXTURES / "bloated-repo" / "nested" / "codeops" / "00-roadmap.md.expected",
                ),
                (
                    project / "codeops" / "features" / "widgets" / "00-roadmap.md",
                    FIXTURES / "bloated-repo" / "nested" / "codeops" / "features" / "widgets" / "00-roadmap.md.expected",
                ),
                (
                    project / "codeops" / "_archive" / "legacy-ui" / "00-roadmap.md",
                    FIXTURES / "bloated-repo" / "nested" / "codeops" / "_archive" / "legacy-ui" / "00-roadmap.md.expected",
                ),
            ]
            rendered = [actual.read_bytes() for actual, _ in pairs]
            expected = [golden.read_bytes() for _, golden in pairs]

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["changed"], [
            "codeops/00-roadmap.md",
            "codeops/_archive/legacy-ui/00-roadmap.md",
            "codeops/features/widgets/00-roadmap.md",
        ])
        self.assertEqual(rendered, expected)


class PortableWorktreeSpecification(unittest.TestCase):
    def test_st_34_list_is_native_json_from_git_porcelain(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project with spaces"
            project.mkdir()
            initialize_git(project)
            result = run_cli(WORKTREE, "list", "--root", str(project), "--json")
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(payload["worktrees"]), 1)
        self.assertEqual(Path(payload["worktrees"][0]["path"]), project)

    def test_st_35_hostile_topic_branch_and_path_are_refused_without_git_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            project.mkdir()
            initialize_git(project)
            before = subprocess.run(
                ["git", "-C", str(project), "show-ref"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout
            result = run_cli(
                WORKTREE,
                "new",
                "../topic;whoami",
                "--root",
                str(project),
                "--branch",
                "feat/../../escape",
                "--path",
                str(project / ".." / "escape"),
                "--dry-run",
                "--json",
            )
            after = subprocess.run(
                ["git", "-C", str(project), "show-ref"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout

        self.assertEqual(result.returncode, 2)
        self.assertEqual(before, after)
        self.assertNotIn("whoami", result.stdout)


class ExistingPortableSurfaceSpecification(unittest.TestCase):
    def test_st_36_hooks_outcomes_and_agents_accept_paths_as_data(self) -> None:
        from scripts.codeops_hooks import NativeHookDependencies, run_hook

        class PassingDependencies(NativeHookDependencies):
            def run_preflight(self, mode: str, payload: dict[str, object]) -> int:
                del mode, payload
                return 0

        fixture = json.loads(
            (ROOT / "tests" / "fixtures" / "hooks" / "session-start-spaces.json").read_text(
                encoding="utf-8"
            )
        )
        with mock.patch.dict("os.environ", {"PLUGIN_ROOT": str(ROOT)}):
            hook = run_hook(fixture, PassingDependencies())
        self.assertEqual(hook.exit_code, 0, hook.stderr)

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project & echo not-a-command"
            project.mkdir()
            store = project / "events.jsonl"
            outcome = run_cli(
                OUTCOMES,
                "emit",
                "--root",
                str(project),
                "--store",
                str(store),
                "--event",
                "verification-run",
                "--stage",
                "verification",
                "--result",
                "pass",
            )
            agents = run_cli(
                AGENTS,
                "--project",
                str(project),
                "--roles",
                "explorer",
                "--dry-run",
            )

        self.assertEqual(outcome.returncode, 0, outcome.stderr)
        self.assertEqual(agents.returncode, 0, agents.stderr)


class PortableVerificationSpecification(unittest.TestCase):
    def test_st_37_verifier_exposes_closed_five_gate_surface(self) -> None:
        result = run_cli(VERIFY, "list", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            payload["checks"],
            ["validate", "docs", "migration", "roadmap", "compact"],
        )

    def test_st_38_aggregate_reports_each_gate_in_deterministic_order(self) -> None:
        result = run_cli(VERIFY, "all", "--root", str(ROOT), "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            [item["name"] for item in payload["results"]],
            ["validate", "docs", "migration", "roadmap", "compact"],
        )
        self.assertTrue(all(item["exitCode"] == 0 for item in payload["results"]))

    def test_unix_compatibility_launchers_are_strict_argument_forwarders(self) -> None:
        launchers = {
            "scripts/codeops-migrate.sh": "codeops_migrate.py",
            "scripts/codeops-roadmap-sync.sh": "codeops_roadmap.py",
            "scripts/codeops-roadmap-compact.sh": "codeops_roadmap.py",
            "bin/codeops-worktree": "codeops_worktree.py",
            "scripts/validate-codex.sh": "codeops_verify.py",
            "scripts/docs-check.sh": "codeops_verify.py",
            "scripts/migration-check.sh": "codeops_verify.py",
            "scripts/roadmap-sync-check.sh": "codeops_verify.py",
            "scripts/compact-check.sh": "codeops_verify.py",
        }
        for relative, owner in launchers.items():
            with self.subTest(launcher=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                executable = [
                    line
                    for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                ]
                self.assertIn("set -euo pipefail", text)
                self.assertIn(owner, text)
                self.assertIn('"$@"', text)
                self.assertLessEqual(len(executable), 12)


if __name__ == "__main__":
    unittest.main()
