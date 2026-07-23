#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
VALID_FIXTURE = ROOT / "tests" / "fixtures" / "state-valid"


class SchemaOneCompatibilityTests(unittest.TestCase):
    def run_state(
        self,
        root: Path,
        command: str,
        *,
        feature: str | None = None,
        as_json: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        args = [sys.executable, str(SCRIPT), command, "--root", str(root)]
        if feature is not None:
            args.extend(["--feature", feature])
        if as_json:
            args.append("--json")
        return subprocess.run(args, text=True, capture_output=True, check=False)

    def test_st_25_ready_graph_json_contract(self) -> None:
        result = self.run_state(VALID_FIXTURE, "readiness")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ready"])
        self.assertIsNone(payload["selected_feature"])
        self.assertEqual(payload["graphs"], 1)
        self.assertEqual(payload["nodes"], 8)
        self.assertEqual(payload["problems"], [])
        self.assertEqual(payload["tasks"], {"pending": 0, "implemented": 0, "verified": 0})
        self.assertEqual(
            payload["features"],
            [{"feature": "ledger", "lifecycle": "complete", "nodes": 8, "ready": True}],
        )

    def test_feature_scoped_readiness_contract(self) -> None:
        result = self.run_state(VALID_FIXTURE, "readiness", feature="ledger")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["selected_feature"], "ledger")
        self.assertEqual(payload["problems"], [])

    def test_ready_graph_human_output_contract(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "state-valid"
            shutil.copytree(VALID_FIXTURE, root)
            result = self.run_state(root, "readiness", feature="ledger", as_json=False)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                "CodeOps graphs: 1 | nodes: 8",
                "Readiness scope: ledger",
                "Tasks: 0 pending | 0 implemented | 0 verified",
                "Feature ledger: complete | ready",
                "READY",
            ],
        )

    def test_status_observes_valid_but_not_ready_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feature = root / "codeops" / "features" / "draft"
            feature.mkdir(parents=True)
            (feature / "requirement.md").write_text("# Draft\n", encoding="utf-8")
            graph = {
                "schema": 1,
                "feature": "draft",
                "nodes": [
                    {
                        "id": "RD-001",
                        "type": "requirement",
                        "title": "Draft requirement",
                        "status": "draft",
                        "path": "requirement.md",
                        "links": ["SPEC-001"],
                    },
                    {
                        "id": "SPEC-001",
                        "type": "specification",
                        "title": "Draft specification",
                        "status": "draft",
                        "path": "requirement.md",
                        "links": ["RD-001"],
                    },
                ],
            }
            (feature / "traceability.json").write_text(
                json.dumps(graph),
                encoding="utf-8",
            )

            result = self.run_state(root, "status", feature="draft")
            payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["selected_feature"], "draft")
        self.assertIn("requirement RD-001 is not approved", "\n".join(payload["problems"]))
        self.assertIn("specification SPEC-001 is not approved", "\n".join(payload["problems"]))

    def test_unknown_feature_fails_without_fallback(self) -> None:
        result = self.run_state(VALID_FIXTURE, "readiness", feature="missing")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertFalse(payload["ready"])
        self.assertIsNone(payload["selected_feature"])
        self.assertIn("feature not found: missing", "\n".join(payload["problems"]))

    def test_validate_rejects_feature_selector(self) -> None:
        result = self.run_state(VALID_FIXTURE, "validate", feature="ledger")
        payload = json.loads(result.stdout)

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "--feature is valid only for readiness or status",
            "\n".join(payload["problems"]),
        )


if __name__ == "__main__":
    unittest.main()
