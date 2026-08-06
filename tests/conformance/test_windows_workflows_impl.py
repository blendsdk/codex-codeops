#!/usr/bin/env python3
"""Implementation coverage for native Windows workflow integration."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
MUTATING_SKILLS = (
    "make-requirements", "retro-requirements", "make-plan", "preflight", "exec-plan",
    "upgrade-plan", "setup-codeops", "roadmap", "setup-routing", "techdocs",
    "analyze-project", "clean-comments", "git-commit",
)
INTERPRETER_SURFACES = (
    "skills/make-requirements/SKILL.md", "skills/make-plan/SKILL.md",
    "skills/preflight/SKILL.md", "skills/roadmap/SKILL.md",
    "skills/setup-routing/SKILL.md", "skills/upgrade-plan/SKILL.md",
    "skills/exec-plan/SKILL.md", "skills/exec-plan/execution-protocol.md",
    "skills/setup-codeops/SKILL.md", "skills/setup-codeops/migration.md",
    "references/artifacts/traceability.md",
)


class SkillSurfaceImplementationTests(unittest.TestCase):
    def test_every_mutating_skill_resolves_one_shared_native_contract(self) -> None:
        contract = (ROOT / "_shared/native-runtime.md").resolve()
        self.assertTrue(contract.is_file())
        for skill in MUTATING_SKILLS:
            path = ROOT / "skills" / skill / "SKILL.md"
            text = path.read_text(encoding="utf-8")
            match = re.search(r"\]\((\.\./\.\./_shared/native-runtime\.md)\)", text)
            self.assertIsNotNone(match, skill)
            self.assertEqual((path.parent / match.group(1)).resolve(), contract)

    def test_runtime_surfaces_have_no_executable_python3_example(self) -> None:
        for relative in INTERPRETER_SURFACES:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"(?m)^\s*python3\s+", text), relative)
            self.assertIn("<CODEOPS_PYTHON>", text, relative)


class InstalledAndCaptureImplementationTests(unittest.TestCase):
    def test_installed_path_with_spaces_executes_read_only_surfaces(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            installed = base / "Installed Plugin With Spaces"
            shutil.copytree(ROOT / "scripts", installed / "scripts")
            shutil.copytree(ROOT / "agent-templates", installed / "agent-templates")
            project = base / "Project With Spaces"
            project.mkdir()
            evidence = base / "native commands.json"
            commands = (
                (sys.executable, str(installed / "scripts/codeops_outcomes.py"), "report",
                 "--root", str(project), "--store", str(base / "empty outcomes.jsonl"), "--json"),
                (sys.executable, str(installed / "scripts/install_agents.py"), "--project",
                 str(project), "--roles", "explorer", "--dry-run"),
                (sys.executable, str(installed / "scripts/codeops_verify.py"), "list",
                 "--root", str(ROOT), "--json"),
            )
            results = [run_command(command, cwd=project, evidence_sink=evidence) for command in commands]
            records = json.loads(evidence.read_text(encoding="utf-8"))

        self.assertTrue(all(result.exit_code == 0 for result in results), results)
        self.assertEqual(len(records), 3)
        self.assertTrue(all(record["cwd"] == str(project) for record in records))

    def test_captured_commands_are_argument_arrays_without_prohibited_runtime(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with tempfile.TemporaryDirectory() as raw:
            sink = Path(raw) / "capture.json"
            result = run_command(
                (sys.executable, str(ROOT / "scripts/codeops_verify.py"), "list", "--root", str(ROOT)),
                cwd=ROOT,
                evidence_sink=sink,
            )
            records = json.loads(sink.read_text(encoding="utf-8"))
        self.assertEqual(result.exit_code, 0, result.stderr)
        forbidden = re.compile(r"(?:^|[\\/])(wsl|bash|git-bash)(?:\.exe)?$", re.IGNORECASE)
        for record in records:
            self.assertIsInstance(record["argv"], list)
            self.assertFalse(any(forbidden.search(token) for token in record["argv"]))


class MutationUtilityImplementationTests(unittest.TestCase):
    def test_outcome_emit_gates_before_atomic_write(self) -> None:
        from scripts import codeops_outcomes

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "codeops").mkdir()
            (root / "codeops/codeops.json").write_text(
                json.dumps({"metrics": {"enabled": True}}), encoding="utf-8"
            )
            store = root / "data" / "outcomes.jsonl"
            args = argparse.Namespace(
                root=str(root), store=str(store), event="task-verified", stage="verification",
                result="pass", count=1, duration_ms=None,
            )
            with patch.object(codeops_outcomes, "run_mutation_preflight", return_value=0) as gate:
                self.assertEqual(codeops_outcomes.emit(args), 0)
            payload = json.loads(store.read_text(encoding="utf-8"))
        self.assertEqual(payload["event"], "task-verified")
        self.assertEqual(gate.call_args.kwargs["entrypoint_code"], "outcome-write")
        self.assertIn(store, gate.call_args.args[1])

    def test_agent_install_gates_complete_plan_and_writes_generated_file(self) -> None:
        from scripts import install_agents

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            argv = ["install_agents.py", "--project", str(project), "--roles", "explorer"]
            with (
                patch.object(sys, "argv", argv),
                patch.object(install_agents, "run_mutation_preflight", return_value=0) as gate,
            ):
                self.assertEqual(install_agents.main(), 0)
            destination = project / ".codex/agents/explorer.toml"
            text = destination.read_text(encoding="utf-8")
        self.assertTrue(text.startswith(install_agents.MARKER))
        self.assertEqual(gate.call_args.kwargs["entrypoint_code"], "agent-install")
        self.assertIn(destination, gate.call_args.args[1])

    def test_snapshot_gates_git_object_and_temporary_index_mutations(self) -> None:
        from scripts import codeops_worktree_snapshot as snapshot

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            subprocess.run(("git", "init", "-q", str(root)), check=True)
            subprocess.run(("git", "-C", str(root), "config", "user.email", "test@example.invalid"), check=True)
            subprocess.run(("git", "-C", str(root), "config", "user.name", "CodeOps Test"), check=True)
            (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            subprocess.run(("git", "-C", str(root), "add", "tracked.txt"), check=True)
            subprocess.run(("git", "-C", str(root), "commit", "-qm", "baseline"), check=True)
            with patch.object(snapshot, "run_mutation_preflight", return_value=0) as gate:
                tree = snapshot.snapshot_worktree(root)
            index = root / ".git" / f"codeops-phase-index-{os.getpid()}"
        self.assertRegex(tree, snapshot.OBJECT_ID_RE)
        self.assertFalse(index.exists())
        self.assertEqual(gate.call_args.kwargs["entrypoint_code"], "snapshot-write")
        self.assertIn(root / ".git" / "objects", gate.call_args.args[1])


class DocumentationImplementationTests(unittest.TestCase):
    def test_windows_docs_keep_support_pending_and_publish_native_commands(self) -> None:
        combined = "\n".join(
            (ROOT / relative).read_text(encoding="utf-8")
            for relative in ("README.md", "docs/installation.md", "docs/troubleshooting.md")
        )
        self.assertIn("remains unsupported", combined)
        self.assertIn("codeops-verify.ps1", combined)
        self.assertIn("Python 3.10", combined)
        self.assertIn("WSL", combined)
        self.assertNotIn("Windows 11 is supported", combined)

    def test_native_constraints_are_present_in_migration_tutorial_and_concepts(self) -> None:
        for relative in ("docs/migration.md", "docs/tutorial.md", "docs/concepts.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            for phrase in ("Python 3.10", "WSL", "fixed local NTFS"):
                self.assertIn(phrase, text, relative)


if __name__ == "__main__":
    unittest.main()
