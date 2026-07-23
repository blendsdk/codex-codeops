#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
REVISION = "sha256:" + hashlib.sha256(b"# Artifact\n").hexdigest()


def node(
    node_id: str,
    node_type: str,
    *,
    status: str = "approved",
    edges: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    value = {
        "id": node_id,
        "type": node_type,
        "title": node_id,
        "status": status,
        "semanticSources": [
            {
                "path": "artifact.md",
                "selector": {"kind": "whole-file"},
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            }
        ],
        "revision": REVISION,
        "edges": edges or [],
        "validations": [],
    }
    value.update(extra)
    return value


def snapshot(upstream: str, relation: str, gate: str) -> dict[str, str]:
    return {
        "upstream": upstream,
        "relation": relation,
        "revision": REVISION,
        "gate": gate,
        "validatedAt": "2026-07-23T00:00:00Z",
    }


class SchemaTwoSpecificationTests(unittest.TestCase):
    maxDiff = None

    def run_state(
        self,
        graphs: dict[str, dict[str, Any]],
        command: str = "validate",
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            for feature, graph in graphs.items():
                graph_root = root / "codeops" / "features" / feature
                graph_root.mkdir(parents=True)
                (graph_root / "traceability.json").write_text(
                    json.dumps(graph),
                    encoding="utf-8",
                )
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    command,
                    "--root",
                    str(root),
                    *arguments,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

    @staticmethod
    def graph(feature: str, nodes: list[dict[str, Any]]) -> dict[str, Any]:
        return {"schema": 2, "feature": feature, "nodes": nodes}

    def payload(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def test_st_1_valid_directed_typed_edge(self) -> None:
        graph = self.graph(
            "accounting",
            [
                node(
                    "RD-001",
                    "requirement",
                    edges=[{"relation": "specified-by", "target": "accounting/SPEC-001"}],
                ),
                node("SPEC-001", "specification"),
            ],
        )

        result = self.run_state({"accounting": graph})

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.payload(result)["ready"])

    def test_st_2_rejects_persisted_inverse_and_names_canonical_relation(self) -> None:
        graph = self.graph(
            "accounting",
            [
                node(
                    "SPEC-001",
                    "specification",
                    edges=[{"relation": "blocks", "target": "accounting/RD-001"}],
                ),
                node("RD-001", "requirement"),
            ],
        )

        result = self.run_state({"accounting": graph})
        problems = "\n".join(self.payload(result)["problems"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("blocks", problems)
        self.assertIn("depends-on", problems)

    def test_st_5_bare_target_is_rejected_without_guessing(self) -> None:
        graph = self.graph("accounting", [node("RD-001", "requirement")])

        result = self.run_state(
            {"accounting": graph},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "RD-001",
        )
        problems = "\n".join(self.payload(result)["problems"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("canonical", problems)
        self.assertIn("--feature", problems)

    def test_st_7_duplicate_canonical_identity_blocks_validation(self) -> None:
        graph = self.graph(
            "accounting",
            [node("RD-001", "requirement"), node("RD-001", "requirement")],
        )

        result = self.run_state({"accounting": graph})

        self.assertEqual(result.returncode, 1)
        self.assertIn("accounting/RD-001", "\n".join(self.payload(result)["problems"]))

    def test_st_8_related_edge_does_not_enter_readiness_closure(self) -> None:
        graph = self.graph(
            "accounting",
            [
                node(
                    "RD-001",
                    "requirement",
                    edges=[{"relation": "related", "target": "accounting/RD-002"}],
                ),
                node("RD-002", "requirement", status="draft"),
            ],
        )

        result = self.run_state(
            {"accounting": graph},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "accounting/RD-001",
        )
        payload = self.payload(result)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(payload["target"], "accounting/RD-001")
        self.assertNotIn("accounting/RD-002", payload["closure"])

    def test_st_15_contract_maturity_blocks_consumer(self) -> None:
        graph = self.graph(
            "compiler",
            [
                node(
                    "PLAN-001",
                    "plan",
                    edges=[
                        {
                            "relation": "consumes-contract",
                            "target": "compiler/CONTRACT-IR",
                            "requiredMaturity": "stable",
                        }
                    ],
                    validations=[
                        snapshot("compiler/CONTRACT-IR", "consumes-contract", "plan")
                    ],
                ),
                node("CONTRACT-IR", "contract", maturity="provisional"),
            ],
        )

        result = self.run_state(
            {"compiler": graph},
            "readiness",
            "--gate",
            "plan",
            "--target",
            "compiler/PLAN-001",
        )
        problems = "\n".join(self.payload(result)["problems"])

        self.assertEqual(result.returncode, 1)
        self.assertIn("stable", problems)
        self.assertIn("provisional", problems)

    def test_st_16_stronger_contract_maturity_satisfies_consumer(self) -> None:
        graph = self.graph(
            "compiler",
            [
                node(
                    "PLAN-001",
                    "plan",
                    edges=[
                        {
                            "relation": "consumes-contract",
                            "target": "compiler/CONTRACT-IR",
                            "requiredMaturity": "provisional",
                        }
                    ],
                    validations=[
                        snapshot("compiler/CONTRACT-IR", "consumes-contract", "plan")
                    ],
                ),
                node("CONTRACT-IR", "contract", maturity="stable"),
            ],
        )

        result = self.run_state(
            {"compiler": graph},
            "readiness",
            "--gate",
            "plan",
            "--target",
            "compiler/PLAN-001",
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_st_17_planning_group_expands_atomically(self) -> None:
        graph = self.graph(
            "compiler",
            [
                node("RD-LEX", "requirement"),
                node("RD-PARSE", "requirement"),
                node(
                    "GROUP-FRONTEND",
                    "planning-group",
                    members=["compiler/RD-LEX", "compiler/RD-PARSE"],
                ),
            ],
        )

        result = self.run_state(
            {"compiler": graph},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "compiler/RD-LEX",
        )
        payload = self.payload(result)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            set(payload["group_expansions"]["compiler/GROUP-FRONTEND"]),
            {"compiler/RD-LEX", "compiler/RD-PARSE"},
        )

    def test_st_18_cycle_after_group_contraction_is_deterministic(self) -> None:
        graph = self.graph(
            "compiler",
            [
                node(
                    "RD-LEX",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "compiler/RD-TYPE"}],
                ),
                node(
                    "RD-TYPE",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "compiler/RD-LEX"}],
                ),
            ],
        )

        first = self.run_state({"compiler": graph})
        second = self.run_state({"compiler": graph})
        first_problems = self.payload(first)["problems"]

        self.assertEqual(first.returncode, 1)
        self.assertEqual(first_problems, self.payload(second)["problems"])
        self.assertIn(
            "compiler/RD-LEX -> compiler/RD-TYPE -> compiler/RD-LEX",
            "\n".join(first_problems),
        )

    def test_st_42_revision_normalization_is_content_based(self) -> None:
        normalized = "# Artifact\n\nMeaningful text\n"
        revision = "sha256:" + hashlib.sha256(normalized.encode()).hexdigest()
        graph = self.graph(
            "compiler",
            [node("RD-LEX", "requirement", revision=revision)],
        )
        variants = (
            "\ufeff# Artifact\r\n\r\nMeaningful text   \r\n",
            "# Artifact\r\rMeaningful text\r",
            "# Artifact\n\nMeaningful text\n\n",
        )
        for content in variants:
            with self.subTest(content=repr(content)):
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    (root / "artifact.md").write_text(content, encoding="utf-8", newline="")
                    graph_root = root / "codeops" / "features" / "compiler"
                    graph_root.mkdir(parents=True)
                    (graph_root / "traceability.json").write_text(
                        json.dumps(graph),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(SCRIPT),
                            "validate",
                            "--root",
                            str(root),
                            "--json",
                        ],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                self.assertEqual(result.returncode, 0, result.stdout)

        changed = self.graph(
            "compiler",
            [node("RD-LEX", "requirement", revision=revision)],
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text(
                "# Artifact\n\nChanged text\n",
                encoding="utf-8",
            )
            graph_root = root / "codeops" / "features" / "compiler"
            graph_root.mkdir(parents=True)
            (graph_root / "traceability.json").write_text(
                json.dumps(changed),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--root", str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("revision-mismatch", result.stdout)

        ordered_payload = "# A\n# B\n"
        ordered_revision = "sha256:" + hashlib.sha256(ordered_payload.encode()).hexdigest()
        sources = [
            {
                "path": "a.md",
                "selector": {"kind": "whole-file"},
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            },
            {
                "path": "b.md",
                "selector": {"kind": "whole-file"},
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            },
        ]
        for declaration in (sources, list(reversed(sources))):
            with self.subTest(order=[source["path"] for source in declaration]):
                graph = self.graph(
                    "compiler",
                    [
                        node(
                            "RD-LEX",
                            "requirement",
                            semanticSources=declaration,
                            revision=ordered_revision,
                        )
                    ],
                )
                with tempfile.TemporaryDirectory() as raw:
                    root = Path(raw)
                    (root / "a.md").write_text("# A\n", encoding="utf-8")
                    (root / "b.md").write_text("# B\n", encoding="utf-8")
                    graph_root = root / "codeops" / "features" / "compiler"
                    graph_root.mkdir(parents=True)
                    (graph_root / "traceability.json").write_text(
                        json.dumps(graph),
                        encoding="utf-8",
                    )
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), "validate", "--root", str(root), "--json"],
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                self.assertEqual(result.returncode, 0, result.stdout)

    def test_gate_profile_matrix_rejects_non_ready_target_state(self) -> None:
        cases = (
            ("requirements", node("RD-001", "requirement", status="draft")),
            ("specifications", node("SPEC-001", "specification", status="draft")),
            ("plan", node("PLAN-001", "plan", status="draft")),
            (
                "audit",
                node(
                    "AUDIT-001",
                    "audit-artifact",
                    status="draft",
                    auditStage="requirements",
                ),
            ),
            ("execution", node("PLAN-001", "plan", status="draft")),
            ("task-complete", node("TASK-001", "task", status="implemented")),
            (
                "feature-acceptance",
                node(
                    "FEATURE-001",
                    "feature",
                    status="draft",
                    members=["sample/TASK-001"],
                    memberGates={"sample/TASK-001": "task-complete"},
                ),
            ),
            (
                "release",
                node(
                    "RELEASE-001",
                    "release",
                    status="draft",
                    required=["sample/TASK-001"],
                    optional=[],
                    excluded=[],
                ),
            ),
        )
        for gate, target_node in cases:
            with self.subTest(gate=gate):
                nodes = [target_node]
                if gate in {"feature-acceptance", "release"}:
                    nodes.append(node("TASK-001", "task", status="verified"))
                graph = self.graph("sample", nodes)
                result = self.run_state(
                    {"sample": graph},
                    "readiness",
                    "--gate",
                    gate,
                    "--target",
                    f"sample/{target_node['id']}",
                )
                payload = self.payload(result)
                self.assertEqual(result.returncode, 1, payload)
                self.assertFalse(payload["ready"])
                self.assertEqual(payload["gate"], gate)
                self.assertEqual(payload["target"], f"sample/{target_node['id']}")
                self.assertTrue(
                    any("status" in problem for problem in payload["problems"]),
                    payload,
                )

    def test_st_3_canonical_target_resolves_exactly(self) -> None:
        graph = self.graph("accounting", [node("RD-001", "requirement")])
        result = self.run_state(
            {"accounting": graph},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "accounting/RD-001",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.payload(result)["target"], "accounting/RD-001")

    def test_st_4_feature_scoped_target_resolves_exactly(self) -> None:
        graph = self.graph("accounting", [node("RD-001", "requirement")])
        result = self.run_state(
            {"accounting": graph},
            "readiness",
            "--gate",
            "requirements",
            "--feature",
            "accounting",
            "--target",
            "RD-001",
        )
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.payload(result)["target"], "accounting/RD-001")

    def test_st_6_incompatible_target_type_names_allowed_types(self) -> None:
        graph = self.graph("accounting", [node("TASK-001", "task", status="pending")])
        result = self.run_state(
            {"accounting": graph},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "accounting/TASK-001",
        )
        problems = "\n".join(self.payload(result)["problems"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("incompatible-target", problems)
        self.assertIn("requirement-set", problems)

    def test_st_10_dependency_blocker_reports_shortest_path(self) -> None:
        graph = self.graph(
            "accounting",
            [
                node(
                    "RD-001",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "identity/RD-IAM-004"}],
                )
            ],
        )
        identity = self.graph(
            "identity",
            [node("RD-IAM-004", "requirement", status="draft")],
        )
        result = self.run_state(
            {"accounting": graph, "identity": identity},
            "readiness",
            "--gate",
            "requirements",
            "--target",
            "accounting/RD-001",
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 1)
        self.assertIn("blockers", payload)
        self.assertIn(
            ["accounting/RD-001", "identity/RD-IAM-004"],
            [problem["path"] for problem in payload["blockers"]],
        )

    def test_st_19_release_closure_uses_only_required_members(self) -> None:
        graph = self.graph(
            "_releases",
            [
                node(
                    "RELEASE-1",
                    "release",
                    required=["_releases/TASK-REQ"],
                    optional=["_releases/TASK-OPT"],
                    excluded=["_releases/TASK-OUT"],
                ),
                node("TASK-REQ", "task", status="verified"),
                node("TASK-OPT", "task", status="pending"),
                node("TASK-OUT", "task", status="pending"),
            ],
        )
        result = self.run_state(
            {"_releases": graph},
            "readiness",
            "--gate",
            "release",
            "--target",
            "_releases/RELEASE-1",
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertIn("_releases/TASK-REQ", payload["closure"])
        self.assertNotIn("_releases/TASK-OPT", payload["closure"])
        self.assertNotIn("_releases/TASK-OUT", payload["closure"])

    def test_st_36_status_reports_lifecycle_transitions_and_gate_summaries(self) -> None:
        graph = self.graph("accounting", [node("RD-001", "requirement", status="draft")])
        result = self.run_state(
            {"accounting": graph},
            "status",
            "--target",
            "accounting/RD-001",
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["target"], "accounting/RD-001")
        self.assertIn("status", payload)
        self.assertEqual(payload["status"], "draft")
        self.assertEqual(payload["lifecycle"], "requirements")
        self.assertFalse(payload["ready"])
        self.assertIn("approved", payload["valid_transitions"])
        self.assertIn("requirements", payload["gates"])
        self.assertFalse(payload["gates"]["requirements"]["ready"])
        self.assertTrue(payload["gates"]["requirements"]["blockers"])
        self.assertIn("stale_snapshots", payload)

    def test_st_9_unrelated_draft_sibling_is_excluded(self) -> None:
        graph = self.graph(
            "erp",
            [
                node("RD-001", "requirement"),
                node("RD-002", "requirement", status="draft"),
            ],
        )
        result = self.run_state(
            {"erp": graph}, "readiness", "--gate", "requirements", "--target", "erp/RD-001"
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertNotIn("erp/RD-002", payload["closure"])

    def test_st_11_downstream_consumer_does_not_block_provider(self) -> None:
        graph = self.graph(
            "erp",
            [
                node("CONTRACT-1", "contract", maturity="stable"),
                node(
                    "RD-CONSUMER",
                    "requirement",
                    status="draft",
                    edges=[{
                        "relation": "consumes-contract",
                        "target": "erp/CONTRACT-1",
                        "requiredMaturity": "stable",
                    }],
                ),
            ],
        )
        result = self.run_state(
            {"erp": graph}, "readiness", "--gate", "specifications", "--target", "erp/CONTRACT-1"
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertNotIn("erp/RD-CONSUMER", payload["closure"])

    def test_st_12_gate_profiles_select_distinct_trace_closures(self) -> None:
        graph = self.graph(
            "erp",
            [
                node(
                    "RD-001",
                    "requirement",
                    edges=[
                        {"relation": "specified-by", "target": "erp/SPEC-001"},
                        {"relation": "accepted-by", "target": "erp/AC-001"},
                    ],
                    validations=[
                        snapshot("erp/AC-001", "accepted-by", "requirements"),
                        snapshot("erp/AC-001", "accepted-by", "specifications"),
                        snapshot("erp/SPEC-001", "specified-by", "specifications"),
                    ],
                ),
                node("SPEC-001", "specification"),
                node("AC-001", "criterion"),
            ],
        )
        closures = {}
        for gate in ("requirements", "specifications"):
            result = self.run_state(
                {"erp": graph}, "readiness", "--gate", gate, "--target", "erp/RD-001"
            )
            self.assertEqual(result.returncode, 0, result.stdout)
            closures[gate] = self.payload(result)["closure"]
        self.assertNotIn("erp/SPEC-001", closures["requirements"])
        self.assertIn("erp/SPEC-001", closures["specifications"])

    def test_st_14_invalid_unrelated_graph_is_diagnostic_only(self) -> None:
        root = ROOT / "tests" / "fixtures" / "state-v2-invalid"
        result = subprocess.run(
            [
                sys.executable, str(SCRIPT), "readiness", "--root", str(root),
                "--gate", "requirements", "--target", "valid/RD-001", "--json",
            ],
            text=True, capture_output=True, check=False,
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["problems"], [])
        self.assertEqual(payload["diagnostics"][0]["feature"], "unrelated")

    def test_st_13_invalid_entered_dependency_blocks_with_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
            accounting = root / "codeops" / "features" / "accounting"
            identity = root / "codeops" / "features" / "identity"
            accounting.mkdir(parents=True)
            identity.mkdir(parents=True)
            accounting_graph = self.graph(
                "accounting",
                [node(
                    "RD-001", "requirement",
                    edges=[{"relation": "depends-on", "target": "identity/RD-001"}],
                )],
            )
            invalid_graph = {"schema": 2, "feature": "identity", "nodes": "invalid"}
            (accounting / "traceability.json").write_text(
                json.dumps(accounting_graph), encoding="utf-8"
            )
            (identity / "traceability.json").write_text(
                json.dumps(invalid_graph), encoding="utf-8"
            )
            result = subprocess.run(
                [
                    sys.executable, str(SCRIPT), "readiness", "--root", str(root),
                    "--gate", "requirements", "--target", "accounting/RD-001", "--json",
                ],
                text=True, capture_output=True, check=False,
            )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            ["accounting/RD-001", "identity/RD-001"],
            [blocker.get("path") for blocker in payload["blockers"]],
        )

    def test_st_20_release_coupled_member_enters_closure(self) -> None:
        graph = self.graph(
            "_releases",
            [
                node(
                    "RELEASE-1", "release",
                    required=["_releases/RD-A"], optional=[], excluded=[],
                ),
                node(
                    "RD-A", "requirement",
                    edges=[{"relation": "release-coupled", "target": "_releases/RD-B"}],
                    validations=[
                        snapshot("_releases/RD-B", "release-coupled", "release")
                    ],
                ),
                node("RD-B", "requirement"),
            ],
        )
        result = self.run_state(
            {"_releases": graph}, "readiness", "--gate", "release",
            "--target", "_releases/RELEASE-1",
        )
        payload = self.payload(result)
        self.assertEqual(result.returncode, 0, payload)
        self.assertIn("_releases/RD-B", payload["closure"])

    def test_st_35_specifications_gate_is_independent(self) -> None:
        graph = self.graph(
            "erp",
            [
                node(
                    "RD-001", "requirement",
                    edges=[{"relation": "specified-by", "target": "erp/SPEC-001"}],
                ),
                node("SPEC-001", "specification", status="draft"),
            ],
        )
        requirements = self.run_state(
            {"erp": graph}, "readiness", "--gate", "requirements", "--target", "erp/RD-001"
        )
        specifications = self.run_state(
            {"erp": graph}, "readiness", "--gate", "specifications", "--target", "erp/RD-001"
        )
        self.assertEqual(requirements.returncode, 0, requirements.stdout)
        self.assertEqual(specifications.returncode, 1, specifications.stdout)

    def test_st_38_repository_discovery_excludes_fixtures(self) -> None:
        repository = subprocess.run(
            [sys.executable, str(SCRIPT), "status", "--root", str(ROOT), "--json"],
            text=True, capture_output=True, check=False,
        )
        fixture = subprocess.run(
            [
                sys.executable, str(SCRIPT), "validate",
                "--root", str(ROOT / "tests" / "fixtures" / "state-v2-cross-feature"),
                "--json",
            ],
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(json.loads(repository.stdout)["graphs"], 1)
        self.assertEqual(json.loads(fixture.stdout)["graphs"], 2)

    def test_st_21_matching_dependency_snapshot_is_current(self) -> None:
        snapshot = {
            "upstream": "sample/RD-UP",
            "relation": "depends-on",
            "revision": REVISION,
            "gate": "requirements",
            "validatedAt": "2026-07-23T12:00:00Z",
        }
        graph = self.graph(
            "sample",
            [
                node(
                    "RD-DOWN",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "sample/RD-UP"}],
                    validations=[snapshot],
                ),
                node("RD-UP", "requirement"),
            ],
        )
        result = self.run_state(
            {"sample": graph}, "readiness", "--gate", "requirements",
            "--target", "sample/RD-DOWN",
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_st_22_snapshot_revision_mismatch_blocks_dependent(self) -> None:
        snapshot = {
            "upstream": "sample/RD-UP",
            "relation": "depends-on",
            "revision": "sha256:" + ("1" * 64),
            "gate": "requirements",
            "validatedAt": "2026-07-23T12:00:00Z",
        }
        graph = self.graph(
            "sample",
            [
                node(
                    "RD-DOWN",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "sample/RD-UP"}],
                    validations=[snapshot],
                ),
                node("RD-UP", "requirement"),
            ],
        )
        result = self.run_state(
            {"sample": graph}, "readiness", "--gate", "requirements",
            "--target", "sample/RD-DOWN",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("stale-snapshot", {item["code"] for item in self.payload(result)["blockers"]})

    def test_st_23_related_revision_is_not_an_invalidation_edge(self) -> None:
        graph = self.graph(
            "sample",
            [
                node(
                    "RD-DOWN",
                    "requirement",
                    edges=[{"relation": "related", "target": "sample/RD-UP"}],
                ),
                node("RD-UP", "requirement"),
            ],
        )
        result = self.run_state(
            {"sample": graph}, "readiness", "--gate", "requirements",
            "--target", "sample/RD-DOWN",
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_st_24_release_snapshot_is_gate_specific(self) -> None:
        snapshot = {
            "upstream": "sample/RD-B",
            "relation": "release-coupled",
            "revision": "sha256:" + ("1" * 64),
            "gate": "release",
            "validatedAt": "2026-07-23T12:00:00Z",
        }
        graph = self.graph(
            "sample",
            [
                node(
                    "RELEASE-1", "release",
                    required=["sample/RD-A"], optional=[], excluded=[],
                ),
                node(
                    "RD-A", "requirement",
                    edges=[{"relation": "release-coupled", "target": "sample/RD-B"}],
                    validations=[snapshot],
                ),
                node("RD-B", "requirement"),
            ],
        )
        requirements = self.run_state(
            {"sample": graph}, "readiness", "--gate", "requirements",
            "--target", "sample/RD-A",
        )
        release = self.run_state(
            {"sample": graph}, "readiness", "--gate", "release",
            "--target", "sample/RELEASE-1",
        )
        self.assertEqual(requirements.returncode, 0, requirements.stdout)
        self.assertEqual(release.returncode, 1)
        self.assertIn("stale-snapshot", {item["code"] for item in self.payload(release)["blockers"]})

    def test_missing_blocking_snapshot_is_reported(self) -> None:
        graph = self.graph(
            "erp",
            [
                node(
                    "RD-001",
                    "requirement",
                    edges=[{"relation": "depends-on", "target": "erp/RD-002"}],
                ),
                node("RD-002", "requirement"),
            ],
        )
        result = self.run_state(
            {"erp": graph}, "readiness", "--gate", "requirements",
            "--target", "erp/RD-001",
        )
        self.assertIn(
            "missing-snapshot",
            {item["code"] for item in self.payload(result)["blockers"]},
        )

    def test_snapshot_without_persisted_relationship_is_reported(self) -> None:
        graph = self.graph(
            "erp",
            [
                node(
                    "RD-001",
                    "requirement",
                    validations=[
                        snapshot("erp/RD-002", "depends-on", "requirements")
                    ],
                ),
                node("RD-002", "requirement"),
            ],
        )
        result = self.run_state(
            {"erp": graph}, "readiness", "--gate", "requirements",
            "--target", "erp/RD-001",
        )
        self.assertIn(
            "extraneous-snapshot",
            {item["code"] for item in self.payload(result)["blockers"]},
        )


if __name__ == "__main__":
    unittest.main()
