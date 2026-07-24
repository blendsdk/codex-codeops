#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / "scripts/codeops_state.py"


def read(path: str) -> str:
    return (ROOT / path).read_text()


class TargetedWorkflowSpecification(unittest.TestCase):
    def assert_contract(self, path: str, *tokens: str) -> None:
        content = read(path)
        for token in tokens:
            self.assertIn(token, content, f"{path} lacks {token!r}")

    def test_st_28_requirements_uses_exact_target(self) -> None:
        self.assert_contract("skills/make-requirements/SKILL.md", "--gate requirements", "--target <target>")

    def test_st_29_preflight_is_narrow(self) -> None:
        self.assert_contract("skills/preflight/SKILL.md", "--gate audit", "--target <target>", "modification set")

    def test_st_30_plan_uses_exact_target(self) -> None:
        self.assert_contract("skills/make-plan/SKILL.md", "--gate plan", "--target <target>")

    def test_st_31_execution_has_entry_and_task_gates(self) -> None:
        self.assert_contract(
            "skills/exec-plan/SKILL.md",
            "--gate execution",
            "--target <plan-target>",
            "`task-complete`",
            "--request <transition-request.json>",
        )

    def test_st_32_roadmap_keeps_siblings_independent(self) -> None:
        root = ROOT / "tests/fixtures/state-v2-cross-feature"
        graphs = sorted(root.glob("codeops/features/*/traceability.json"))
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in graphs]
        result = subprocess.run(
            [sys.executable, str(STATE), "status", "--root", str(root),
             "--target", "accounting/RD-001", "--json"],
            text=True, capture_output=True, check=False,
        )
        payload = json.loads(result.stdout)
        after = [hashlib.sha256(path.read_bytes()).hexdigest() for path in graphs]
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["target"], "accounting/RD-001")
        self.assertEqual(before, after)

    def test_st_33_feature_acceptance_is_explicit(self) -> None:
        root = ROOT / "tests/fixtures/state-v2-release"
        result = subprocess.run(
            [sys.executable, str(STATE), "readiness", "--root", str(root),
             "--gate", "release", "--target", "_releases/RELEASE-1", "--json"],
            text=True, capture_output=True, check=False,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, payload)
        self.assertTrue(payload["ready"])
        self.assertNotIn("_releases/TASK-OPT", payload["closure"])

    def test_st_34_public_workflow_commands_are_documented(self) -> None:
        self.assert_contract("docs/tutorial.md", "--gate requirements", "--gate execution")

    def test_execution_cannot_complete_with_missing_code_documentation(self) -> None:
        # Implementation is not complete until its public and non-trivial entities are understandable.
        self.assert_contract(
            "skills/exec-plan/execution-protocol.md",
            "Documentation-standard self-check (NON-NEGOTIABLE, before every `[x]`)",
            "every public, exported, or external-facing class",
            "every non-trivial internal entity is documented",
            "Missing required documentation blocks `[x]`",
        )
        for path in (
            "agent-templates/plan-task-executor.md",
            "agent-templates/plan-task-executor-opus.md",
        ):
            self.assert_contract(
                path,
                "Documentation gate (non-negotiable)",
                "Missing documentation blocks completion",
            )
        self.assert_contract(
            "agent-templates/phase-reviewer.md",
            "Documentation compliance",
            "Missing required documentation is a standards finding",
        )

    def test_st_40_collection_declares_all_cases(self) -> None:
        self.assertIn("set(range(1, 50))", read("tests/conformance/test_state_test_collection.py"))

    def test_st_41_codex_port_closes_only_with_pilot(self) -> None:
        plan = read("plans/codex-port/99-execution-plan.md")
        evidence = json.loads(read("tests/evidence/dependency-aware-readiness-pilot.json"))
        self.assertFalse(evidence["qualifiesForCodexPortTask6_8"])
        self.assertIn("- [ ] 6.8", plan)


if __name__ == "__main__":
    unittest.main()
