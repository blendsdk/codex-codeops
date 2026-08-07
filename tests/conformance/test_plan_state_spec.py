#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.codeops_plan import inspect_plan, rd_delivery


class PlanStateSpecificationTests(unittest.TestCase):
    def make_plan(self, root: Path, implements: str, tasks: str, name: str = "sample") -> Path:
        plan = root / "plans" / name
        plan.mkdir(parents=True)
        (plan / "00-index.md").write_text(f"# Plan\n\n> **Implements**: {implements}\n", encoding="utf-8")
        (plan / "99-execution-plan.md").write_text(f"# Execution Plan\n\n{tasks}", encoding="utf-8")
        return plan

    def test_plan_can_implement_multiple_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = inspect_plan(self.make_plan(root, "RD-01, RD-02", "- [ ] T-1 Build\n"), root)
        self.assertEqual(status.implements, ("RD-01", "RD-02"))

    def test_resume_prefers_verification_pending_then_not_started(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = inspect_plan(
                self.make_plan(root, "RD-01", "- [ ] T-1 Later\n- [~] T-2 Verify this first\n"), root
            )
        self.assertEqual(status.next_task, "T-2 Verify this first")

    def test_blocked_task_requires_a_visible_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status = inspect_plan(self.make_plan(root, "RD-01", "- [!] T-1 Blocked: waiting for API\n"), root)
        self.assertEqual(status.lifecycle, "Blocked")
        self.assertFalse(status.problems)

    def test_requirement_delivery_is_derived_from_its_plan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            done = inspect_plan(self.make_plan(root, "RD-01, RD-02", "- [x] T-1 Verified\n"), root)
        self.assertEqual(rd_delivery((done,)), {"RD-01": "Done", "RD-02": "Done"})


if __name__ == "__main__":
    unittest.main()
