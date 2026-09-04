#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    """Return one repository policy file as UTF-8 text."""

    return (ROOT / relative).read_text(encoding="utf-8")


class ComplexityEscalationImplementation(unittest.TestCase):
    """Verify that each workflow entry point carries the shared contract."""

    def test_dispatched_executor_packet_and_templates_have_the_same_inputs(self) -> None:
        paths = (
            "_shared/quality-profile.md",
            "skills/exec-plan/execution-protocol.md",
            "agent-templates/plan-task-executor.md",
            "agent-templates/plan-task-executor-opus.md",
        )
        for relative in paths:
            with self.subTest(path=relative):
                text = read(relative)
                self.assertIn("original goal", text)
                self.assertIn("smallest viable design", text)

    def test_requirements_and_plan_finalizers_accept_only_safe_deferrals(self) -> None:
        paths = (
            "skills/make-requirements/SKILL.md",
            "skills/make-plan/quality-checklist.md",
        )
        for relative in paths:
            with self.subTest(path=relative):
                text = read(relative)
                self.assertNotIn("Zero deferred items", text)
                self.assertIn("deferred extra machinery", text)
                self.assertIn("absent", text)

    def test_preflight_previous_decision_rule_has_complexity_exception(self) -> None:
        skill = read("skills/preflight/SKILL.md")
        report = read("skills/preflight/report-format.md")
        self.assertIn("deferred complexity decision", skill)
        self.assertIn("**Complexity exception:**", report)
        self.assertIn("🟠 MAJOR", report)

    def test_mini_plan_conversion_covers_runtime_and_review_detection(self) -> None:
        skill = read("skills/exec-plan/SKILL.md")
        protocol = read("skills/exec-plan/execution-protocol.md")
        task_loop = protocol.split("Task completion is **two-stage**", 1)[1].split(
            "### Post-phase quality step", 1
        )[0]
        mini_branch_start = task_loop.index("For a T-NN mini-plan")
        full_branch_start = task_loop.index("For a full plan", mini_branch_start)
        mini_branch = task_loop[mini_branch_start:full_branch_start]

        self.assertIn("full standalone-plan", mini_branch)
        self.assertIn("preserve", mini_branch)
        self.assertIn("before dispatching", mini_branch)
        self.assertIn("presenting the packet", mini_branch)
        self.assertIn("accepting a decision", mini_branch)
        self.assertIn("[!]", task_loop[:mini_branch_start])
        self.assertIn("post-task review", skill)

    def test_optional_candidate_gate_follows_scope_confirmation(self) -> None:
        text = read("skills/make-requirements/discovery-phases.md")
        annotation = text.index("possible-cost note")
        confirmation = text.index("Run the gate only after")
        self.assertLess(annotation, confirmation)
        self.assertIn("before it becomes executable", text[confirmation:])


if __name__ == "__main__":
    unittest.main()
