"""Implementation and hostile-boundary tests for the portable control layer."""

from __future__ import annotations

import json
import ast
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import os
import shutil


ROOT = Path(__file__).resolve().parents[2]
MIGRATE = ROOT / "scripts" / "codeops_migrate.py"


class PortableParserAndProcessTests(unittest.TestCase):
    def test_unknown_option_exits_two_without_creating_layout(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = subprocess.run(
                [sys.executable, str(MIGRATE), "preview", "--root", str(root), "--unknown"],
                text=True,
                capture_output=True,
                check=False,
                shell=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("unrecognized arguments", result.stderr)
            self.assertFalse((root / "codeops").exists())

    def test_subprocess_adapter_keeps_hostile_argument_as_data(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        hostile = "topic & whoami | $(touch nope)"
        completed = SimpleNamespace(returncode=7, stdout="out", stderr="err")
        with mock.patch("subprocess.run", return_value=completed) as invoked:
            result = run_command(("git", "branch", hostile), cwd=ROOT)

        self.assertEqual(result.exit_code, 7)
        arguments, keywords = invoked.call_args
        self.assertEqual(arguments[0], ["git", "branch", hostile])
        self.assertIs(keywords["shell"], False)
        self.assertEqual(keywords["cwd"], ROOT)

    def test_subprocess_adapter_rejects_nul_before_execution(self) -> None:
        from scripts.codeops_platform.subprocesses import run_command

        with mock.patch("subprocess.run") as invoked:
            with self.assertRaisesRegex(ValueError, "without NUL"):
                run_command(("git", "bad\0argument"), cwd=ROOT)
        invoked.assert_not_called()

    def test_worktree_human_list_retains_native_git_output(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project with spaces"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / ".fixture").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            expected = subprocess.run(
                ["git", "-C", str(project), "worktree", "list"],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
                shell=False,
            )
            actual = subprocess.run(
                [sys.executable, str(ROOT / "scripts/codeops_worktree.py"), "list", "--root", str(project)],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
                shell=False,
            )
        self.assertEqual(actual.returncode, 0, actual.stderr)
        self.assertEqual(actual.stdout, expected.stdout)


class PortableContainmentAndFailureTests(unittest.TestCase):
    def test_worktree_path_must_be_distinct_sibling(self) -> None:
        from scripts.codeops_worktree_lib.model import contained_worktree_path

        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw)
            main = parent / "project"
            main.mkdir()
            self.assertEqual(
                contained_worktree_path(main, parent / "project-topic"),
                (parent / "project-topic").resolve(),
            )
            for escaped in (main, main / "nested", parent.parent / "escaped"):
                with self.subTest(path=escaped):
                    with self.assertRaises(ValueError):
                        contained_worktree_path(main, escaped)

    def test_migration_git_failure_rolls_back_and_never_writes_marker(self) -> None:
        from scripts.codeops_migrate_lib.apply import apply_preview
        from scripts.codeops_migrate_lib.model import MigrationPreview, Move

        preview = MigrationPreview(
            "feature",
            "test",
            (
                Move("requirements", "codeops/features/feature/requirements"),
                Move("plans/feature", "codeops/features/feature/plans/feature"),
            ),
            (),
        )
        git_results = iter(
            (
                (0, "ROOT", ""),
                (0, "", ""),
                (0, "", ""),
                (1, "", "simulated git mv failure"),
                (0, "", ""),
            )
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()

            def fake_git(_root: Path, *arguments: str) -> tuple[int, str, str]:
                code, stdout, stderr = next(git_results)
                return code, str(root) if arguments[:2] == ("rev-parse", "--show-toplevel") else stdout, stderr

            with mock.patch("scripts.codeops_migrate_lib.apply._git", side_effect=fake_git), mock.patch(
                "scripts.codeops_migrate_lib.apply.run_mutation_preflight", return_value=0
            ):
                code, payload = apply_preview(root, preview)

            self.assertEqual(code, 1)
            self.assertEqual(payload["result"], "refused")
            self.assertIn("simulated git mv failure", payload["error"])
            self.assertFalse((root / "codeops" / ".codeops.yml").exists())

    def test_migration_post_marker_failure_removes_false_commit(self) -> None:
        from scripts.codeops_migrate_lib import apply as migration_apply
        from scripts.codeops_migrate_lib.model import build_preview
        from scripts.codeops_state_lib.filesystem import atomic_write_bytes as real_atomic_write

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as plugin_data:
            project = Path(raw) / "billing-platform"
            shutil.copytree(ROOT / "scripts/fixtures/flat-repo", project)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )

            def fail_after_marker(path: Path, data: bytes, *, ops=None) -> None:
                real_atomic_write(path, data, ops=ops)
                if path.name == ".codeops.yml":
                    raise OSError("simulated post-replace interruption")

            with mock.patch.dict(os.environ, {"PLUGIN_ROOT": str(ROOT), "PLUGIN_DATA": plugin_data}), mock.patch(
                "scripts.codeops_migrate_lib.apply.atomic_write_bytes",
                side_effect=fail_after_marker,
            ):
                code, payload = migration_apply.apply_preview(project, build_preview(project))

            self.assertEqual(code, 1)
            self.assertEqual(payload["result"], "refused")
            self.assertTrue((project / "requirements").is_dir())
            self.assertFalse((project / "codeops/.codeops.yml").exists())
            self.assertFalse((project / "codeops/codeops.json").exists())

    def test_migration_refuses_preexisting_generated_destination(self) -> None:
        from scripts.codeops_migrate_lib.apply import apply_preview
        from scripts.codeops_migrate_lib.model import build_preview

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "billing-platform"
            shutil.copytree(ROOT / "scripts/fixtures/flat-repo", project)
            (project / "codeops").mkdir()
            original = b'{"preserve": true}\n'
            (project / "codeops/codeops.json").write_bytes(original)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            code, payload = apply_preview(project, build_preview(project))
            self.assertEqual(code, 1)
            self.assertIn("destination already exists", payload["error"])
            self.assertEqual((project / "codeops/codeops.json").read_bytes(), original)

    def test_migration_refuses_malformed_false_marker(self) -> None:
        from scripts.codeops_migrate_lib.model import build_preview

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "codeops").mkdir()
            (root / "codeops/.codeops.yml").write_text("codeopsLayout: nested\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "marker is malformed"):
                build_preview(root)

    def test_migration_cleanup_failure_still_restores_git_moves(self) -> None:
        from scripts.codeops_migrate_lib import apply as migration_apply
        from scripts.codeops_migrate_lib.model import build_preview
        from scripts.codeops_state_lib.filesystem import atomic_write_bytes as real_atomic_write

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as plugin_data:
            project = Path(raw) / "billing-platform"
            shutil.copytree(ROOT / "scripts/fixtures/flat-repo", project)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            original_unlink = Path.unlink

            def fail_after_marker(path: Path, data: bytes, *, ops=None) -> None:
                real_atomic_write(path, data, ops=ops)
                if path.name == ".codeops.yml":
                    raise OSError("simulated post-marker failure")

            def fail_config_cleanup(path: Path, *args, **kwargs):
                if path == project / "codeops/codeops.json":
                    raise PermissionError("simulated cleanup denial")
                return original_unlink(path, *args, **kwargs)

            with mock.patch.dict(os.environ, {"PLUGIN_ROOT": str(ROOT), "PLUGIN_DATA": plugin_data}), mock.patch(
                "scripts.codeops_migrate_lib.apply.atomic_write_bytes",
                side_effect=fail_after_marker,
            ), mock.patch.object(Path, "unlink", autospec=True, side_effect=fail_config_cleanup):
                code, payload = migration_apply.apply_preview(project, build_preview(project))
            self.assertEqual(code, 2)
            self.assertEqual(payload["result"], "recovery-required")
            self.assertTrue((project / "requirements").is_dir())

    def test_roadmap_multi_file_failure_rolls_back_complete_set(self) -> None:
        from scripts.codeops_roadmap_lib import rendering
        from scripts.codeops_state_lib.filesystem import atomic_write_bytes as real_atomic_write

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            first = root / "plans/00-roadmap.md"
            second = root / "plans/_archive/two/00-roadmap.md"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            first.write_bytes(b"one-before\n")
            second.write_bytes(b"two-before\n")
            failed = False

            def fail_second_target(path: Path, data: bytes, *, ops=None) -> None:
                nonlocal failed
                if path == second and data == b"two-after\n" and not failed:
                    failed = True
                    raise OSError("simulated second publish failure")
                real_atomic_write(path, data, ops=ops)

            with mock.patch("scripts.codeops_roadmap_lib.rendering.run_mutation_preflight", return_value=0), mock.patch(
                "scripts.codeops_roadmap_lib.rendering.atomic_write_bytes",
                side_effect=fail_second_target,
            ):
                code = rendering.write_rendered(
                    root,
                    {first: b"one-after\n", second: b"two-after\n"},
                )

            self.assertEqual(code, 1)
            self.assertEqual(first.read_bytes(), b"one-before\n")
            self.assertEqual(second.read_bytes(), b"two-before\n")
            self.assertFalse((root / ".codeops-roadmap-transaction").exists())

    def test_roadmap_crash_recovery_precedes_recomputation(self) -> None:
        from scripts.codeops_roadmap_lib import rendering

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            first = root / "plans/00-roadmap.md"
            second = root / "plans/_archive/two/00-roadmap.md"
            first.parent.mkdir(parents=True)
            second.parent.mkdir(parents=True)
            before = (b"first-before\n", b"second-before\n")
            after = (b"first-after\n", b"second-after\n")
            first.write_bytes(after[0])
            second.write_bytes(before[1])
            state = root / ".codeops-roadmap-transaction"
            state.mkdir()
            for index in range(2):
                (state / f"{index}.before").write_bytes(before[index])
                (state / f"{index}.after").write_bytes(after[index])
            (state / "active.json").write_text(
                json.dumps({
                    "schema": 1,
                    "targets": [
                        "plans/00-roadmap.md",
                        "plans/_archive/two/00-roadmap.md",
                    ],
                    "beforeHashes": [rendering._digest(value) for value in before],
                    "afterHashes": [rendering._digest(value) for value in after],
                }),
                encoding="utf-8",
            )
            with mock.patch("scripts.codeops_roadmap_lib.rendering.run_mutation_preflight", return_value=0):
                code = rendering.write_rendered(root, {})
            self.assertEqual(code, 4)
            self.assertEqual(first.read_bytes(), before[0])
            self.assertEqual(second.read_bytes(), before[1])
            self.assertFalse(state.exists())

    def test_roadmap_recovery_rejects_noncanonical_journal_target(self) -> None:
        from scripts.codeops_roadmap_lib import rendering

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            protected = root / "README.md"
            protected.write_bytes(b"protected\n")
            state = root / ".codeops-roadmap-transaction"
            state.mkdir()
            before = b"attacker-before\n"
            after = b"protected\n"
            (state / "0.before").write_bytes(before)
            (state / "0.after").write_bytes(after)
            (state / "active.json").write_text(
                json.dumps({
                    "schema": 1,
                    "targets": ["README.md"],
                    "beforeHashes": [rendering._digest(before)],
                    "afterHashes": [rendering._digest(after)],
                }),
                encoding="utf-8",
            )
            with mock.patch("scripts.codeops_roadmap_lib.rendering.run_mutation_preflight", return_value=0):
                code = rendering.write_rendered(root, {})
            self.assertEqual(code, 3)
            self.assertEqual(protected.read_bytes(), b"protected\n")

    def test_roadmap_sync_refuses_invalid_authoritative_traceability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "codeops/features/feature").mkdir(parents=True)
            (root / "codeops/.codeops.yml").write_text("codeopsLayout: nested\n", encoding="utf-8")
            (root / "codeops/features/feature/traceability.json").write_text("{}\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/codeops_roadmap.py"),
                    "sync",
                    "--root",
                    str(root),
                    "--check",
                ],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
                shell=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("authoritative traceability is invalid", result.stderr)

    def test_worktree_preflight_covers_git_metadata_and_sibling_target(self) -> None:
        from scripts.codeops_worktree_lib.commands import create_worktree

        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / ".fixture").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            with mock.patch(
                "scripts.codeops_worktree_lib.commands.run_mutation_preflight",
                return_value=2,
            ) as preflight:
                code, payload = create_worktree(
                    project,
                    "feature",
                    base=None,
                    branch=None,
                    path=None,
                    dry_run=False,
                    launch=False,
                )
            self.assertEqual(code, 2)
            self.assertEqual(payload["result"], "blocked")
            boundary, targets = preflight.call_args.args[:2]
            self.assertEqual(boundary, project.parent.resolve())
            self.assertIn((project / ".git").resolve(), targets)
            self.assertIn((project.parent / "project-feature").resolve(), targets)

    def test_explicit_delete_branch_remains_forceful_for_unmerged_commit(self) -> None:
        from scripts.codeops_worktree_lib.commands import create_worktree, remove_worktree

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as plugin_data:
            project = Path(raw) / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / ".fixture").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            with mock.patch.dict(os.environ, {"PLUGIN_ROOT": str(ROOT), "PLUGIN_DATA": plugin_data}):
                code, created = create_worktree(
                    project,
                    "unmerged",
                    base=None,
                    branch=None,
                    path=None,
                    dry_run=False,
                    launch=False,
                )
                self.assertEqual(code, 0, created)
                worktree = Path(str(created["path"]))
                (worktree / "change.txt").write_text("unmerged\n", encoding="utf-8")
                subprocess.run(["git", "-C", str(worktree), "add", "."], check=True)
                subprocess.run(
                    ["git", "-C", str(worktree), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "unmerged"],
                    check=True,
                )
                code, removed = remove_worktree(
                    project,
                    str(worktree),
                    force=False,
                    delete_branch=True,
                    dry_run=False,
                )
            self.assertEqual(code, 0, removed)
            branch = subprocess.run(
                ["git", "-C", str(project), "show-ref", "--verify", "--quiet", "refs/heads/feat/unmerged"],
                check=False,
                shell=False,
            )
            self.assertNotEqual(branch.returncode, 0)

    def test_branch_delete_failure_restores_removed_worktree(self) -> None:
        from scripts.codeops_platform.subprocesses import CommandResult, run_command as real_run
        from scripts.codeops_worktree_lib.commands import create_worktree, remove_worktree

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as plugin_data:
            project = Path(raw) / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / ".fixture").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            with mock.patch.dict(os.environ, {"PLUGIN_ROOT": str(ROOT), "PLUGIN_DATA": plugin_data}):
                code, created = create_worktree(
                    project, "restore", base=None, branch=None, path=None, dry_run=False, launch=False
                )
                self.assertEqual(code, 0, created)
                worktree = Path(str(created["path"]))

                def fail_delete(argv, *, cwd, environment=None, evidence_sink=None):
                    if tuple(argv[-3:-1]) == ("branch", "-D"):
                        return CommandResult(tuple(argv), 1, "", "simulated branch delete failure")
                    return real_run(argv, cwd=cwd, environment=environment, evidence_sink=evidence_sink)

                with mock.patch("scripts.codeops_worktree_lib.commands.run_command", side_effect=fail_delete):
                    code, payload = remove_worktree(
                        project,
                        str(worktree),
                        force=False,
                        delete_branch=True,
                        dry_run=False,
                    )
            self.assertEqual(code, 1)
            self.assertTrue(payload["rolledBack"])
            self.assertTrue(worktree.is_dir())

    def test_roadmap_transaction_lock_refuses_concurrent_writer(self) -> None:
        from scripts.codeops_roadmap_lib.rendering import _exclusive_transaction_lock

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            with _exclusive_transaction_lock(root) as first:
                self.assertTrue(first)
                with _exclusive_transaction_lock(root) as second:
                    self.assertFalse(second)


class PortableRenderingAndReportingTests(unittest.TestCase):
    def test_roadmap_rendering_is_byte_deterministic(self) -> None:
        from scripts.codeops_roadmap_lib.model import synchronize
        from scripts.codeops_roadmap_lib.rendering import compact

        fixture = ROOT / "tests" / "fixtures" / "roadmap" / "nested"
        first_sync = synchronize(fixture, "2025-06-01")
        second_sync = synchronize(fixture, "2025-06-01")
        self.assertEqual(first_sync.drift, second_sync.drift)
        self.assertEqual(first_sync.rendered, second_sync.rendered)
        first_compact = compact(fixture)
        second_compact = compact(fixture)
        self.assertEqual(first_compact.rendered, second_compact.rendered)
        self.assertEqual(
            json.dumps(first_compact.to_json(fixture), sort_keys=True),
            json.dumps(second_compact.to_json(fixture), sort_keys=True),
        )

    def test_roadmap_injected_date_changes_only_with_owned_drift(self) -> None:
        from scripts.codeops_roadmap_lib.model import synchronize

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "plans").mkdir()
            roadmap = root / "plans/00-roadmap.md"
            roadmap.write_text(
                "# Roadmap\n\n"
                "> **Progress**: 0 / 1 (0%)\n"
                "> **Last Updated**: 1999-01-01\n\n"
                "## Tracker\n\n"
                "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
                "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
                "| RD-01 | Done | — | — | Done | done | 1999-01-01 | — |\n",
                encoding="utf-8",
            )
            changed = synchronize(root, "2026-08-06")
            rendered = changed.rendered[roadmap].decode("utf-8")
            self.assertIn("> **Progress**: 1 / 1 (100%)", rendered)
            self.assertIn("> **Last Updated**: 2026-08-06", rendered)
            roadmap.write_text(rendered, encoding="utf-8")
            stable = synchronize(root, "2099-01-01")
            self.assertEqual(stable.rendered, {})

    def test_verifier_forces_utf8_for_every_child(self) -> None:
        from scripts.codeops_verify_lib import core

        completed = SimpleNamespace(exit_code=0, stdout="", stderr="")
        with mock.patch("scripts.codeops_verify_lib.core.run_command", return_value=completed) as invoked:
            core._python(ROOT, "scripts/validate_plugin.py", ".", environment={"PATH": "fixture"})
        environment = invoked.call_args.kwargs["environment"]
        self.assertEqual(environment["PYTHONUTF8"], "1")
        self.assertEqual(environment["PYTHONIOENCODING"], "utf-8")

    @unittest.skipUnless(os.name == "nt", "native PowerShell launcher is Windows-only")
    def test_powershell_verifier_rejects_root_override(self) -> None:
        for option in ("--root", "--root=value", "--ro", "--r"):
            with self.subTest(option=option):
                arguments = [
                    "powershell.exe",
                    "-NoProfile",
                    "-File",
                    str(ROOT / "scripts/codeops-verify.ps1"),
                    "docs",
                    option,
                ]
                if option == "--root":
                    arguments.append(str(Path(tempfile.gettempdir())))
                result = subprocess.run(
                    arguments,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    capture_output=True,
                    check=False,
                    shell=False,
                )
                self.assertEqual(result.returncode, 2)

    def test_aggregate_reports_all_checks_after_failure_in_closed_order(self) -> None:
        from scripts.codeops_verify_lib.core import CHECK_NAMES, CheckResult, run_checks

        calls: list[str] = []

        def check(name: str, exit_code: int):
            def invoke(_root: Path) -> CheckResult:
                calls.append(name)
                return CheckResult(name, exit_code, stderr=f"{name}-diagnostic\n")

            return invoke

        checks = {
            name: check(name, 1 if name == "docs" else 0)
            for name in CHECK_NAMES
        }
        results = run_checks(ROOT, checks)
        self.assertEqual(calls, list(CHECK_NAMES))
        self.assertEqual([item.name for item in results], list(CHECK_NAMES))
        self.assertEqual([item.exit_code for item in results], [0, 1, 0, 0, 0])

    def test_all_unix_compatibility_launchers_are_thin(self) -> None:
        launchers = (
            "scripts/codeops-migrate.sh",
            "scripts/codeops-roadmap-sync.sh",
            "scripts/codeops-roadmap-compact.sh",
            "bin/codeops-worktree",
            "scripts/validate-codex.sh",
            "scripts/docs-check.sh",
            "scripts/migration-check.sh",
            "scripts/roadmap-sync-check.sh",
            "scripts/compact-check.sh",
        )
        for relative in launchers:
            with self.subTest(launcher=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                executable = [
                    line for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")
                ]
                self.assertIn("set -euo pipefail", text)
                self.assertIn('"$@"', text)
                self.assertLessEqual(len(executable), 12)

    def test_shipped_windows_paths_never_delegate_to_bash_or_wsl(self) -> None:
        hooks = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        windows_commands: list[str] = []

        def collect(value: object) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "commandWindows" and isinstance(child, str):
                        windows_commands.append(child)
                    collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)

        collect(hooks)
        self.assertTrue(windows_commands)
        for command in windows_commands:
            lowered = command.casefold()
            self.assertNotIn("wsl", lowered)
            self.assertNotIn("bash", lowered)
            self.assertNotIn("git-bash", lowered)

        forbidden = {"wsl", "wsl.exe", "bash", "bash.exe", "git-bash", "git-bash.exe"}
        python_paths = (
            ROOT / "scripts/codeops_hooks.py",
            ROOT / "scripts/codeops_migrate.py",
            ROOT / "scripts/codeops_roadmap.py",
            ROOT / "scripts/codeops_worktree.py",
            ROOT / "scripts/codeops_verify.py",
            ROOT / "scripts/codeops_platform/subprocesses.py",
        )
        call_names = {"run", "popen", "run_command", "call", "check_call", "check_output"}
        for path in python_paths:
            with self.subTest(path=path.relative_to(ROOT)):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call):
                        continue
                    function = node.func
                    name = function.attr if isinstance(function, ast.Attribute) else function.id if isinstance(function, ast.Name) else ""
                    if name.casefold() not in call_names:
                        continue
                    literals = {
                        item.value.casefold()
                        for item in ast.walk(node)
                        if isinstance(item, ast.Constant) and isinstance(item.value, str)
                    }
                    self.assertTrue(forbidden.isdisjoint(literals), f"forbidden delegation in {path}")

        for path in sorted((ROOT / "scripts").glob("*.ps1")):
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8").casefold()
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    self.assertNotRegex(
                        stripped,
                        r"(?:^|[;&|]\s*|start-process\s+)[\"']?(?:wsl(?:\.exe)?|bash(?:\.exe)?|git-bash(?:\.exe)?)\b",
                    )


@unittest.skipIf(os.name == "nt", "retained Unix launchers run only on the Ubuntu authority")
class UnixCharacterizationTests(unittest.TestCase):
    """Compare retained Unix surfaces with their portable Python owners."""

    def run_process(
        self,
        argv: list[str],
        *,
        cwd: Path,
        input_text: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            cwd=cwd,
            input=input_text,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
            shell=False,
        )

    def assert_same_process(
        self,
        portable: subprocess.CompletedProcess[str],
        retained: subprocess.CompletedProcess[str],
    ) -> None:
        self.assertEqual(retained.returncode, portable.returncode, retained.stderr)
        self.assertEqual(retained.stdout, portable.stdout)
        self.assertEqual(retained.stderr, portable.stderr)

    def test_migration_roadmap_and_compact_launchers_match_python(self) -> None:
        fixtures = ROOT / "scripts" / "fixtures"
        cases = (
            (
                fixtures / "flat-repo",
                [sys.executable, str(ROOT / "scripts/codeops_migrate.py"), "legacy", "--root", ".", "--dry-run", "--json"],
                [str(ROOT / "scripts/codeops-migrate.sh"), "--dry-run", "--json"],
            ),
            (
                fixtures / "roadmap-repo" / "nested",
                [sys.executable, str(ROOT / "scripts/codeops_roadmap.py"), "sync", "--root", ".", "--check", "--json"],
                [str(ROOT / "scripts/codeops-roadmap-sync.sh"), "--check", "--json"],
            ),
            (
                fixtures / "bloated-repo" / "flat",
                [sys.executable, str(ROOT / "scripts/codeops_roadmap.py"), "compact", "--root", ".", "--dry-run", "--json"],
                [str(ROOT / "scripts/codeops-roadmap-compact.sh"), "--dry-run", "--json"],
            ),
        )
        for source, portable_argv, retained_argv in cases:
            with self.subTest(launcher=retained_argv[0]), tempfile.TemporaryDirectory() as raw:
                project = Path(raw) / "fixture"
                shutil.copytree(source, project)
                portable = self.run_process(portable_argv, cwd=project)
                retained = self.run_process(retained_argv, cwd=project)
                self.assert_same_process(portable, retained)

    def test_worktree_and_hook_launchers_match_python(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project"
            project.mkdir()
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            (project / ".fixture").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(project), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(project), "-c", "user.name=CodeOps Test", "-c", "user.email=codeops@example.invalid", "commit", "-qm", "fixture"],
                check=True,
            )
            portable = self.run_process(
                [sys.executable, str(ROOT / "scripts/codeops_worktree.py"), "list", "--root", "."],
                cwd=project,
            )
            retained = self.run_process([str(ROOT / "bin/codeops-worktree"), "list"], cwd=project)
            self.assert_same_process(portable, retained)

        payload = (ROOT / "tests/fixtures/hooks/session-start-spaces.json").read_text(encoding="utf-8")
        environment = dict(os.environ, PLUGIN_ROOT=str(ROOT))
        portable = self.run_process(
            [sys.executable, str(ROOT / "scripts/codeops_hooks.py"), "--event", "SessionStart"],
            cwd=ROOT,
            input_text=payload,
            environment=environment,
        )
        retained = self.run_process(
            [str(ROOT / "scripts/hook_session_context.sh")],
            cwd=ROOT,
            input_text=payload,
            environment=environment,
        )
        self.assert_same_process(portable, retained)

    def test_agent_and_outcome_fixture_contracts_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw) / "project & data"
            project.mkdir()
            agent_argv = [
                sys.executable,
                str(ROOT / "scripts/install_agents.py"),
                "--project",
                str(project),
                "--roles",
                "explorer",
                "--dry-run",
            ]
            first = self.run_process(agent_argv, cwd=ROOT)
            second = self.run_process(agent_argv, cwd=ROOT)
            self.assert_same_process(first, second)

            store = project / "empty outcomes.jsonl"
            outcome_argv = [
                sys.executable,
                str(ROOT / "scripts/codeops_outcomes.py"),
                "report",
                "--root",
                str(project),
                "--store",
                str(store),
                "--json",
            ]
            first = self.run_process(outcome_argv, cwd=ROOT)
            second = self.run_process(outcome_argv, cwd=ROOT)
            self.assert_same_process(first, second)
            self.assertEqual(json.loads(first.stdout)["events"], 0)


if __name__ == "__main__":
    unittest.main()
