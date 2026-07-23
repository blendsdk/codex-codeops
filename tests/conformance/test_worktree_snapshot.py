#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_worktree_snapshot.py"


class WorktreeSnapshotTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout

    def test_diff_includes_uncommitted_and_untracked_phase_changes_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.git(root, "init", "-q")
            self.git(root, "config", "user.name", "CodeOps Test")
            self.git(root, "config", "user.email", "codeops@example.invalid")
            tracked = root / "tracked.txt"
            tracked.write_text("committed\n", encoding="utf-8")
            self.git(root, "add", "tracked.txt")
            self.git(root, "commit", "-qm", "initial")

            tracked.write_text("pre-phase\n", encoding="utf-8")
            snapshot = subprocess.run(
                [sys.executable, str(SCRIPT), "snapshot", "--root", str(root)],
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()

            tracked.write_text("phase-change\n", encoding="utf-8")
            (root / "created.txt").write_text("new phase file\n", encoding="utf-8")
            phase_diff = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "diff",
                    "--root",
                    str(root),
                    "--baseline",
                    snapshot,
                ],
                text=True,
                capture_output=True,
                check=True,
            ).stdout

            self.assertIn("-pre-phase", phase_diff)
            self.assertIn("+phase-change", phase_diff)
            self.assertIn("created.txt", phase_diff)
            self.assertNotIn("-committed", phase_diff)
            self.assertEqual(
                self.git(root, "status", "--short").splitlines(),
                [" M tracked.txt", "?? created.txt"],
            )

    def test_diff_rejects_invalid_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "diff",
                    "--root",
                    raw,
                    "--baseline",
                    "../HEAD",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("baseline must be a full Git object identifier", result.stdout)


if __name__ == "__main__":
    unittest.main()
