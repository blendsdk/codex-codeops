#!/usr/bin/env python3
"""Specification contracts for native Windows certification and support claims."""

from __future__ import annotations

from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]


class CertificationCISpecification(unittest.TestCase):
    def test_st_46_ci_has_explicit_ubuntu_and_windows_11_arm_native_jobs(self) -> None:
        workflow = ROOT / ".github/workflows/ci.yml"
        payload = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        jobs = payload["jobs"]
        ubuntu = jobs["validate-ubuntu"]
        windows = jobs["validate-windows-11-arm"]
        self.assertEqual(ubuntu["runs-on"], "ubuntu-latest")
        self.assertEqual(windows["runs-on"], "windows-11-arm")

        def python_versions(job: dict[str, object]) -> list[str]:
            return [
                str(step["with"]["python-version"])
                for step in job["steps"]
                if isinstance(step, dict)
                and str(step.get("uses", "")).startswith("actions/setup-python@")
            ]

        for job in (ubuntu, windows):
            versions = python_versions(job)
            self.assertEqual(len(versions), 1)
            self.assertGreaterEqual(tuple(map(int, re.match(r"^(\d+)\.(\d+)", versions[0]).groups())), (3, 10))

        windows_steps = "\n".join(
            str(step.get("run", "")) for step in windows["steps"] if isinstance(step, dict)
        ).casefold()
        self.assertIn("source with spaces", str(windows).casefold())
        self.assertIn("codeops-windows-preflight.ps1", windows_steps)
        self.assertIn("codeops-verify.ps1", windows_steps)
        self.assertNotRegex(windows_steps, r"(?:^|\s)(?:bash|wsl)(?:\.exe)?(?:\s|$)")
        self.assertNotIn(".sh", windows_steps)

        ubuntu_steps = "\n".join(
            str(step.get("run", "")) for step in ubuntu["steps"] if isinstance(step, dict)
        )
        for launcher in (
            "./scripts/validate-codex.sh", "./scripts/docs-check.sh",
            "./scripts/migration-check.sh", "./scripts/roadmap-sync-check.sh",
            "./scripts/compact-check.sh",
        ):
            self.assertIn(launcher, ubuntu_steps)


if __name__ == "__main__":
    unittest.main()
