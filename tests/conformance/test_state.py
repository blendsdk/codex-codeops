#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
FIXTURES = ROOT / "tests" / "fixtures"


class StateConformanceTests(unittest.TestCase):
    def run_state(self, fixture: str, command: str = "readiness") -> tuple[int, dict]:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), command, "--root", str(FIXTURES / fixture), "--json"],
            text=True,
            capture_output=True,
            check=False,
        )
        return result.returncode, json.loads(result.stdout)

    def test_complete_graph_is_ready(self) -> None:
        code, payload = self.run_state("state-valid")
        self.assertEqual(code, 0, payload)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["nodes"], 8)
        self.assertEqual(payload["problems"], [])
        self.assertEqual(payload["features"][0]["lifecycle"], "complete")

    def test_material_ambiguity_and_broken_link_block_readiness(self) -> None:
        code, payload = self.run_state("state-invalid")
        self.assertEqual(code, 1)
        self.assertFalse(payload["ready"])
        joined = "\n".join(payload["problems"])
        self.assertIn("links to missing node SPEC-MISSING", joined)
        self.assertIn("material ambiguity AR-001 is open", joined)
        self.assertIn("requirement RD-001 is not approved", joined)

    def test_invalid_strict_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codeops = root / "codeops"
            codeops.mkdir()
            (codeops / "codeops.json").write_text(
                '{"schema":1,"mode":"strict","artifacts":{"layout":"nested","root":"codeops"},"quality":{"independentReview":false},"metrics":{"enabled":false}}',
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", "--root", str(root), "--json"],
                text=True,
                capture_output=True,
                check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertIn("strict mode cannot disable independent review", "\n".join(payload["problems"]))

    def test_reopened_ambiguity_invalidates_approved_downstream_work(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feature = root / "codeops/features/example"
            feature.mkdir(parents=True)
            (feature / "artifact.md").write_text("# Evidence\n", encoding="utf-8")
            nodes = [
                {"id": "AR-001", "type": "ambiguity", "title": "Reopened", "status": "open", "path": "artifact.md", "links": ["RD-001"], "risk": "critical"},
                {"id": "RD-001", "type": "requirement", "title": "Affected", "status": "approved", "path": "artifact.md", "links": ["SPEC-001"]},
                {"id": "SPEC-001", "type": "specification", "title": "Affected spec", "status": "approved", "path": "artifact.md", "links": ["RD-001", "TASK-001"]},
                {"id": "TASK-001", "type": "task", "title": "Affected task", "status": "verified", "path": "artifact.md", "links": ["SPEC-001"]},
            ]
            (feature / "traceability.json").write_text(
                json.dumps({"schema": 1, "feature": "example", "updated": "2026-07-23", "nodes": nodes}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "readiness", "--root", str(root), "--json"],
                text=True, capture_output=True, check=False,
            )
            payload = json.loads(result.stdout)
            joined = "\n".join(payload["problems"])
            self.assertEqual(result.returncode, 1)
            self.assertIn("RD-001 must be marked stale", joined)
            self.assertIn("SPEC-001 must be marked stale", joined)
            self.assertIn("TASK-001 must be marked stale", joined)

    def test_unknown_status_cannot_produce_false_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            feature = root / "codeops/features/example"
            feature.mkdir(parents=True)
            (feature / "artifact.md").write_text("# Evidence\n", encoding="utf-8")
            nodes = [
                {"id": "RD-001", "type": "requirement", "title": "Bad state", "status": "finished-ish", "path": "artifact.md", "links": ["SPEC-001"]},
                {"id": "SPEC-001", "type": "specification", "title": "Spec", "status": "approved", "path": "artifact.md", "links": ["RD-001"]},
            ]
            (feature / "traceability.json").write_text(
                json.dumps({"schema": 1, "feature": "example", "nodes": nodes}), encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "readiness", "--root", str(root), "--json"],
                text=True, capture_output=True, check=False,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertIn("finished-ish", "\n".join(payload["problems"]))


if __name__ == "__main__":
    unittest.main()
