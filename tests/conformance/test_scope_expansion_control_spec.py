#!/usr/bin/env python3
"""Specification oracle for user-controlled optional scope exploration."""

from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "_shared/scope-expansion-control.md"
SUPPORTED = (
    "skills/make-plan/SKILL.md",
    "skills/preflight/SKILL.md",
    "skills/exec-plan/SKILL.md",
)


class ScopeExpansionControlSpecification(unittest.TestCase):
    """Verify the public workflow contract independently of its implementation details."""

    def policy(self) -> str:
        """Return the normative scope-expansion policy text."""

        return POLICY.read_text(encoding="utf-8")

    def test_default_mode_stays_strictly_inside_authorized_scope(self) -> None:
        """Optional additions must be silent and non-blocking unless exploration is requested."""

        text = self.policy()
        self.assertIn("Strict scope is the default", text)
        self.assertIn("do not report", text)
        self.assertIn("must not affect", text)
        for relative in SUPPORTED:
            with self.subTest(skill=relative):
                self.assertIn(
                    "Strict scope is the default",
                    (ROOT / relative).read_text(encoding="utf-8"),
                )

    def test_explore_scope_uses_an_exact_invocation_scoped_flag(self) -> None:
        """Only one exact flag before the sentinel may enable optional exploration."""

        for relative in SUPPORTED:
            with self.subTest(skill=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("## Scope exploration option", text)
                self.assertIn("exact standalone `--explore-scope` token", text)
                self.assertIn("before the first `--` sentinel", text)
                self.assertIn("zero occurrences means strict scope", text)
                self.assertIn("more than one is invalid", text)
                self.assertIn("tokens at or after the sentinel are target content", text)
                self.assertIn("remove it before resolving targets, paths, or modes", text)
                self.assertIn("../../_shared/scope-expansion-control.md", text)

    def test_necessary_corrections_are_always_reported(self) -> None:
        """Strict mode must still surface evidence that the requested behavior cannot work."""

        text = self.policy()
        for token in (
            "Necessary correction",
            "grounded causal evidence",
            "smallest correction",
            "no compliant solution",
            "blocking uncertainty",
            "always report",
            "burden of proof",
        ):
            self.assertIn(token, text)

    def test_optional_expansions_receive_stable_user_owned_decisions(self) -> None:
        """Explored additions must remain proposals until the user explicitly rules on them."""

        text = self.policy()
        for token in (
            "SE-001",
            "Proposed addition",
            "Origin",
            "Why it is outside scope",
            "Impact",
            "Recommendation",
            "user decision",
            "Keep",
            "Defer",
            "Discard",
        ):
            self.assertIn(token, text)
        self.assertIn("Only `Keep`", text)

    def test_finding_resolution_does_not_authorize_expansion(self) -> None:
        """Accepting or fixing a finding must not implicitly approve optional new scope."""

        text = self.policy()
        self.assertIn("Finding resolution and expansion authorization are separate", text)
        self.assertIn("apply all fixes", text)
        self.assertIn("does not authorize", text)

    def test_resume_preserves_discard_and_supersedes_derived_work(self) -> None:
        """A later run must not revive rejected work or leave removed work executable."""

        text = self.policy()
        for token in (
            "new evidence",
            "renewed authorization",
            "superseded",
            "must not remain executable",
            "resume",
            "dependency-traced",
            "specifications, tests, tasks, implementation, and verification",
            "never auto-revert",
        ):
            self.assertIn(token, text)

    def test_deferred_entries_remain_dormant_until_their_trigger(self) -> None:
        """Resuming a workflow must not repeatedly revive deferred optional proposals."""

        text = self.policy()
        for token in (
            "named owner",
            "observable revisit trigger",
            "dormant",
            "ordinary resume",
            "same `SE-*` ID",
            "never implies `Keep`",
        ):
            self.assertIn(token, text)

    def test_register_paths_are_target_qualified_and_collision_free(self) -> None:
        """Different governed targets in one directory must never share proposal identity."""

        policy = self.policy()
        layout = (ROOT / "_shared/layout-convention.md").read_text(encoding="utf-8")
        self.assertIn("_shared/layout-convention.md", policy)
        for token in (
            "Scope-expansion register",
            "00-scope-expansion-register.md",
            "00-scope-expansion-register-<document-name>.md",
            "scope-expansion-register-<artifact-name>.md",
            "Ad-hoc directory",
            "scope-expansion-register.md",
            "collision-free",
        ):
            self.assertIn(token, layout)

    def test_register_identity_is_monotonic_and_history_preserving(self) -> None:
        """Proposal IDs and prior user rulings must remain stable across every later run."""

        text = self.policy()
        for token in (
            "artifact-local",
            "monotonic",
            "never reused",
            "append-only history",
            "Decision",
            "Authority and evidence",
            "Derived artifact or graph target",
        ):
            self.assertIn(token, text)

    def test_auto_design_never_accepts_scope_expansions(self) -> None:
        """Technical-design delegation must remain subordinate to product-scope authority."""

        policy = self.policy()
        auto_design = (ROOT / "_shared/auto-design.md").read_text(encoding="utf-8")
        self.assertIn("`--auto-design` cannot choose `Keep`", policy)
        self.assertIn("scope expansion", auto_design)


if __name__ == "__main__":
    unittest.main()
