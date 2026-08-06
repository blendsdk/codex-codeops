#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.codeops_hooks import NativeHookDependencies, run_hook


FIXTURES = ROOT / "tests" / "fixtures" / "hooks"


class PortableBehaviorDependencies(NativeHookDependencies):
    """Exercise production hook behavior after a deterministic successful gate."""

    def run_preflight(self, mode: str, payload: dict[str, object]) -> int:
        del mode, payload
        return 0


class HookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_plugin_root = os.environ.get("PLUGIN_ROOT")
        os.environ["PLUGIN_ROOT"] = str(ROOT)

    def tearDown(self) -> None:
        if self.previous_plugin_root is None:
            os.environ.pop("PLUGIN_ROOT", None)
        else:
            os.environ["PLUGIN_ROOT"] = self.previous_plugin_root

    def payload(self, name: str) -> dict[str, object]:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    def test_marker_payload_warns_without_blocking(self) -> None:
        result = run_hook(
            self.payload("apply-patch-marker.json"),
            PortableBehaviorDependencies(),
        )
        self.assertEqual(result.exit_code, 0)
        self.assertIn("layout marker", result.stderr)

    def test_normal_patch_is_silent(self) -> None:
        result = run_hook(
            self.payload("apply-patch-normal.json"),
            PortableBehaviorDependencies(),
        )
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stderr, "")

    def test_session_context_contains_both_standards(self) -> None:
        result = run_hook(
            self.payload("session-start-spaces.json"),
            PortableBehaviorDependencies(),
        )
        self.assertEqual(result.exit_code, 0, result.stderr)
        self.assertIn("Coding standards", result.stdout)
        self.assertIn("Output style", result.stdout)


if __name__ == "__main__":
    unittest.main()
