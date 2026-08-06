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


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "scripts" / "fixtures"
MIGRATE = ROOT / "scripts" / "codeops_migrate.py"
ROADMAP = ROOT / "scripts" / "codeops_roadmap.py"


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


if __name__ == "__main__":
    unittest.main()
