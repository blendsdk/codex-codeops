#!/usr/bin/env python3
"""Specification tests for the user-visible execution progress display."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import codeops_plan


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_plan.py"


class ProgressBarSpecificationTests(unittest.TestCase):
    """Verify the progress display promised to users during plan execution."""

    def test_progress_bar_has_ten_cells_and_accessible_numeric_context(self) -> None:
        """A partial display includes ten cells, counts, and a rounded percentage."""
        self.assertEqual(
            codeops_plan.render_progress(1, 3),
            "Progress: [███░░░░░░░] 1/3 tasks (33%)",
        )

    def test_progress_bar_is_empty_at_zero_and_full_at_completion(self) -> None:
        """Boundary states are visually exact and retain their numeric meaning."""
        self.assertEqual(
            codeops_plan.render_progress(0, 4),
            "Progress: [░░░░░░░░░░] 0/4 tasks (0%)",
        )
        self.assertEqual(
            codeops_plan.render_progress(4, 4),
            "Progress: [██████████] 4/4 tasks (100%)",
        )

    def test_progress_cli_counts_only_verified_markers_without_mutating_the_plan(self) -> None:
        """The display is derived from Markdown and treats verification-pending work as incomplete."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plans" / "sample"
            plan.mkdir(parents=True)
            (plan / "00-index.md").write_text(
                "# Sample\n\n> **Implements**: RD-01\n",
                encoding="utf-8",
            )
            execution = plan / "99-execution-plan.md"
            execution.write_text(
                "# Execution\n\n- [x] T-1 Verified\n- [~] T-2 Awaiting verification\n- [ ] T-3 Later\n",
                encoding="utf-8",
            )
            before = execution.read_bytes()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--plan",
                    str(plan),
                    "--progress-bar",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "Progress: [███░░░░░░░] 1/3 tasks (33%)\n")
            self.assertEqual(execution.read_bytes(), before)
            self.assertEqual(tuple(root.rglob("traceability.json")), ())


if __name__ == "__main__":
    unittest.main()
