#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "hooks"


class HookTests(unittest.TestCase):
    def test_marker_payload_warns_without_blocking(self) -> None:
        payload = (FIXTURES / "apply-patch-marker.json").read_text(encoding="utf-8")
        result = subprocess.run([str(ROOT / "scripts" / "hook_marker_guard.sh")], input=payload, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn("layout marker", result.stderr)

    def test_normal_patch_is_silent(self) -> None:
        payload = (FIXTURES / "apply-patch-normal.json").read_text(encoding="utf-8")
        result = subprocess.run([str(ROOT / "scripts" / "hook_marker_guard.sh")], input=payload, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_session_context_contains_both_standards(self) -> None:
        env = os.environ.copy()
        env["PLUGIN_ROOT"] = str(ROOT)
        result = subprocess.run([str(ROOT / "scripts" / "hook_session_context.sh")], env=env, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Coding standards", result.stdout)
        self.assertIn("Output style", result.stdout)


if __name__ == "__main__":
    unittest.main()
