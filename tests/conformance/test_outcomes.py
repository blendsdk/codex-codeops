#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_outcomes.py"


class OutcomeTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True, check=False)

    def test_disabled_project_records_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            store = project / "events.jsonl"
            result = self.run_tool("emit", "--root", str(project), "--store", str(store), "--event", "task-verified", "--stage", "execution", "--result", "pass")
            self.assertEqual(result.returncode, 0)
            self.assertFalse(store.exists())

    def test_enabled_project_records_only_enums_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            (project / "codeops").mkdir()
            (project / "codeops" / "codeops.json").write_text('{"metrics":{"enabled":true}}', encoding="utf-8")
            store = project / "events.jsonl"
            result = self.run_tool("emit", "--root", str(project), "--store", str(store), "--event", "verification-run", "--stage", "verification", "--result", "pass", "--count", "3")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(store.read_text(encoding="utf-8"))
            self.assertEqual(payload["count"], 3)
            self.assertEqual(set(payload), {"schema", "timestamp", "project", "event", "stage", "result", "count"})
            report = self.run_tool("report", "--root", str(project), "--store", str(store), "--json")
            self.assertEqual(json.loads(report.stdout)["totals"]["verification-run"], 3)


if __name__ == "__main__":
    unittest.main()
