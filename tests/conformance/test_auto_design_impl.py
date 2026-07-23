#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "_shared/auto-design.md"
SUPPORTED = {
    ROOT / "skills/make-requirements/SKILL.md",
    ROOT / "skills/make-plan/SKILL.md",
    ROOT / "skills/preflight/SKILL.md",
    ROOT / "skills/exec-plan/SKILL.md",
}


class AutoDesignImplementation(unittest.TestCase):
    def test_exact_token_contract_rejects_lookalikes(self) -> None:
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("exactly one standalone token", text)
        for lookalike in ("--auto-designer", "--auto-design=true", "auto-design"):
            self.assertRegex(text, re.escape(lookalike))

    def test_every_supported_skill_has_total_argument_rules(self) -> None:
        for path in SUPPORTED:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path):
                self.assertIn("before the first `--` sentinel", text)
                self.assertIn("zero occurrences means normal mode", text)
                self.assertIn("more than one is invalid", text)
                self.assertIn("tokens at or after the sentinel are target content", text)
                self.assertIn("remove it before resolving targets, paths, or modes", text)

    def test_supported_allowlist_is_closed(self) -> None:
        linked = {
            path
            for path in (ROOT / "skills").glob("*/SKILL.md")
            if "../../_shared/auto-design.md" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(linked, SUPPORTED)

    def test_nested_context_is_typed_and_downward_only(self) -> None:
        text = POLICY.read_text(encoding="utf-8")
        for token in (
            "root invocation ID",
            "parent workflow",
            "delegated categories",
            "reserved categories",
            "permission state",
            "never widen",
            "fails closed",
        ):
            self.assertIn(token, text)

    def test_reserved_authority_covers_hostile_boundaries(self) -> None:
        text = POLICY.read_text(encoding="utf-8")
        for token in (
            "credentials",
            "spending",
            "deployment",
            "publication",
            "destructive",
            "legal",
            "security policy",
            "different products",
        ):
            self.assertIn(token, text)

    def test_action_and_commit_permissions_remain_independent(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        execution = (ROOT / "skills/exec-plan/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("does not grant action permission", policy)
        self.assertIn("does not imply `--auto-commit`", execution)
        self.assertNotIn("auto-design automatically commits", policy.lower())
        forbidden = (
            "--auto-design authorizes",
            "--auto-design grants",
            "auto-design automatically applies",
            "auto-design automatically commits",
            "auto-design automatically pushes",
            "auto-design automatically deploys",
        )
        for path in SUPPORTED:
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(skill=path):
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

    def test_authoritative_paths_do_not_force_user_only_resolution(self) -> None:
        paths = (
            ROOT / "skills/preflight/SKILL.md",
            ROOT / "skills/preflight/report-format.md",
            ROOT / "skills/exec-plan/SKILL.md",
            ROOT / "skills/exec-plan/execution-protocol.md",
        )
        for path in paths:
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=path):
                self.assertIn("normal mode", text)
                self.assertIn("active auto-design", text)
        preflight = paths[0].read_text(encoding="utf-8")
        execution = paths[2].read_text(encoding="utf-8")
        self.assertIn("In normal mode, every finding", preflight)
        self.assertIn("With active auto-design, eligible technical resolutions", preflight)
        self.assertIn("In normal mode, 🔴 CRITICAL and 🟠 MAJOR findings", execution)
        self.assertIn("With active auto-design, select and record", execution)

    def test_critical_findings_cannot_be_auto_waived(self) -> None:
        preflight = (ROOT / "skills/preflight/SKILL.md").read_text(encoding="utf-8")
        protocol = (
            ROOT / "skills/exec-plan/execution-protocol.md"
        ).read_text(encoding="utf-8")
        self.assertIn("never auto-waive risk or dismiss a critical/major finding", preflight)
        self.assertIn("risk may never be waived", protocol)


if __name__ == "__main__":
    unittest.main()
