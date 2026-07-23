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


if __name__ == "__main__":
    unittest.main()
