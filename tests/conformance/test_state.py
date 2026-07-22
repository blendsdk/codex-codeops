#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
FIXTURES = ROOT / "tests" / "fixtures"


class StateConformanceTests(unittest.TestCase):
    def run_state(self, fixture: str, command: str = "readiness") -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--root", str(FIXTURES / fixture), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_complete_graph_is_ready(self) -> None:
        code, payload = self.run_state("state-valid")
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["nodes"], 8)
        self.assertEqual(payload["problems"], [])

    def test_material_ambiguity_and_broken_link_block_readiness(self) -> None:
        code, payload = self.run_state("state-invalid")
        self.assertEqual(code, 1)
        self.assertFalse(payload["ready"])
        joined = "\n".join(payload["problems"])
        self.assertIn("links to missing node SPEC-MISSING", joined)
        self.assertIn("material ambiguity AR-001 is open", joined)
        self.assertIn("requirement RD-001 is not approved", joined)


if __name__ == "__main__":
    unittest.main()
