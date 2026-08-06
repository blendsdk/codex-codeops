#!/usr/bin/env python3
"""Specification contracts for native Windows workflow integration."""

from __future__ import annotations

from pathlib import Path
import re
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


if __name__ == "__main__":
    unittest.main()
