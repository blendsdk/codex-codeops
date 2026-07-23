#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import unittest

from scripts.codeops_state_lib.gates import evaluate_target
from scripts.codeops_state_lib.models import Edge, Node


ROOT = pathlib.Path(__file__).resolve().parents[2]


class TargetedWorkflowImplementation(unittest.TestCase):
    def test_task_completion_does_not_pull_sibling_tasks(self) -> None:
        def node(node_id: str, node_type: str, status: str, edges: tuple[Edge, ...] = ()) -> Node:
            return Node("sample", node_id, node_type, node_id, status, (), "sha256:x", edges, ())
        nodes = {
            "sample/PLAN": node("PLAN", "plan", "approved", (
                Edge("implemented-by", "sample/TASK-1"), Edge("implemented-by", "sample/TASK-2"),
            )),
            "sample/TASK-1": node("TASK-1", "task", "verified"),
            "sample/TASK-2": node("TASK-2", "task", "implemented"),
        }
        sources = {identity: ROOT / "plan.md" for identity in nodes}
        closure, problems = evaluate_target("sample/TASK-1", "task-complete", nodes, sources)
        self.assertNotIn("sample/TASK-2", closure.members)
        self.assertFalse(problems)

    def test_workflow_documents_have_no_legacy_feature_gate(self) -> None:
        for path in ("skills/make-plan/SKILL.md", "skills/exec-plan/SKILL.md"):
            self.assertNotIn("readiness --root . --feature", (ROOT / path).read_text())

    def test_public_document_links_resolve(self) -> None:
        for path in ("docs/concepts.md", "docs/tutorial.md", "docs/migration.md", "docs/troubleshooting.md"):
            self.assertTrue((ROOT / path).is_file())

    def test_roadmap_contract_names_explicit_aggregates(self) -> None:
        text = (ROOT / "skills/roadmap/SKILL.md").read_text()
        self.assertIn("--gate feature-acceptance", text)
        self.assertIn("--gate release", text)


if __name__ == "__main__":
    unittest.main()
