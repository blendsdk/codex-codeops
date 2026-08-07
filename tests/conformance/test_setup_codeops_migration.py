#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "setup-codeops" / "SKILL.md"
MIGRATION = ROOT / "skills" / "setup-codeops" / "migration.md"


class SetupCodeOpsMigrationTests(unittest.TestCase):
    def test_legacy_graph_detection_precedes_configured_noop(self) -> None:
        text = SKILL.read_text(encoding="utf-8")
        graph_detection = text.index("codeops/features/*/traceability.json")
        marker_noop = text.index("codeops/.codeops.yml present")
        self.assertLess(graph_detection, marker_noop)

    def test_yes_uses_preview_apply_and_verification_without_bypassing_safety(self) -> None:
        text = (SKILL.read_text(encoding="utf-8") + MIGRATION.read_text(encoding="utf-8")).lower()
        for token in (
            "codeops_plan_migrate.py",
            "--apply",
            "codeops_plan.py",
            "--root . --json",
            "--yes",
            "blocked",
            "clean",
            "idempot",
        ):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
