#!/usr/bin/env python3
"""Implementation tests for native Windows evidence capture and validation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from scripts.capture_windows_evidence import (
    _discard_capture,
    _normalized,
    _prepare_output,
    _write_json,
    capture,
)
from scripts.codeops_verify_lib.core import windows_evidence
from scripts.validate_windows_evidence import validate_evidence_set
from scripts.validate_plugin import validate_windows_support_claim
from scripts.windows_release_authority import load_authority, verify_candidate


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "windows-evidence" / "valid"
VERSION = "0.4.0"
COMMIT = "a" * 40


def validate(root: Path, cli: str = "cli.json", desktop: str | None = "desktop.json") -> list[str]:
    return validate_evidence_set(
        root,
        cli_path=root / cli,
        desktop_path=root / desktop if desktop else None,
        expected_version=VERSION,
        expected_commit=COMMIT,
    )


class EvidenceFixtureTests(unittest.TestCase):
    def test_valid_fixture_recomputes_all_supporting_hashes(self) -> None:
        self.assertEqual(validate(FIXTURE), [])

    def test_adversarial_fixture_is_rejected(self) -> None:
        errors = validate(FIXTURE, "invalid-cli.json")
        self.assertTrue(any("required scenario" in error for error in errors), errors)

    def test_unknown_fields_and_traversal_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
            payload = json.loads((root / "cli.json").read_text(encoding="utf-8"))
            payload["secretOutput"] = "must not be retained"
            payload["scenarios"][0]["record"] = "../outside.json"
            (root / "cli.json").write_text(json.dumps(payload), encoding="utf-8")
            errors = validate(root)
        self.assertTrue(any("unknown field" in error for error in errors), errors)
        self.assertTrue(any("inside the evidence root" in error for error in errors), errors)

    def test_record_schema_is_closed_and_bound_to_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
            record = root / "records" / "installation.json"
            payload = json.loads(record.read_text(encoding="utf-8"))
            payload["stdout"] = "project content"
            record.write_text(json.dumps(payload), encoding="utf-8")
            errors = validate(root)
        self.assertTrue(any("hash" in error for error in errors), errors)
        self.assertTrue(any("unknown field `stdout`" in error for error in errors), errors)

    def test_desktop_candidate_hash_must_match_cli(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
            desktop = json.loads((root / "desktop.json").read_text(encoding="utf-8"))
            desktop["candidateSha256"] = "c" * 64
            (root / "desktop.json").write_text(json.dumps(desktop), encoding="utf-8")
            errors = validate(root)
        self.assertTrue(any("candidateSha256" in error for error in errors), errors)

    def test_independent_candidate_hash_rejects_a_self_consistent_stale_pair(self) -> None:
        errors = validate_evidence_set(
            FIXTURE,
            cli_path=FIXTURE / "cli.json",
            desktop_path=FIXTURE / "desktop.json",
            expected_version=VERSION,
            expected_commit=COMMIT,
            expected_candidate_sha256="c" * 64,
        )
        self.assertTrue(any("release authority" in error for error in errors), errors)

    def test_release_authority_rehashes_the_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            candidate = root / "candidate.zip"
            candidate.write_bytes(b"candidate")
            digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
            authority_path = root / "authority.json"
            authority_path.write_text(json.dumps({
                "schemaVersion": 1,
                "pluginVersion": VERSION,
                "sourceCommit": COMMIT,
                "candidateSha256": digest,
                "artifactName": "candidate.zip",
                "ci": {
                    "runId": "1", "headCommit": COMMIT, "conclusion": "success",
                    "artifactName": "candidate.zip",
                },
            }), encoding="utf-8")
            authority, errors = load_authority(authority_path, VERSION)
            self.assertEqual(errors, [])
            self.assertEqual(verify_candidate(candidate, authority), [])
            candidate.write_bytes(b"different")
            self.assertTrue(verify_candidate(candidate, authority))

    def test_release_authority_binds_ci_head_to_candidate_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "authority.json"
            path.write_text(json.dumps({
                "schemaVersion": 1,
                "pluginVersion": VERSION,
                "sourceCommit": COMMIT,
                "candidateSha256": "b" * 64,
                "artifactName": "candidate.zip",
                "ci": {
                    "runId": "1", "headCommit": "c" * 40, "conclusion": "success",
                    "artifactName": "candidate.zip",
                },
            }), encoding="utf-8")
            _, errors = load_authority(path, VERSION)
        self.assertTrue(any("must match sourceCommit" in error for error in errors), errors)


class CaptureBoundaryTests(unittest.TestCase):
    def test_capture_uses_installed_workflows_and_inherited_command_evidence(self) -> None:
        source = (ROOT / "scripts" / "capture_windows_evidence.py").read_text(encoding="utf-8")
        self.assertNotIn("SCENARIO_TESTS", source)
        self.assertNotIn('(sys.executable, "-m", "unittest"', source)
        self.assertIn('"CODEOPS_COMMAND_EVIDENCE"', source)
        self.assertIn('"plugin", "add"', source)
        self.assertIn('args.codex, "exec"', source)
        self.assertIn("_codex_commands", source)
        self.assertIn("installed scenarios failed", source)

    def test_path_sanitizer_replaces_candidate_root(self) -> None:
        plugin = Path("C:/Candidate With Spaces")
        value = _normalized("C:/Candidate With Spaces/scripts/codeops_verify.py", plugin)
        self.assertEqual(value, "<PLUGIN_ROOT>/scripts/codeops_verify.py")

    def test_capture_refuses_non_windows_before_touching_candidate(self) -> None:
        args = argparse.Namespace(
            root=ROOT, candidate=ROOT / "missing.zip", output=ROOT / "unused",
            reviewer="octocat", ci_run_id="1", ci_commit=COMMIT,
            ci_conclusion="success", codex_version="codex-cli 1.0.0",
        )
        with patch("scripts.capture_windows_evidence.os.name", "posix"):
            with self.assertRaisesRegex(RuntimeError, "native Windows 11"):
                capture(args)

    def test_output_preserves_existing_evidence_and_refuses_version_collision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "evidence"
            output.mkdir()
            retained = output / "prior.json"
            retained.write_text("retained\n", encoding="utf-8")
            records, manifest = _prepare_output(output, VERSION)
            _write_json(manifest, {"status": "partial"})
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                _prepare_output(output, VERSION)
            _discard_capture(records, manifest)
            self.assertEqual(retained.read_text(encoding="utf-8"), "retained\n")
            self.assertTrue(output.is_dir())

    def test_json_writer_uses_lf_for_hash_stability(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "record.json"
            _write_json(path, {"line": "one\ntwo"})
            self.assertNotIn(b"\r\n", path.read_bytes())

    def test_capture_cleans_global_install_after_primary_failure(self) -> None:
        target = ("codex", "market", ROOT, {})

        def fail(_args: argparse.Namespace, cleanup: list[object]) -> Path:
            cleanup.append(target)
            raise RuntimeError("injected capture failure")

        with patch("scripts.capture_windows_evidence._capture", side_effect=fail), patch(
            "scripts.capture_windows_evidence._remove_certification_install", return_value=[],
        ) as cleanup:
            with self.assertRaisesRegex(RuntimeError, "injected capture failure"):
                capture(argparse.Namespace())
        cleanup.assert_called_once_with(*target)


class PortableVerificationTests(unittest.TestCase):
    def test_portable_gate_allows_absent_pre_release_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                '{"version":"0.4.0"}\n', encoding="utf-8",
            )
            result = windows_evidence(root)
        self.assertEqual(result.exit_code, 0, result.stderr)

    def test_full_gate_requires_both_evidence_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                '{"version":"0.4.0"}\n', encoding="utf-8",
            )
            result = windows_evidence(root, required=True)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("CLI evidence", result.stderr)
        self.assertIn("desktop evidence", result.stderr)

    def test_installed_gate_rehashes_external_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".codex-plugin").mkdir()
            (root / ".codex-plugin" / "plugin.json").write_text(
                '{"version":"0.4.0"}\n', encoding="utf-8",
            )
            candidate = root / "candidate.zip"
            candidate.write_bytes(b"wrong candidate")
            authority = {
                "sourceCommit": COMMIT,
                "candidateSha256": "b" * 64,
                "ci": {"headCommit": COMMIT},
            }
            with patch("scripts.codeops_verify_lib.core.load_authority", return_value=(authority, [])), patch(
                "scripts.codeops_verify_lib.core.validate_evidence_set", return_value=[],
            ), patch.dict("os.environ", {"CODEOPS_WINDOWS_CANDIDATE": str(candidate)}, clear=False):
                result = windows_evidence(root, required=True)
        self.assertEqual(result.exit_code, 1)
        self.assertIn("SHA-256", result.stderr)


class ReleaseClaimGuardTests(unittest.TestCase):
    def test_current_certified_documentation_passes_claim_guard(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        errors: list[str] = []
        validate_windows_support_claim(ROOT, manifest, errors)
        self.assertEqual(errors, [])

    def test_affirmative_claim_without_retained_pair_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "README.md").write_text(
                "CodeOps supports native Windows 11 with Python 3.10 or newer.\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            validate_windows_support_claim(root, {"version": VERSION}, errors)
        self.assertTrue(any("CLI evidence" in error for error in errors), errors)
        self.assertTrue(any("desktop evidence" in error for error in errors), errors)

    def test_conflicting_pending_wording_blocks_a_claim(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "README.md").write_text(
                "CodeOps supports native Windows 11. Windows remains unsupported.\n",
                encoding="utf-8",
            )
            errors: list[str] = []
            validate_windows_support_claim(root, {"version": VERSION}, errors)
        self.assertTrue(any("conflicts" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
