#!/usr/bin/env python3
"""Implementation tests for progress-bar validation and CLI boundaries."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from scripts.codeops_plan import render_progress


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_plan.py"


class ProgressBarImplementationTests(unittest.TestCase):
    """Cover defensive behavior outside the user-facing progress specification."""

    def test_progress_bar_rejects_invalid_counts(self) -> None:
        """Negative, inverted, boolean, and non-integer counts fail explicitly."""
        invalid_calls = (
            (-1, 3, ValueError),
            (4, 3, ValueError),
            (True, 3, TypeError),
            (1, 3.0, TypeError),
        )
        for verified, total, error in invalid_calls:
            with self.subTest(verified=verified, total=total):
                with self.assertRaises(error):
                    render_progress(verified, total)

    def test_progress_bar_handles_an_empty_checklist_without_division(self) -> None:
        """A structurally invalid empty plan still has a safe diagnostic representation."""
        self.assertEqual(
            render_progress(0, 0),
            "Progress: [░░░░░░░░░░] 0/0 tasks (0%)",
        )

    def test_cli_rejects_conflicting_output_formats(self) -> None:
        """Machine-readable JSON and human progress output cannot be requested together."""
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json", "--progress-bar"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with argument", result.stderr)


if __name__ == "__main__":
    unittest.main()
