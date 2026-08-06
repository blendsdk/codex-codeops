#!/usr/bin/env python3
"""Specification contracts for native Windows workflow integration."""

from __future__ import annotations

from pathlib import Path
import json
import os
import re
import shutil
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]

MUTATION_OWNERS = {
    "scripts/codeops_migrate_lib/apply.py": "layout-migration",
    "scripts/codeops_roadmap_lib/rendering.py": "roadmap-write",
    "scripts/codeops_worktree_lib/commands.py": "worktree-mutation",
    "scripts/codeops_state.py": "state-transition",
    "scripts/codeops_outcomes.py": "outcome-write",
    "scripts/codeops_worktree_snapshot.py": "snapshot-write",
    "scripts/install_agents.py": "agent-install",
}

MUTATING_SKILLS = (
    "make-requirements",
    "retro-requirements",
    "make-plan",
    "preflight",
    "exec-plan",
    "upgrade-plan",
    "setup-codeops",
    "roadmap",
    "setup-routing",
    "techdocs",
    "analyze-project",
    "clean-comments",
    "git-commit",
)

INTERPRETER_SURFACES = (
    "skills/make-requirements/SKILL.md",
    "skills/make-plan/SKILL.md",
    "skills/preflight/SKILL.md",
    "skills/roadmap/SKILL.md",
    "skills/setup-routing/SKILL.md",
    "skills/upgrade-plan/SKILL.md",
    "skills/exec-plan/SKILL.md",
    "skills/exec-plan/execution-protocol.md",
    "skills/setup-codeops/SKILL.md",
    "skills/setup-codeops/migration.md",
    "references/artifacts/traceability.md",
)


class WorkflowMutationSpecification(unittest.TestCase):
    def test_st_12_every_direct_mutation_owner_has_registered_command_gate(self) -> None:
        registry = (ROOT / "scripts/codeops_windows_preflight.py").read_text(encoding="utf-8")
        for relative, entrypoint in MUTATION_OWNERS.items():
            with self.subTest(owner=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("run_mutation_preflight", text)
                self.assertIn(entrypoint, text)
                self.assertIn(f'"{entrypoint}"', registry)

    def test_st_12_every_mutating_skill_uses_shared_defense_in_depth_gate(self) -> None:
        contract = ROOT / "_shared/native-runtime.md"
        self.assertTrue(contract.is_file(), "shared native runtime contract is missing")
        contract_text = contract.read_text(encoding="utf-8") if contract.is_file() else ""
        self.assertIn("## Mutation defense in depth", contract_text)
        self.assertIn("skill-mutation", contract_text)
        for skill in MUTATING_SKILLS:
            with self.subTest(skill=skill):
                text = (ROOT / f"skills/{skill}/SKILL.md").read_text(encoding="utf-8")
                self.assertIn("## Native prerequisite gate", text)
                self.assertIn("../../_shared/native-runtime.md", text)

    def test_st_12_runtime_examples_use_certified_host_neutral_interpreter(self) -> None:
        contract = ROOT / "_shared/native-runtime.md"
        self.assertTrue(contract.is_file(), "shared native runtime contract is missing")
        contract_text = contract.read_text(encoding="utf-8") if contract.is_file() else ""
        self.assertIn("<CODEOPS_PYTHON>", contract_text)
        self.assertIn("Python 3.10", contract_text)
        self.assertIn("codeops-windows-preflight.ps1", contract_text)
        for relative in INTERPRETER_SURFACES:
            with self.subTest(surface=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"(?m)^\s*python3\s+", text))
                if "codeops_state.py" in text or "install_agents.py" in text or "codeops_worktree_snapshot.py" in text:
                    self.assertIn("<CODEOPS_PYTHON>", text)


class InstalledWorkflowSpecification(unittest.TestCase):
    def test_st_39_installed_plugin_path_with_spaces_runs_portable_surfaces(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            installed = base / "Installed Plugin & Spaces"
            shutil.copytree(ROOT / "scripts", installed / "scripts")
            shutil.copytree(ROOT / "agent-templates", installed / "agent-templates")
            project = base / "Project With Spaces"
            project.mkdir()
            evidence = base / "command evidence.json"
            commands = (
                (
                    sys.executable,
                    str(installed / "scripts/codeops_outcomes.py"),
                    "report",
                    "--root",
                    str(project),
                    "--store",
                    str(base / "outcomes with spaces.jsonl"),
                    "--json",
                ),
                (
                    sys.executable,
                    str(installed / "scripts/install_agents.py"),
                    "--project",
                    str(project),
                    "--roles",
                    "explorer",
                    "--dry-run",
                ),
                (
                    sys.executable,
                    str(installed / "scripts/codeops_verify.py"),
                    "list",
                    "--root",
                    str(ROOT),
                    "--json",
                ),
            )
            results = [
                run_command(command, cwd=project, evidence_sink=evidence)
                for command in commands
            ]
            records = json.loads(evidence.read_text(encoding="utf-8"))

        self.assertTrue(all(result.exit_code == 0 for result in results), results)
        self.assertEqual(len(records), len(commands))
        self.assertIn("Installed Plugin & Spaces", "\n".join(" ".join(item["argv"]) for item in records))
        self.assertEqual(json.loads(results[0].stdout)["events"], 0)
        self.assertIn("WOULD WRITE", results[1].stdout)
        self.assertEqual(
            json.loads(results[2].stdout)["checks"],
            ["validate", "docs", "migration", "roadmap", "compact"],
        )

    def test_st_39_captured_commands_exclude_prohibited_runtimes(self) -> None:
        forbidden = {"wsl", "wsl.exe", "bash", "bash.exe", "git-bash", "git-bash.exe"}
        command = (
            sys.executable,
            str(ROOT / "scripts/codeops_verify.py"),
            "list",
            "--root",
            str(ROOT),
        )
        from scripts.codeops_platform.subprocesses import run_command

        with tempfile.TemporaryDirectory() as raw:
            evidence = Path(raw) / "commands.json"
            result = run_command(command, cwd=ROOT, evidence_sink=evidence)
            records = json.loads(evidence.read_text(encoding="utf-8"))
        self.assertEqual(result.exit_code, 0, result.stderr)
        for record in records:
            executable = Path(record["argv"][0]).name.casefold()
            self.assertNotIn(executable, forbidden)
            self.assertFalse(any(part.casefold() in forbidden for part in record["argv"][1:]))

    def test_st_40_native_full_verification_surface_is_closed_and_shell_free(self) -> None:
        from scripts.codeops_verify import CHECKS

        self.assertEqual(
            list(CHECKS),
            ["validate", "docs", "migration", "roadmap", "compact"],
        )
        launcher = (ROOT / "scripts/codeops-verify.ps1").read_text(encoding="utf-8").casefold()
        self.assertIn("codeops_verify.py", launcher)
        self.assertNotIn("wsl.exe", launcher)
        self.assertNotIn("bash.exe", launcher)


if __name__ == "__main__":
    unittest.main()
