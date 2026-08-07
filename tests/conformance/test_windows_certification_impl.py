#!/usr/bin/env python3
"""Implementation tests for native Windows evidence capture and validation."""

from __future__ import annotations

import argparse
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


class CaptureBoundaryTests(unittest.TestCase):
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
