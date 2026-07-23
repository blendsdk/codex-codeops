#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any

from scripts.codeops_state_lib.models import Edge, Node
from scripts.codeops_state_lib.closure import build_closure
from scripts.codeops_state_lib.discovery import discover_graphs
from scripts.codeops_state_lib.schema import parse_graph_v2, validate_portfolio_v2


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
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
    def run_cli(
        self,
        root: Path,
        command: str,
        *args: str,
    ) -> tuple[int, dict[str, Any]]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--root", str(root), *args, "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

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

    def test_dependency_closure_is_sorted_with_shortest_paths(self) -> None:
        nodes = {
            identity: Node(
                "sample",
                identity.split("/", 1)[1],
                "requirement",
                identity,
                "approved",
                (),
                REVISION,
                tuple(edges),
                (),
            )
            for identity, edges in {
                "sample/RD-A": (
                    Edge("depends-on", "sample/RD-C"),
                    Edge("depends-on", "sample/RD-B"),
                ),
                "sample/RD-B": (
                    Edge("depends-on", "sample/RD-C"),
                ),
                "sample/RD-C": (),
            }.items()
        }
        closure = build_closure("sample/RD-A", "requirements", nodes)
        self.assertEqual(
            closure.members,
            ("sample/RD-A", "sample/RD-B", "sample/RD-C"),
        )
        self.assertEqual(
            closure.paths["sample/RD-C"],
            ("sample/RD-A", "sample/RD-C"),
        )

    def test_repository_discovery_excludes_fixture_graphs(self) -> None:
        discovered = discover_graphs(ROOT)
        self.assertEqual(len(discovered), 1)
        self.assertEqual(
            discovered[0].relative_to(ROOT).as_posix(),
            "codeops/features/dependency-aware-readiness/traceability.json",
        )
        fixture = ROOT / "tests" / "fixtures" / "state-v2-cross-feature"
        self.assertEqual(len(discover_graphs(fixture)), 2)

    def test_unrelated_semantic_error_is_diagnostic_not_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            for feature in ("valid", "unrelated"):
                (root / "codeops" / "features" / feature).mkdir(parents=True)
            valid = {"schema": 2, "feature": "valid", "nodes": [base_node("RD-001", "requirement")]}
            unrelated_node = base_node(
                "RD-002",
                "requirement",
                edges=[{"relation": "depends-on", "target": "unrelated/RD-MISSING"}],
            )
            unrelated = {"schema": 2, "feature": "unrelated", "nodes": [unrelated_node]}
            for feature, graph in (("valid", valid), ("unrelated", unrelated)):
                (root / "codeops" / "features" / feature / "traceability.json").write_text(
                    json.dumps(graph), encoding="utf-8"
                )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "valid/RD-001"
            )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["blockers"], [])
        self.assertIn("dangling-edge", {item["code"] for item in payload["diagnostics"]})

    def test_entered_invalid_graph_is_blocking_with_real_path(self) -> None:
        fixture = ROOT / "tests" / "fixtures" / "state-v2-cross-feature"
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            shutil.copytree(fixture, root, dirs_exist_ok=True)
            identity = root / "codeops" / "features" / "identity" / "traceability.json"
            identity.write_text('{"schema":2,"feature":"identity","nodes":"invalid"}', encoding="utf-8")
            code, payload = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "accounting/RD-001"
            )
        self.assertEqual(code, 1)
        self.assertIn("invalid-nodes", {item["code"] for item in payload["blockers"]})
        self.assertIn(
            ["accounting/RD-001", "identity/RD-001"],
            [item.get("path") for item in payload["blockers"]],
        )

    def test_mixed_schema_is_reported_and_schema1_target_requires_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            v2_root = root / "codeops" / "features" / "modern"
            v1_root = root / "codeops" / "features" / "legacy"
            v2_root.mkdir(parents=True)
            v1_root.mkdir(parents=True)
            (v2_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "modern", "nodes": [base_node("RD-001", "requirement")]}),
                encoding="utf-8",
            )
            (v1_root / "legacy.md").write_text("# Legacy\n", encoding="utf-8")
            (v1_root / "traceability.json").write_text(
                json.dumps({
                    "schema": 1,
                    "feature": "legacy",
                    "nodes": [{
                        "id": "RD-001", "type": "requirement", "title": "Legacy",
                        "status": "approved", "path": "legacy.md", "links": [],
                    }],
                }),
                encoding="utf-8",
            )
            validate_code, validate = self.run_cli(root, "validate")
            target_code, target = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "legacy/RD-001"
            )
        self.assertEqual(validate_code, 0, validate)
        self.assertEqual(validate["schema_versions"], [1, 2])
        self.assertEqual(validate["graphs"], 2)
        self.assertEqual(target_code, 1)
        self.assertIn("upgrade-required", {item["code"] for item in target["blockers"]})

    def test_unsafe_configured_root_is_globally_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config = root / "codeops"
            config.mkdir()
            (config / "codeops.json").write_text(
                json.dumps({"artifacts": {"root": "../outside"}}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("unsafe-config-root", {item["code"] for item in payload["blockers"]})

    def test_feature_member_gate_is_evaluated_recursively(self) -> None:
        feature = base_node(
            "FEATURE-1",
            "feature",
            members=["sample/TASK-1"],
            memberGates={"sample/TASK-1": "task-complete"},
        )
        task = base_node("TASK-1", "task", status="implemented")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [feature, task]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "feature-acceptance", "--target", "sample/FEATURE-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("sample/TASK-1", "\n".join(payload["problems"]))

    def test_plan_execution_and_superseded_evidence_predicates(self) -> None:
        plan = base_node("PLAN-1", "plan", evidence=[])
        task = base_node(
            "TASK-1",
            "task",
            status="verified",
            edges=[{"relation": "verified-by", "target": "sample/VERIFY-1"}],
        )
        verification = base_node("VERIFY-1", "verification", status="superseded")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [plan, task, verification]}),
                encoding="utf-8",
            )
            execution_code, execution = self.run_cli(
                root, "readiness", "--gate", "execution", "--target", "sample/PLAN-1"
            )
            complete_code, complete = self.run_cli(
                root, "readiness", "--gate", "task-complete", "--target", "sample/TASK-1"
            )
        self.assertEqual(execution_code, 1)
        self.assertIn("planned-test-required", {item["code"] for item in execution["blockers"]})
        self.assertIn("entry-evidence-required", {item["code"] for item in execution["blockers"]})
        self.assertEqual(complete_code, 1)
        self.assertIn("status-not-ready", {item["code"] for item in complete["blockers"]})

    def test_requirement_plan_gate_requires_explicit_approved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({
                    "schema": 2,
                    "feature": "sample",
                    "nodes": [base_node("RD-001", "requirement")],
                }),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "plan", "--target", "sample/RD-001"
            )
        self.assertEqual(code, 1)
        self.assertIn("approved-plan-required", {item["code"] for item in payload["blockers"]})

    def test_shared_decision_deferral_and_major_finding_blockers(self) -> None:
        requirement = base_node(
            "RD-001",
            "requirement",
            edges=[
                {"relation": "affected-by", "target": "sample/DECISION-1"},
                {"relation": "affected-by", "target": "sample/DEFERRAL-1"},
                {"relation": "affected-by", "target": "sample/FINDING-1"},
            ],
        )
        decision = base_node("DECISION-1", "decision", status="stale")
        deferral = base_node("DEFERRAL-1", "deferral", status="proposed")
        finding = base_node("FINDING-1", "finding", status="open", risk="high")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({
                    "schema": 2,
                    "feature": "sample",
                    "nodes": [requirement, decision, deferral, finding],
                }),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "sample/RD-001"
            )
        self.assertEqual(code, 1)
        codes = {item["code"] for item in payload["blockers"]}
        self.assertTrue(
            {"decision-not-current", "unapproved-deferral", "blocking-finding"} <= codes
        )

    def test_release_recursively_evaluates_required_requirement(self) -> None:
        release = base_node(
            "RELEASE-1",
            "release",
            required=["sample/RD-001"],
            optional=[],
            excluded=[],
        )
        requirement = base_node("RD-001", "requirement", status="draft")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({
                    "schema": 2,
                    "feature": "sample",
                    "nodes": [release, requirement],
                }),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "release", "--target", "sample/RELEASE-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("sample/RD-001", "\n".join(payload["problems"]))

    def test_requirement_set_expands_and_evaluates_members(self) -> None:
        aggregate = base_node(
            "SET-1",
            "requirement-set",
            members=["sample/RD-001"],
        )
        requirement = base_node("RD-001", "requirement", status="draft")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [aggregate, requirement]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "sample/SET-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("sample/RD-001", payload["closure"])

    def test_release_coupling_is_symmetric_for_closure(self) -> None:
        release = base_node(
            "RELEASE-1",
            "release",
            required=["sample/RD-B"],
            optional=[],
            excluded=[],
        )
        left = base_node(
            "RD-A",
            "requirement",
            edges=[{"relation": "release-coupled", "target": "sample/RD-B"}],
        )
        right = base_node("RD-B", "requirement")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [release, left, right]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "release", "--target", "sample/RELEASE-1"
            )
        self.assertEqual(code, 0, payload)
        self.assertIn("sample/RD-A", payload["closure"])

    def test_feature_member_gate_type_is_validated_before_recursion(self) -> None:
        feature = base_node(
            "FEATURE-1",
            "feature",
            members=["sample/TASK-1"],
            memberGates={"sample/TASK-1": "feature-acceptance"},
        )
        task = base_node("TASK-1", "task", status="verified")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [feature, task]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "feature-acceptance", "--target", "sample/FEATURE-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("incompatible-target", {item["code"] for item in payload["blockers"]})

    def test_planning_group_plan_gate_requires_owning_plan(self) -> None:
        group = base_node(
            "GROUP-1",
            "planning-group",
            members=["sample/RD-001"],
        )
        requirement = base_node("RD-001", "requirement")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [group, requirement]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "plan", "--target", "sample/GROUP-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("approved-plan-required", {item["code"] for item in payload["blockers"]})

    def test_audit_mapping_evaluates_verification_state(self) -> None:
        verification = base_node("VERIFY-1", "verification", status="failing")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            graph_root = root / "codeops" / "features" / "sample"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "sample", "nodes": [verification]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(
                root, "readiness", "--gate", "audit", "--target", "sample/VERIFY-1"
            )
        self.assertEqual(code, 1)
        self.assertIn("status-not-ready", {item["code"] for item in payload["blockers"]})

    def test_high_finding_blocks_but_low_finding_does_not(self) -> None:
        for risk, expected in (("high", 1), ("low", 0)):
            with self.subTest(risk=risk), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
                graph_root = root / "codeops" / "features" / "sample"
                graph_root.mkdir(parents=True)
                requirement = base_node(
                    "RD-001",
                    "requirement",
                    edges=[{"relation": "affected-by", "target": "sample/FINDING-1"}],
                )
                finding = base_node("FINDING-1", "finding", status="open", risk=risk)
                (graph_root / "traceability.json").write_text(
                    json.dumps({"schema": 2, "feature": "sample", "nodes": [requirement, finding]}),
                    encoding="utf-8",
                )
                code, payload = self.run_cli(
                    root, "readiness", "--gate", "requirements", "--target", "sample/RD-001"
                )
                self.assertEqual(code, expected, payload)

    def test_cross_version_identity_collision_is_global(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            config = root / "codeops"
            artifacts = config / "artifacts"
            (artifacts / "v1").mkdir(parents=True)
            (artifacts / "v2").mkdir(parents=True)
            (config / "codeops.json").write_text(
                json.dumps({
                    "schema": 1,
                    "mode": "strict",
                    "artifacts": {"layout": "nested", "root": "codeops/artifacts"},
                    "quality": {"independentReview": True},
                    "metrics": {"enabled": False},
                }),
                encoding="utf-8",
            )
            (artifacts / "v1" / "legacy.md").write_text("# Legacy\n", encoding="utf-8")
            (artifacts / "v1" / "traceability.json").write_text(
                json.dumps({
                    "schema": 1,
                    "feature": "same",
                    "nodes": [{
                        "id": "RD-001", "type": "requirement", "title": "Legacy",
                        "status": "approved", "path": "legacy.md", "links": [],
                    }],
                }),
                encoding="utf-8",
            )
            (artifacts / "v2" / "traceability.json").write_text(
                json.dumps({"schema": 2, "feature": "same", "nodes": [base_node("RD-001", "requirement")]}),
                encoding="utf-8",
            )
            code, payload = self.run_cli(root, "validate")
        self.assertEqual(code, 1)
        self.assertIn("duplicate-identity", {item["code"] for item in payload["blockers"]})

    def test_structural_scope_follows_only_selected_gate_relations(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            target_root = root / "codeops" / "features" / "target"
            evidence_root = root / "codeops" / "features" / "evidence"
            coupled_root = root / "codeops" / "features" / "coupled"
            for path in (target_root, evidence_root, coupled_root):
                path.mkdir(parents=True)
            target = base_node(
                "RD-001",
                "requirement",
                edges=[
                    {"relation": "specified-by", "target": "evidence/SPEC-001"},
                    {"relation": "release-coupled", "target": "coupled/RD-001"},
                ],
            )
            specification = base_node(
                "SPEC-001",
                "specification",
                edges=[{"relation": "depends-on", "target": "evidence/SPEC-001"}],
            )
            coupled = base_node(
                "RD-001",
                "requirement",
                edges=[{"relation": "depends-on", "target": "coupled/RD-MISSING"}],
            )
            for path, feature, nodes in (
                (target_root, "target", [target]),
                (evidence_root, "evidence", [specification]),
                (coupled_root, "coupled", [coupled]),
            ):
                (path / "traceability.json").write_text(
                    json.dumps({"schema": 2, "feature": feature, "nodes": nodes}),
                    encoding="utf-8",
                )
            requirements_code, requirements = self.run_cli(
                root, "readiness", "--gate", "requirements", "--target", "target/RD-001"
            )
            specifications_code, specifications = self.run_cli(
                root, "readiness", "--gate", "specifications", "--target", "target/RD-001"
            )
        self.assertEqual(requirements_code, 0, requirements)
        self.assertEqual(
            {"evidence", "coupled"},
            {item["feature"] for item in requirements["diagnostics"]},
        )
        self.assertEqual(specifications_code, 1)
        self.assertIn("evidence", {item.get("feature") for item in specifications["blockers"]})
        self.assertNotIn("coupled", {item.get("feature") for item in specifications["blockers"]})

    def test_release_accepts_and_rejects_terminal_evidence_members(self) -> None:
        cases = (
            ("test", "passing", "planned"),
            ("implementation", "verified", "present"),
            ("verification", "passing", "failing"),
        )
        for node_type, passing_status, failing_status in cases:
            for status, expected_code in ((passing_status, 0), (failing_status, 1)):
                with self.subTest(node_type=node_type, status=status), tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
                    graph_root = root / "codeops" / "features" / "sample"
                    graph_root.mkdir(parents=True)
                    evidence_id = {
                        "test": "TEST-1",
                        "implementation": "IMPL-1",
                        "verification": "VERIFY-1",
                    }[node_type]
                    release = base_node(
                        "RELEASE-1",
                        "release",
                        required=[f"sample/{evidence_id}"],
                        optional=[],
                        excluded=[],
                    )
                    evidence = base_node(evidence_id, node_type, status=status)
                    (graph_root / "traceability.json").write_text(
                        json.dumps({
                            "schema": 2,
                            "feature": "sample",
                            "nodes": [release, evidence],
                        }),
                        encoding="utf-8",
                    )
                    code, payload = self.run_cli(
                        root,
                        "readiness",
                        "--gate",
                        "release",
                        "--target",
                        "sample/RELEASE-1",
                    )
                    self.assertEqual(code, expected_code, payload)
                    if expected_code:
                        self.assertNotIn(
                            "incompatible-target",
                            {item["code"] for item in payload["blockers"]},
                        )


if __name__ == "__main__":
    unittest.main()
