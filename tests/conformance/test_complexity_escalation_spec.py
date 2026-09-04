#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]


def read(relative: str) -> str:
    """Return one repository policy file as UTF-8 text."""

    return (ROOT / relative).read_text(encoding="utf-8")


class ComplexityEscalationSpecification(unittest.TestCase):
    """Protect the user-visible complexity approval contract."""

    def test_ce_st_1_executor_always_receives_comparison_baseline(self) -> None:
        for relative in (
            "skills/exec-plan/execution-protocol.md",
            "agent-templates/plan-task-executor.md",
            "agent-templates/plan-task-executor-opus.md",
        ):
            with self.subTest(path=relative):
                text = read(relative)
                self.assertIn("original goal", text)
                self.assertIn("smallest viable design", text)
                self.assertIn("fails closed", text)

    def test_ce_st_2_requirements_preserve_the_comparison_baseline(self) -> None:
        template = read("skills/make-requirements/templates.md")
        preflight = read("skills/preflight/dimensions.md")
        self.assertIn("## Minimum-Sufficient Baseline", template)
        self.assertIn("**Original goal:**", template)
        self.assertIn("**Smallest viable design:**", template)
        self.assertIn("legacy artifact", preflight)
        self.assertIn("do not infer it", preflight)

    def test_ce_st_3_mini_plan_cannot_own_a_complexity_approval(self) -> None:
        execution = read("skills/exec-plan/SKILL.md")
        protocol = read("skills/exec-plan/execution-protocol.md")
        task_loop = protocol.split("Task completion is **two-stage**", 1)[1].split(
            "### Post-phase quality step", 1
        )[0]
        self.assertIn("ends the mini-plan path", execution)
        self.assertIn("00-ambiguity-register.md", execution)
        self.assertIn("Do not accept or store a complexity approval only in the", execution)
        self.assertIn("For a T-NN mini-plan", task_loop)
        self.assertIn("before dispatching", task_loop)
        self.assertIn("or accepting a decision", task_loop)

    def test_ce_st_4_optional_discovery_does_not_warn_before_scope_choice(self) -> None:
        discovery = read("skills/make-requirements/discovery-phases.md")
        self.assertIn("Do not run the full Complexity", discovery)
        self.assertIn("Run the gate only after the user chooses", discovery)

    def test_ce_st_5_deferral_never_leaves_machinery_executable(self) -> None:
        gate = read("_shared/zero-ambiguity-gate.md")
        report = read("skills/preflight/report-format.md")
        self.assertIn("only after the machinery is absent", gate)
        self.assertIn("Deletion-only appearances", gate)
        self.assertIn("If it remains present", report)
        self.assertIn("keep the finding", report)

    def test_ce_st_6_security_does_not_bypass_generalized_mechanism_review(self) -> None:
        gate = read("_shared/zero-ambiguity-gate.md")
        self.assertIn("direct controls implemented through an existing", gate)
        self.assertIn("A new generalized mechanism", gate)
        self.assertIn("still triggers this gate", gate)


if __name__ == "__main__":
    unittest.main()
