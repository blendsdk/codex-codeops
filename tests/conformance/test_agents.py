#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "install_agents.py"


class AgentInstallerTests(unittest.TestCase):
    def run_installer(self, project: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--project", str(project), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generates_valid_role_and_check_passes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            result = self.run_installer(project, "--roles", "explorer,executor")
            self.assertEqual(result.returncode, 0, result.stderr)
            explorer = project / ".codex" / "agents" / "explorer.toml"
            executor = project / ".codex" / "agents" / "executor.toml"
            self.assertIn('sandbox_mode = "read-only"', explorer.read_text())
            self.assertIn('sandbox_mode = "workspace-write"', executor.read_text())
            check = self.run_installer(project, "--roles", "explorer,executor", "--check")
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_preserves_hand_authored_agent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            target = project / ".codex" / "agents" / "explorer.toml"
            target.parent.mkdir(parents=True)
            target.write_text('name = "my-agent"\n', encoding="utf-8")
            result = self.run_installer(project, "--roles", "explorer")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), 'name = "my-agent"\n')
            self.assertIn("PRESERVE hand-authored", result.stdout)

    def test_check_detects_missing_generated_agent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = self.run_installer(Path(raw), "--roles", "security-auditor", "--check")
            self.assertEqual(result.returncode, 1)
            self.assertIn("MISSING", result.stderr)


if __name__ == "__main__":
    unittest.main()
