#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.codeops_state_lib.models import Node
from scripts.codeops_state_lib.schema import parse_graph_v2, validate_portfolio_v2


REVISION = "sha256:" + hashlib.sha256(b"# Artifact\n").hexdigest()


def base_node(node_id: str, node_type: str, **extra: Any) -> dict[str, Any]:
    value = {
        "id": node_id,
        "type": node_type,
        "title": node_id,
        "status": "approved",
        "semanticSources": [
            {
                "path": "artifact.md",
                "selector": {"kind": "whole-file"},
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            }
        ],
        "revision": REVISION,
        "edges": [],
        "validations": [],
    }
    value.update(extra)
    return value


class SchemaTwoImplementationTests(unittest.TestCase):
    def parse(
        self,
        nodes: list[dict[str, Any]],
        *,
        artifact: str = "# Artifact\n",
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text(artifact, encoding="utf-8")
            feature = root / "codeops" / "features" / "sample"
            feature.mkdir(parents=True)
            path = feature / "traceability.json"
            path.write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": nodes}),
                encoding="utf-8",
            )
            graph, problems = parse_graph_v2(path, root)
            if graph is not None:
                problems.extend(validate_portfolio_v2([graph]))
            return [f"{problem.code}: {problem.message}" for problem in problems]

    def test_illegal_relation_direction_is_rejected(self) -> None:
        problems = self.parse(
            [
                base_node(
                    "SPEC-001",
                    "specification",
                    edges=[{"relation": "specified-by", "target": "sample/RD-001"}],
                ),
                base_node("RD-001", "requirement"),
            ]
        )
        self.assertIn("illegal-edge", "\n".join(problems))

    def test_self_and_duplicate_edges_are_rejected(self) -> None:
        edge = {"relation": "depends-on", "target": "sample/RD-001"}
        duplicate = self.parse([base_node("RD-001", "requirement", edges=[edge, edge])])
        self.assertIn("duplicate-edge", "\n".join(duplicate))
        self_edge = self.parse([base_node("RD-001", "requirement", edges=[edge])])
        self.assertIn("self-edge", "\n".join(self_edge))

    def test_duplicate_identity_is_canonical(self) -> None:
        problems = self.parse(
            [base_node("RD-001", "requirement"), base_node("RD-001", "requirement")]
        )
        self.assertIn("duplicate canonical identity sample/RD-001", "\n".join(problems))

    def test_aggregate_members_are_sorted_unique_and_resolved(self) -> None:
        problems = self.parse(
            [
                base_node(
                    "SET-001",
                    "requirement-set",
                    members=["sample/RD-002", "sample/RD-001", "sample/RD-001"],
                ),
                base_node("RD-001", "requirement"),
            ]
        )
        rendered = "\n".join(problems)
        self.assertIn("invalid-members", rendered)
        self.assertIn("missing member sample/RD-002", rendered)

    def test_only_contract_may_carry_maturity(self) -> None:
        problems = self.parse([base_node("RD-001", "requirement", maturity="stable")])
        self.assertIn("may not carry maturity", "\n".join(problems))

    def test_cross_group_cycle_has_stable_path(self) -> None:
        nodes = [
            base_node(
                "RD-A",
                "requirement",
                edges=[{"relation": "depends-on", "target": "sample/RD-B"}],
            ),
            base_node(
                "RD-B",
                "requirement",
                edges=[{"relation": "depends-on", "target": "sample/RD-A"}],
            ),
        ]
        first = self.parse(nodes)
        second = self.parse(nodes)
        self.assertEqual(first, second)
        self.assertIn(
            "sample/RD-A -> sample/RD-B -> sample/RD-A",
            "\n".join(first),
        )

    def test_heading_selector_requires_a_value(self) -> None:
        item = base_node("RD-001", "requirement")
        item["semanticSources"][0]["selector"] = {"kind": "heading"}
        problems = self.parse([item])
        self.assertIn("invalid-source", "\n".join(problems))

    def test_heading_selector_must_match_exactly_once(self) -> None:
        item = base_node(
            "RD-001",
            "requirement",
            revision="sha256:" + hashlib.sha256(b"## Unique\nBody\n").hexdigest(),
        )
        item["semanticSources"][0]["selector"] = {"kind": "heading", "value": "Unique"}
        missing = self.parse([item], artifact="# Different\n")
        duplicate = self.parse(
            [item],
            artifact="# Root\n## Unique\nOne\n## Unique\nTwo\n",
        )
        valid = self.parse([item], artifact="# Root\n## Unique\nBody\n## Next\n")
        self.assertIn("source-selection", "\n".join(missing))
        self.assertIn("source-selection", "\n".join(duplicate))
        self.assertEqual(valid, [])

    def test_heading_selector_ignores_backtick_and_tilde_fences(self) -> None:
        item = base_node(
            "RD-001",
            "requirement",
            revision="sha256:" + hashlib.sha256(b"## Unique\nBody\n").hexdigest(),
        )
        item["semanticSources"][0]["selector"] = {"kind": "heading", "value": "Unique"}
        for marker in ("```", "~~~"):
            with self.subTest(marker=marker):
                artifact = (
                    f"# Root\n{marker}text\n## Unique\nfake\n{marker}\n"
                    "## Unique\nBody\n## Next\n"
                )
                self.assertEqual(self.parse([item], artifact=artifact), [])

    def test_heading_selector_accepts_up_to_three_spaces_of_indent(self) -> None:
        item = base_node(
            "RD-001",
            "requirement",
            revision="sha256:" + hashlib.sha256(b"   ## Unique\nBody\n").hexdigest(),
        )
        item["semanticSources"][0]["selector"] = {"kind": "heading", "value": "Unique"}
        self.assertEqual(
            self.parse([item], artifact="# Root\n   ## Unique\nBody\n## Next\n"),
            [],
        )

    def test_fence_marker_with_text_does_not_close_the_fence(self) -> None:
        item = base_node(
            "RD-001",
            "requirement",
            revision="sha256:" + hashlib.sha256(b"## Unique\nReal\n").hexdigest(),
        )
        item["semanticSources"][0]["selector"] = {"kind": "heading", "value": "Unique"}
        for marker in ("```", "~~~"):
            with self.subTest(marker=marker):
                artifact = (
                    f"# Root\n{marker}text\n{marker}not-a-close\n"
                    f"## Unique\nFake\n{marker}\n## Unique\nReal\n## Next\n"
                )
                self.assertEqual(self.parse([item], artifact=artifact), [])

    def test_source_path_cannot_escape_project_root(self) -> None:
        item = base_node("RD-001", "requirement")
        item["semanticSources"][0]["path"] = "../../../../outside.md"
        problems = self.parse([item])
        self.assertIn("path-escape", "\n".join(problems))

    def test_release_and_audit_conditional_fields_are_required(self) -> None:
        release = base_node("RELEASE-1", "release")
        audit = base_node("AUDIT-1", "audit-artifact")
        problems = self.parse([release, audit])
        rendered = "\n".join(problems)
        self.assertIn("missing-release-members", rendered)
        self.assertIn("invalid-audit-stage", rendered)

    def test_release_membership_arrays_reject_duplicates(self) -> None:
        for field_name in ("required", "optional", "excluded"):
            with self.subTest(field=field_name):
                member = base_node("RD-001", "requirement")
                release = base_node(
                    "RELEASE-1",
                    "release",
                    required=[],
                    optional=[],
                    excluded=[],
                )
                release[field_name] = ["sample/RD-001", "sample/RD-001"]
                problems = self.parse([member, release])
                self.assertIn("duplicate-release-member", "\n".join(problems))

    def test_contract_vocabularies_and_uniqueness_are_enforced(self) -> None:
        item = base_node(
            "RD-001",
            "requirement",
            risk="urgent",
            evidence=["proof.txt", "proof.txt"],
        )
        rendered = "\n".join(self.parse([item]))
        self.assertIn("invalid-risk", rendered)
        self.assertIn("invalid-evidence", rendered)

    def test_reverse_symmetric_relationship_is_rejected(self) -> None:
        problems = self.parse(
            [
                base_node(
                    "RD-A",
                    "requirement",
                    edges=[{"relation": "related", "target": "sample/RD-B"}],
                ),
                base_node(
                    "RD-B",
                    "requirement",
                    edges=[{"relation": "related", "target": "sample/RD-A"}],
                ),
            ]
        )
        self.assertIn("redundant-relationship", "\n".join(problems))

    def test_member_gates_are_immutable_after_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            feature = root / "codeops" / "features" / "sample"
            feature.mkdir(parents=True)
            member = base_node("TASK-1", "task", status="verified")
            aggregate = base_node(
                "FEATURE-1",
                "feature",
                members=["sample/TASK-1"],
                memberGates={"sample/TASK-1": "task-complete"},
            )
            path = feature / "traceability.json"
            path.write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [member, aggregate]}),
                encoding="utf-8",
            )
            graph, problems = parse_graph_v2(path, root)
            self.assertEqual(problems, [])
            assert graph is not None
            parsed = graph.by_identity()["sample/FEATURE-1"]
            with self.assertRaises(TypeError):
                parsed.member_gates["sample/TASK-1"] = "release"  # type: ignore[index]

    def test_direct_node_construction_defensively_freezes_member_gates(self) -> None:
        source = {"sample/TASK-1": "task-complete"}
        parsed = Node(
            "sample",
            "FEATURE-1",
            "feature",
            "Feature",
            "approved",
            (),
            REVISION,
            (),
            (),
            members=("sample/TASK-1",),
            member_gates=source,
        )
        source["sample/TASK-1"] = "release"
        self.assertEqual(parsed.member_gates["sample/TASK-1"], "task-complete")
        with self.assertRaises(TypeError):
            parsed.member_gates["sample/TASK-1"] = "release"  # type: ignore[index]

    def test_invalid_utf8_source_is_a_structural_problem(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_bytes(b"\xff\xfe")
            feature = root / "codeops" / "features" / "sample"
            feature.mkdir(parents=True)
            path = feature / "traceability.json"
            path.write_text(
                json.dumps(
                    {
                        "schema": 2,
                        "feature": "sample",
                        "nodes": [base_node("RD-001", "requirement")],
                    }
                ),
                encoding="utf-8",
            )
            graph, problems = parse_graph_v2(path, root)
        self.assertIsNotNone(graph)
        self.assertIn("source-not-utf8", "\n".join(problem.code for problem in problems))


if __name__ == "__main__":
    unittest.main()
