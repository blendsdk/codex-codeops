#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.codeops_plan import inspect_plan


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_plan_migrate.py"


class PlanMigrationTests(unittest.TestCase):
    def make_feature(
        self,
        root: Path,
        plans: tuple[str, ...] = ("billing-plan",),
        rds: tuple[str, ...] = ("RD-01", "RD-02"),
        roadmap: bool = True,
    ) -> Path:
        codeops = root / "codeops"
        feature = codeops / "features" / "billing"
        requirements = feature / "requirements"
        requirements.mkdir(parents=True)
        for rd_id in rds:
            (requirements / f"{rd_id}-sample.md").write_text(f"# {rd_id}\n", encoding="utf-8")
        for plan_name in plans:
            plan = feature / "plans" / plan_name
            plan.mkdir(parents=True)
            (plan / "00-index.md").write_text(f"# {plan_name}\n\n> **Status**: Ready\n", encoding="utf-8")
            (plan / "99-execution-plan.md").write_text("# Execution\n\n- [ ] T-1 Build\n", encoding="utf-8")
        (feature / "traceability.json").write_text('{"schema": 2}\n', encoding="utf-8")
        if roadmap:
            rows = "\n".join(
                f"| {rd_id} | Item | [RD] | [plan](plans/{plans[0]}/00-index.md) | Plan Created | | | |"
                for rd_id in rds
            )
            (feature / "00-roadmap.md").write_text(
                "# Roadmap\n\n| ID | Title | RD | Plan | Stage | Status | Updated | Blocker |\n"
                "|---|---|---|---|---|---|---|---|\n"
                f"{rows}\n",
                encoding="utf-8",
            )
        return codeops

    def commit_fixture(self, root: Path) -> None:
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-q", "-m", "fixture"], check=True)

    def run_migrator(self, codeops: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(codeops), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_preview_infers_multiple_rds_from_roadmap_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory))
            index = codeops / "features" / "billing" / "plans" / "billing-plan" / "00-index.md"
            before = index.read_text(encoding="utf-8")
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("billing/RD-01, billing/RD-02 (feature roadmap)", result.stdout)
            self.assertIn("DELETE features/billing/traceability.json", result.stdout)
            self.assertEqual(index.read_text(encoding="utf-8"), before)

    def test_apply_updates_markdown_then_deletes_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codeops = self.make_feature(root)
            self.commit_fixture(root)
            result = self.run_migrator(codeops, "--apply")
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = codeops / "features" / "billing" / "plans" / "billing-plan"
            self.assertEqual(inspect_plan(plan).implements, ("billing/RD-01", "billing/RD-02"))
            self.assertFalse((codeops / "features" / "billing" / "traceability.json").exists())
            second_preview = self.run_migrator(codeops)
            self.assertEqual(second_preview.returncode, 0, second_preview.stdout + second_preview.stderr)
            self.assertNotIn("UPDATE", second_preview.stdout)

    def test_ambiguous_mapping_blocks_every_write_and_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codeops = self.make_feature(root, plans=("first", "second"), roadmap=False)
            self.commit_fixture(root)
            result = self.run_migrator(codeops, "--apply")
            self.assertEqual(result.returncode, 1)
            self.assertIn("cannot infer implemented targets", result.stdout)
            self.assertTrue((codeops / "features" / "billing" / "traceability.json").is_file())
            for plan_name in ("first", "second"):
                index = codeops / "features" / "billing" / "plans" / plan_name / "00-index.md"
                self.assertNotIn("**Implements**", index.read_text(encoding="utf-8"))

    def test_single_plan_single_rd_is_an_unambiguous_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), rds=("RD-AP-001",), roadmap=False)
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("billing/RD-AP-001 (single plan and single RD)", result.stdout)

    def test_archived_features_are_included(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), rds=("RD-01",), roadmap=False)
            archive = codeops / "_archive"
            archive.mkdir()
            (codeops / "features" / "billing").rename(archive / "billing")
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("DELETE _archive/billing/traceability.json", result.stdout)

    def test_roadmap_tracker_creates_missing_index_from_execution_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            codeops = self.make_feature(root, rds=(), roadmap=False)
            feature = codeops / "features" / "billing"
            plan = feature / "plans" / "billing-plan"
            (plan / "00-index.md").unlink()
            (feature / "00-roadmap.md").write_text(
                "# Roadmap\n\n| ID | Title | RD | Plan |\n|---|---|---|---|\n"
                "| T-01 | Cleanup | — | [plan](plans/billing-plan/99-execution-plan.md) |\n",
                encoding="utf-8",
            )
            self.commit_fixture(root)
            result = self.run_migrator(codeops, "--apply")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            index = plan / "00-index.md"
            self.assertIn("> **Implements**: billing/T-01", index.read_text(encoding="utf-8"))
            self.assertEqual(inspect_plan(plan).implements, ("billing/T-01",))

    def test_plan_local_requirement_is_recovered_from_legacy_graph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), rds=(), roadmap=False)
            graph = codeops / "features" / "billing" / "traceability.json"
            graph.write_text(
                '{"nodes": ['
                '{"id":"REQ-IMPORT","type":"requirement","semanticSources":['
                '{"path":"codeops/features/billing/plans/billing-plan/01-requirements.md"}]},'
                '{"id":"PLAN-IMPORT","type":"plan","semanticSources":['
                '{"path":"codeops/features/billing/plans/billing-plan/00-index.md"}],"edges":[]}'
                ']}\n',
                encoding="utf-8",
            )
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("billing/REQ-IMPORT (legacy graph)", result.stdout)

    def test_archived_feature_without_graph_is_out_of_scope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), rds=("RD-01",), roadmap=False)
            archive_feature = codeops / "_archive" / "unrelated"
            plan = archive_feature / "plans" / "ambiguous"
            plan.mkdir(parents=True)
            (plan / "99-execution-plan.md").write_text("# Execution\n\n- [ ] T-1 Build\n", encoding="utf-8")
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("unrelated", result.stdout)

    def test_rd_reference_in_index_metadata_is_an_explicit_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), plans=("first", "second"), roadmap=False)
            index = codeops / "features" / "billing" / "plans" / "first" / "00-index.md"
            index.write_text("# First\n\n> **Type**: Remediation follow-up to RD-02\n", encoding="utf-8")
            second = codeops / "features" / "billing" / "plans" / "second" / "00-index.md"
            second.write_text("# Second\n\n> **Implements**: billing/RD-01\n", encoding="utf-8")
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("billing/RD-02 (plan metadata)", result.stdout)

    def test_lightweight_task_id_in_execution_title_is_an_explicit_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            codeops = self.make_feature(Path(directory), rds=(), roadmap=False)
            plan = codeops / "features" / "billing" / "plans" / "billing-plan"
            (plan / "00-index.md").unlink()
            (plan / "99-execution-plan.md").write_text(
                "# Task T-07: Repair release\n\n- [x] T-07.1 Verified\n", encoding="utf-8"
            )
            result = self.run_migrator(codeops)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("billing/T-07 (plan metadata)", result.stdout)


if __name__ == "__main__":
    unittest.main()
