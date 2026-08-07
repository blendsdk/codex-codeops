#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.codeops_plan import lifecycle, parse_tasks


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_plan.py"


class PlanStateImplementationTests(unittest.TestCase):
    def test_lifecycle_has_four_states(self) -> None:
        cases = {
            "- [ ] T-1 Start\n": "Ready",
            "- [~] T-1 Await verification\n": "Executing",
            "- [x] T-1 Verified\n": "Done",
            "- [!] T-1 Blocked: dependency unavailable\n": "Blocked",
        }
        for checklist, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(lifecycle(parse_tasks(checklist)), expected)

    def test_cli_needs_no_traceability_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan = root / "plans" / "sample"
            plan.mkdir(parents=True)
            (plan / "00-index.md").write_text(
                "# Sample\n\n> **Implements**: RD-01\n", encoding="utf-8"
            )
            (plan / "99-execution-plan.md").write_text(
                "# Execution Plan\n\n- [x] T-1 Verified\n", encoding="utf-8"
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"lifecycle": "Done"', result.stdout)
        self.assertFalse((root / "traceability.json").exists())

    def test_invalid_markers_are_not_silently_treated_as_progress(self) -> None:
        self.assertEqual(parse_tasks("- [?] T-1 Unknown\n"), ())

    def test_normal_workflows_do_not_invoke_removed_state_interface(self) -> None:
        workflows = (
            "make-requirements",
            "make-plan",
            "preflight",
            "exec-plan",
            "roadmap",
            "setup-codeops",
            "setup-routing",
            "upgrade-plan",
        )
        removed_tokens = ("codeops_state.py", "transition-request", "readiness --")
        for workflow in workflows:
            for path in (ROOT / "skills" / workflow).glob("*.md"):
                text = path.read_text(encoding="utf-8")
                for token in removed_tokens:
                    self.assertNotIn(token, text, f"{path} retains {token}")


if __name__ == "__main__":
    unittest.main()
