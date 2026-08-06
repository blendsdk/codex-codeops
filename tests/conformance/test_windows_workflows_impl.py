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
    "_shared/quality-profile.md",
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

    def test_git_commit_gate_uses_linked_worktree_metadata_boundary(self) -> None:
        text = (ROOT / "skills/git-commit/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "primary worktree's parent", "--git-common-dir", "index.lock", "objects", "refs",
            "logs", "COMMIT_EDITMSG", "before `git add`", "before `git commit`",
        ):
            self.assertIn(required, text)


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

    def test_inherited_capture_records_nested_git_commands_and_default_leaves_no_trace(self) -> None:
        from scripts import codeops_worktree_snapshot as snapshot

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            root = base / "Repository With Spaces"
            subprocess.run(("git", "init", "-q", str(root)), check=True)
            subprocess.run(("git", "-C", str(root), "config", "user.email", "test@example.invalid"), check=True)
            subprocess.run(("git", "-C", str(root), "config", "user.name", "CodeOps Test"), check=True)
            (root / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            subprocess.run(("git", "-C", str(root), "add", "tracked.txt"), check=True)
            subprocess.run(("git", "-C", str(root), "commit", "-qm", "baseline"), check=True)
            sink = base / "nested commands.json"
            with (
                patch.dict(os.environ, {"CODEOPS_COMMAND_EVIDENCE": str(sink)}),
                patch.object(snapshot, "run_mutation_preflight", return_value=0),
            ):
                snapshot.snapshot_worktree(root)
            records = json.loads(sink.read_text(encoding="utf-8"))
            commands = [record["argv"] for record in records]
            no_trace = base / "ordinary-run.json"
            with (
                patch.dict(os.environ, {}, clear=False),
                patch.object(snapshot, "run_mutation_preflight", return_value=0),
            ):
                os.environ.pop("CODEOPS_COMMAND_EVIDENCE", None)
                snapshot.snapshot_worktree(root)
        self.assertTrue(any("worktree" in command and "list" in command for command in commands))
        self.assertTrue(any("write-tree" in command for command in commands))
        self.assertFalse(no_trace.exists())


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

    def test_concurrent_outcome_emitters_do_not_lose_events(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "codeops").mkdir()
            (root / "codeops/codeops.json").write_text(
                json.dumps({"metrics": {"enabled": True}}), encoding="utf-8"
            )
            store = root / "outcomes.jsonl"
            worker = (
                "from pathlib import Path; import argparse; "
                "from scripts import codeops_outcomes as m; "
                "m.run_mutation_preflight=lambda *a, **k: 0; "
                "a=argparse.Namespace(root=r'%s',store=r'%s',event='task-verified',"
                "stage='verification',result='pass',count=1,duration_ms=None); "
                "raise SystemExit(m.emit(a))"
            ) % (root, store)
            processes = [
                subprocess.Popen((sys.executable, "-c", worker), cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
                for _ in range(8)
            ]
            results = [process.communicate(timeout=30) + (process.returncode,) for process in processes]
            lines = store.read_text(encoding="utf-8").splitlines()
        self.assertTrue(all(code == 0 for _, _, code in results), results)
        self.assertEqual(len(lines), 8)
        self.assertTrue(all(json.loads(line)["event"] == "task-verified" for line in lines))

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

    def test_multi_role_agent_failure_rolls_back_the_complete_set(self) -> None:
        from scripts import install_agents

        real_write = install_agents.atomic_write_bytes
        failed = False

        def fail_second_destination(path: Path, data: bytes, **kwargs: object) -> None:
            nonlocal failed
            if path.name == "design-challenger.toml" and install_agents.TRANSACTION_DIRECTORY not in path.parts and not failed:
                failed = True
                raise OSError("injected later write failure")
            real_write(path, data, **kwargs)

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            argv = [
                "install_agents.py", "--project", str(project),
                "--roles", "explorer,design-challenger",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(install_agents, "run_mutation_preflight", return_value=0),
                patch.object(install_agents, "atomic_write_bytes", side_effect=fail_second_destination),
            ):
                self.assertEqual(install_agents.main(), 1)
            target = project / ".codex/agents"
            state = target / install_agents.TRANSACTION_DIRECTORY
            remaining = list(target.glob("*.toml"))
        self.assertTrue(failed)
        self.assertEqual(remaining, [])
        self.assertFalse(state.exists())

    def test_agent_install_recovers_interrupted_hash_bound_transaction_on_restart(self) -> None:
        from scripts import install_agents

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            target = project / ".codex/agents"
            state = target / install_agents.TRANSACTION_DIRECTORY
            state.mkdir(parents=True)
            entries: list[dict[str, object]] = []
            for role in ("explorer", "design-challenger"):
                after = install_agents.render(
                    role, ROOT / "agent-templates" / install_agents.ROLE_SOURCES[role]
                ).encode("utf-8")
                (state / f"{role}.after").write_bytes(after)
                entries.append({
                    "role": role, "existed": False, "beforeHash": None,
                    "afterHash": install_agents._digest(after),
                })
            (target / "explorer.toml").write_bytes((state / "explorer.after").read_bytes())
            (state / "active.json").write_text(
                json.dumps({"schema": 1, "entries": entries}) + "\n", encoding="utf-8"
            )
            argv = [
                "install_agents.py", "--project", str(project),
                "--roles", "explorer,design-challenger",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(install_agents, "run_mutation_preflight", return_value=0),
            ):
                self.assertEqual(install_agents.main(), 0)
            installed = sorted(path.name for path in target.glob("*.toml"))
        self.assertEqual(installed, ["design-challenger.toml", "explorer.toml"])
        self.assertFalse(state.exists())

    def test_duplicate_agent_roles_are_deduplicated_before_transaction_planning(self) -> None:
        from scripts import install_agents

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            argv = [
                "install_agents.py", "--project", str(project),
                "--roles", "explorer,explorer",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(install_agents, "run_mutation_preflight", return_value=0),
            ):
                self.assertEqual(install_agents.main(), 0)
            installed = list((project / ".codex/agents").glob("*.toml"))
            state = project / ".codex/agents" / install_agents.TRANSACTION_DIRECTORY
        self.assertEqual([path.name for path in installed], ["explorer.toml"])
        self.assertFalse(state.exists())

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
            lock = Path(f"{index}.lock")
            self.assertFalse(index.exists())
            self.assertFalse(lock.exists())
        self.assertRegex(tree, snapshot.OBJECT_ID_RE)
        self.assertEqual(gate.call_args.kwargs["entrypoint_code"], "snapshot-write")
        self.assertIn(root / ".git" / "objects", gate.call_args.args[1])
        self.assertIn(lock, gate.call_args.args[1])

    def test_snapshot_from_linked_worktree_uses_common_sibling_boundary(self) -> None:
        from scripts import codeops_worktree_snapshot as snapshot

        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            main = base / "Main Repository"
            linked = base / "Linked Worktree"
            subprocess.run(("git", "init", "-q", str(main)), check=True)
            subprocess.run(("git", "-C", str(main), "config", "user.email", "test@example.invalid"), check=True)
            subprocess.run(("git", "-C", str(main), "config", "user.name", "CodeOps Test"), check=True)
            (main / "tracked.txt").write_text("baseline\n", encoding="utf-8")
            subprocess.run(("git", "-C", str(main), "add", "tracked.txt"), check=True)
            subprocess.run(("git", "-C", str(main), "commit", "-qm", "baseline"), check=True)
            subprocess.run(("git", "-C", str(main), "worktree", "add", "-qb", "linked-test", str(linked)), check=True)
            with patch.object(snapshot, "run_mutation_preflight", return_value=0) as gate:
                tree = snapshot.snapshot_worktree(linked)
            targets = gate.call_args.args[1]
        self.assertRegex(tree, snapshot.OBJECT_ID_RE)
        self.assertEqual(gate.call_args.args[0], base.resolve())
        self.assertIn(main / ".git" / "objects", targets)
        self.assertTrue(any(path.name.endswith(".lock") for path in targets))


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
