#!/usr/bin/env python3
"""Specification contracts for native Windows workflow integration."""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
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
    "_shared/quality-profile.md",
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

    def test_native_full_verification_surface_is_closed_and_shell_free(self) -> None:
        from scripts.codeops_verify import CHECKS

        self.assertEqual(
            list(CHECKS),
            ["validate", "docs", "migration", "roadmap", "compact"],
        )
        launcher = (ROOT / "scripts/codeops-verify.ps1").read_text(encoding="utf-8").casefold()
        self.assertIn("codeops_verify.py", launcher)
        self.assertNotIn("wsl.exe", launcher)
        self.assertNotIn("bash.exe", launcher)

    def test_st_40_spaces_path_runs_sequential_native_lifecycle_with_final_validation(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw) / "Native Lifecycle With Spaces"
            base.mkdir()
            installed = base / "Installed Plugin With Spaces"
            shutil.copytree(ROOT / "scripts", installed / "scripts")
            shutil.copytree(ROOT / "agent-templates", installed / "agent-templates")
            shutil.copytree(ROOT / ".codex-plugin", installed / ".codex-plugin")
            shutil.copytree(ROOT / "hooks", installed / "hooks")
            plugin_data = base / "Plugin Data"
            plugin_data.mkdir()
            project = base / "Lifecycle Project"
            feature = project / "codeops/features/sample"
            feature.mkdir(parents=True)
            artifact = b"# Artifact\n"
            (project / "artifact.md").write_bytes(artifact)
            revision = "sha256:" + hashlib.sha256(artifact).hexdigest()

            def node(
                identity: str,
                kind: str,
                status: str,
                edges: list[dict[str, str]] | None = None,
                **extra: object,
            ) -> dict[str, object]:
                value: dict[str, object] = {
                    "id": identity, "type": kind, "title": identity, "status": status,
                    "semanticSources": [{
                        "path": "artifact.md", "selector": {"kind": "whole-file"},
                        "normalization": "utf8-lf-trim-trailing-v1", "digest": "sha256",
                    }],
                    "revision": revision, "edges": edges or [], "validations": [],
                }
                value.update(extra)
                return value

            graph = {
                "schema": 2, "feature": "sample", "nodes": [
                    node("RD-001", "requirement", "approved"),
                    node(
                        "PLAN-001", "plan", "approved",
                        [
                            {"relation": "depends-on", "target": "sample/SPEC-001"},
                            {"relation": "implemented-by", "target": "sample/TASK-001"},
                        ],
                        evidence=["commit:baseline"],
                        validations=[
                            {"upstream": "sample/SPEC-001", "relation": "depends-on", "revision": revision, "gate": gate, "validatedAt": "2026-08-07T00:00:00Z"}
                            for gate in ("plan", "execution")
                        ] + [{
                            "upstream": "sample/TASK-001", "relation": "implemented-by", "revision": revision,
                            "gate": "execution", "validatedAt": "2026-08-07T00:00:00Z",
                        }],
                    ),
                    node("TASK-001", "task", "pending"),
                    node(
                        "SPEC-001", "specification", "approved",
                        [{"relation": "accepted-by", "target": "sample/AC-001"}],
                        validations=[
                            {"upstream": "sample/AC-001", "relation": "accepted-by", "revision": revision, "gate": gate, "validatedAt": "2026-08-07T00:00:00Z"}
                            for gate in ("plan", "execution")
                        ],
                    ),
                    node(
                        "AC-001", "criterion", "approved",
                        [{"relation": "tested-by", "target": "sample/ST-001"}],
                    ),
                    node("ST-001", "test", "red-confirmed"),
                ],
            }
            graph_path = feature / "traceability.json"
            graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
            (project / "codeops/.codeops.yml").write_text("codeopsLayout: nested\nschema: 1\n", encoding="utf-8")
            (project / "codeops/00-roadmap.md").write_text(
                "# Portfolio Roadmap\n\n"
                "> **Features**: 0 / 1 done\n"
                "> **Last Updated**: 1999-01-01\n\n"
                "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
                "|---------|---------|---------------|----------|--------|--------------|\n"
                "| sample | [→](features/sample/00-roadmap.md) | execution | 0/1 RDs | ⬜ | 1999-01-01 |\n",
                encoding="utf-8",
            )
            (feature / "00-roadmap.md").write_text(
                "# Feature Roadmap\n\n"
                "> **Progress**: 0 / 1 (0%)\n"
                "> **Last Updated**: 1999-01-01\n\n"
                "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
                "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
                "| RD-001 | Requirement | — | PLAN-001 | Done | done | 1999-01-01 | — |\n",
                encoding="utf-8",
            )
            evidence = base / "commands.json"
            environment = {
                **os.environ,
                "CODEOPS_COMMAND_EVIDENCE": str(evidence),
                "PLUGIN_ROOT": str(installed),
                "PLUGIN_DATA": str(plugin_data),
            }
            state = installed / "scripts/codeops_state.py"
            lifecycle_commands = (
                (sys.executable, str(state), "readiness", "--root", str(project), "--gate", "requirements", "--target", "sample/RD-001", "--json"),
                (sys.executable, str(state), "readiness", "--root", str(project), "--gate", "plan", "--target", "sample/PLAN-001", "--json"),
                (sys.executable, str(state), "readiness", "--root", str(project), "--gate", "execution", "--target", "sample/PLAN-001", "--json"),
            )
            results = [run_command(command, cwd=project, environment=environment) for command in lifecycle_commands]

            request = project / "transition.json"
            request.write_text(json.dumps({
                "schema": 1, "operationId": "spaces-lifecycle", "target": "sample/TASK-001",
                "expected": {"status": "pending", "revision": revision},
                "requested": {"status": "implemented"}, "gate": "plan",
                "sourceUpdates": [], "validationAdditions": [], "validationRemovals": [],
                "staleReason": None, "evidence": {},
            }), encoding="utf-8")
            transition_run = run_command(
                (sys.executable, str(state), "transition", "--root", str(project),
                 "--request", str(request), "--json"),
                cwd=project,
                environment=environment,
            )
            roadmap_run = run_command(
                (sys.executable, str(installed / "scripts/codeops_roadmap.py"), "sync",
                 "--root", str(project), "--write", "--date", "2026-08-07", "--json"),
                cwd=project,
                environment=environment,
            )
            roadmap_check = run_command(
                (sys.executable, str(installed / "scripts/codeops_roadmap.py"), "sync",
                 "--root", str(project), "--check", "--date", "2026-08-07", "--json"),
                cwd=project,
                environment=environment,
            )

            migration = base / "Migration Project"
            (migration / "requirements").mkdir(parents=True)
            (migration / "requirements/RD-001.md").write_text("# Requirement\n", encoding="utf-8")
            (migration / "plans/sample").mkdir(parents=True)
            (migration / "plans/sample/99-execution-plan.md").write_text("# Plan\n", encoding="utf-8")
            subprocess.run(("git", "init", "-q", str(migration)), check=True)
            subprocess.run(("git", "-C", str(migration), "config", "user.email", "test@example.invalid"), check=True)
            subprocess.run(("git", "-C", str(migration), "config", "user.name", "CodeOps Test"), check=True)
            subprocess.run(("git", "-C", str(migration), "add", "."), check=True)
            subprocess.run(("git", "-C", str(migration), "commit", "-qm", "baseline"), check=True)
            migration_run = run_command(
                (sys.executable, str(installed / "scripts/codeops_migrate.py"), "apply",
                 "--root", str(migration), "--json"),
                cwd=migration,
                environment=environment,
            )

            validation = run_command(
                (sys.executable, str(state), "validate", "--root", str(project), "--json"),
                cwd=project,
                environment=environment,
            )
            records = json.loads(evidence.read_text(encoding="utf-8"))
            migrated_marker = (migration / "codeops/.codeops.yml").is_file()
            feature_roadmap = (feature / "00-roadmap.md").read_text(encoding="utf-8")
            portfolio_roadmap = (project / "codeops/00-roadmap.md").read_text(encoding="utf-8")

        self.assertTrue(all(result.exit_code == 0 for result in results), results)
        self.assertEqual(transition_run.exit_code, 0, transition_run.stderr)
        self.assertEqual(json.loads(transition_run.stdout)["result"], "committed")
        self.assertEqual(roadmap_run.exit_code, 0, roadmap_run.stderr)
        self.assertNotIn("DRIFT", roadmap_run.stdout + roadmap_run.stderr)
        self.assertEqual(roadmap_check.exit_code, 0, roadmap_check.stderr)
        self.assertEqual(json.loads(roadmap_check.stdout)["drift"], [])
        self.assertIn("> **Progress**: 1 / 1 (100%)", feature_roadmap)
        self.assertIn("> **Last Updated**: 2026-08-07", feature_roadmap)
        self.assertIn("> **Features**: 1 / 1 done", portfolio_roadmap)
        self.assertEqual(migration_run.exit_code, 0, migration_run.stderr)
        self.assertEqual(validation.exit_code, 0, validation.stderr)
        self.assertTrue(migrated_marker)
        forbidden = {"wsl", "wsl.exe", "bash", "bash.exe", "git-bash", "git-bash.exe"}
        self.assertTrue(any("readiness" in record["argv"] for record in records))
        self.assertTrue(any("mv" in record["argv"] for record in records))
        self.assertTrue(any("validate" in record["argv"] for record in records))
        self.assertFalse(any(Path(token).name.casefold() in forbidden for record in records for token in record["argv"]))


if __name__ == "__main__":
    unittest.main()
