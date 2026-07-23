#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "_shared/auto-design.md"
SUPPORTED = (
    "skills/make-requirements/SKILL.md",
    "skills/make-plan/SKILL.md",
    "skills/preflight/SKILL.md",
    "skills/exec-plan/SKILL.md",
)


class AutoDesignSpecification(unittest.TestCase):
    def policy(self) -> str:
        return POLICY.read_text(encoding="utf-8")

    def test_ad_st_1_normal_mode_remains_user_owned(self) -> None:
        for relative in SUPPORTED:
            with self.subTest(skill=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("Normal mode:", text)
                self.assertIn("explicit user decision", text)
                self.assertIn("must not infer delegated authority", text)

    def test_ad_st_2_supported_skills_activate_exact_flag(self) -> None:
        for relative in SUPPORTED:
            with self.subTest(skill=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("## Auto-design option", text)
                self.assertIn("exact standalone `--auto-design` token", text)
                self.assertIn("remove it before resolving targets, paths, or modes", text)
                self.assertIn("announce `Auto-design active", text)
                self.assertIn("../../_shared/auto-design.md", text)
                self.assertIn("unsupported child fails closed", text)

    def test_ad_st_3_eligible_decision_uses_quality_rubric(self) -> None:
        text = self.policy()
        for token in ("correctness", "safety", "maintainability", "verifiability",
                      "performance", "compatibility", "recovery", "evolution"):
            self.assertIn(token, text)

    def test_ad_st_4_reserved_authority_is_closed(self) -> None:
        text = self.policy()
        for token in ("product behavior", "legal", "financial exposure", "credentials",
                      "destructive", "deployment", "external communication"):
            self.assertIn(token, text)

    def test_ad_st_5_action_permissions_are_orthogonal(self) -> None:
        text = self.policy()
        self.assertIn("does not grant action permission", text)
        self.assertIn("--auto-commit", text)
        for relative in SUPPORTED:
            with self.subTest(skill=relative):
                self.assertIn(
                    "does not grant action permission",
                    (ROOT / relative).read_text(encoding="utf-8"),
                )

    def test_ad_st_6_insufficient_evidence_escalates_once(self) -> None:
        text = self.policy()
        self.assertIn("bounded escalation", text)
        self.assertIn("never guess", text)

    def test_ad_st_7_invalidated_decision_reopens(self) -> None:
        text = self.policy()
        self.assertIn("reopen", text)
        self.assertIn("downstream", text)
        self.assertIn("stale", text)

    def test_ad_st_8_nested_authority_only_narrows(self) -> None:
        text = self.policy()
        self.assertIn("root invocation ID", text)
        self.assertIn("narrow", text)
        self.assertIn("never widen", text)

    def test_ad_st_9_delegated_record_has_complete_provenance(self) -> None:
        text = self.policy()
        for token in ("Authority: AI — delegated by --auto-design", "eligibility",
                      "rejected alternatives", "counterargument", "confidence",
                      "policy version", "reopen triggers"):
            self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
