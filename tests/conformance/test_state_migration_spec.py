#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
REVISION = "sha256:" + hashlib.sha256(b"# Artifact\n").hexdigest()


def requirement(status: str = "draft", *, edges: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "id": "RD-001",
        "type": "requirement",
        "title": "Requirement",
        "status": status,
        "semanticSources": [{
            "path": "artifact.md",
            "selector": {"kind": "whole-file"},
            "normalization": "utf8-lf-trim-trailing-v1",
            "digest": "sha256",
        }],
        "revision": REVISION,
        "edges": edges or [],
        "validations": [],
    }


class TransitionSpecificationTests(unittest.TestCase):
    def make_root(self, raw: str, nodes: list[dict[str, Any]]) -> tuple[Path, Path]:
        root = Path(raw)
        (root / "artifact.md").write_text("# Artifact\n", encoding="utf-8")
        graph_root = root / "codeops" / "features" / "sample"
        graph_root.mkdir(parents=True)
        graph = graph_root / "traceability.json"
        graph.write_text(
            json.dumps({"schema": 2, "feature": "sample", "nodes": nodes}, indent=2) + "\n",
            encoding="utf-8",
        )
        return root, graph

    def request(
        self,
        root: Path,
        *,
        requested_status: str,
        expected_status: str = "draft",
        expected_revision: str = REVISION,
        operation_id: str = "op-1",
    ) -> Path:
        path = root / "request.json"
        path.write_text(
            json.dumps({
                "schema": 1,
                "operationId": operation_id,
                "target": "sample/RD-001",
                "expected": {
                    "status": expected_status,
                    "revision": expected_revision,
                },
                "requested": {"status": requested_status},
                "gate": "requirements",
                "sourceUpdates": [],
                "validationAdditions": [],
                "validationRemovals": [],
                "staleReason": None,
                "evidence": {},
            }),
            encoding="utf-8",
        )
        return path

    def run_command(
        self,
        command: str,
        root: Path,
        request: Path,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                command,
                "--root",
                str(root),
                "--request",
                str(request),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def payload(self, result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        self.assertTrue(result.stdout, result.stderr)
        return json.loads(result.stdout)

    def run_upgrade(
        self,
        root: Path,
        preview: Path,
        *,
        apply: bool = False,
        resolutions: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT),
            "traceability-upgrade",
            "--root",
            str(root),
            "--feature",
            "sample",
            "--preview",
            str(preview),
            "--json",
        ]
        if apply:
            command.append("--apply")
        if resolutions is not None:
            command.extend(["--resolutions", str(resolutions)])
        return subprocess.run(command, text=True, capture_output=True, check=False)

    def upgrade_root(self, raw: str) -> Path:
        source = ROOT / "tests" / "fixtures" / "state-v1-upgrade" / "ambiguous"
        root = Path(raw)
        shutil.copytree(source, root, dirs_exist_ok=True)
        return root

    def test_legal_projected_approval_commits_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [requirement()])
            request = self.request(root, requested_status="approved")
            result = self.run_command("transition", root, request)
            payload = self.payload(result)
            after = json.loads(graph.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, payload)
        self.assertEqual(payload["result"], "committed")
        self.assertEqual(payload["target"], "sample/RD-001")
        self.assertEqual(after["nodes"][0]["status"], "approved")

    def test_st_43_illegal_jump_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [requirement()])
            before = graph.read_bytes()
            request = self.request(root, requested_status="stale")
            result = self.run_command("transition", root, request)
            payload = self.payload(result)
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(before, after)
        self.assertIn("invalid-transition", {item["code"] for item in payload["blockers"]})

    def test_compare_and_swap_mismatch_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [requirement()])
            before = graph.read_bytes()
            request = self.request(
                root,
                requested_status="approved",
                expected_revision="sha256:" + ("1" * 64),
            )
            result = self.run_command("transition", root, request)
            payload = self.payload(result)
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(before, after)
        self.assertIn("compare-and-swap", {item["code"] for item in payload["blockers"]})

    def test_st_49_invalid_projected_dependency_does_not_write(self) -> None:
        dependency = requirement(status="draft")
        dependency["id"] = "RD-UP"
        target = requirement(edges=[{"relation": "depends-on", "target": "sample/RD-UP"}])
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [target, dependency])
            before = graph.read_bytes()
            request = self.request(root, requested_status="approved")
            result = self.run_command("transition", root, request)
            payload = self.payload(result)
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(before, after)
        self.assertIn("status-not-ready", {item["code"] for item in payload["blockers"]})

    def test_caller_cannot_replace_governing_gate_with_audit(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [requirement()])
            request = self.request(root, requested_status="approved")
            payload = json.loads(request.read_text(encoding="utf-8"))
            payload["gate"] = "audit"
            request.write_text(json.dumps(payload), encoding="utf-8")
            before = graph.read_bytes()
            result = self.run_command("transition", root, request)
            response = self.payload(result)
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(response["blockers"][0]["code"], "invalid-transition-gate")
        self.assertEqual(after, before)

    def test_evidence_transitions_support_test_and_task_lifecycle(self) -> None:
        test_node = requirement(status="planned")
        test_node.update({"id": "TEST-1", "type": "test"})
        implementation = requirement(status="present")
        implementation.update({"id": "IMPL-1", "type": "implementation"})
        verification = requirement(status="planned")
        verification.update({"id": "VERIFY-1", "type": "verification"})
        task = requirement(status="pending")
        task.update({
            "id": "TASK-1",
            "type": "task",
        })
        criterion = requirement(status="approved")
        criterion.update({
            "id": "CRIT-1",
            "type": "criterion",
            "edges": [
                {"relation": "tested-by", "target": "sample/TEST-1"},
                {"relation": "implemented-by", "target": "sample/TASK-1"},
                {"relation": "implemented-by", "target": "sample/IMPL-1"},
                {"relation": "verified-by", "target": "sample/VERIFY-1"},
            ],
            "validations": [{
                "upstream": "sample/TEST-1",
                "relation": "tested-by",
                "revision": REVISION,
                "gate": "task-complete",
                "validatedAt": "2026-07-23T00:00:00Z",
            }, {
                "upstream": "sample/TASK-1",
                "relation": "implemented-by",
                "revision": REVISION,
                "gate": "task-complete",
                "validatedAt": "2026-07-23T00:00:00Z",
            }]
        })
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(
                raw, [criterion, task, test_node, implementation, verification]
            )

            def advance(
                operation: str,
                target: str,
                expected_status: str,
                requested_status: str,
                gate: str,
                evidence: dict[str, str],
            ) -> subprocess.CompletedProcess[str]:
                request = self.request(
                    root,
                    requested_status="approved",
                    operation_id=operation,
                )
                payload = json.loads(request.read_text(encoding="utf-8"))
                payload["target"] = target
                payload["expected"]["status"] = expected_status
                payload["requested"]["status"] = requested_status
                payload["gate"] = gate
                payload["evidence"] = evidence
                request.write_text(json.dumps(payload), encoding="utf-8")
                return self.run_command("transition", root, request)

            results = [
                advance(
                    "op-red",
                    "sample/TEST-1",
                    "planned",
                    "red-confirmed",
                    "task-complete",
                    {"redEvidence": "expected failing test"},
                ),
                advance(
                    "op-green",
                    "sample/TEST-1",
                    "red-confirmed",
                    "passing",
                    "task-complete",
                    {"greenEvidence": "passing test command"},
                ),
                advance(
                    "op-impl-verified",
                    "sample/IMPL-1",
                    "present",
                    "verified",
                    "task-complete",
                    {"verificationEvidence": "implementation verification"},
                ),
                advance(
                    "op-verification-passing",
                    "sample/VERIFY-1",
                    "planned",
                    "passing",
                    "task-complete",
                    {"commandEvidence": "verification command passed"},
                ),
                advance(
                    "op-implemented",
                    "sample/TASK-1",
                    "pending",
                    "implemented",
                    "plan",
                    {},
                ),
                advance(
                    "op-verified",
                    "sample/TASK-1",
                    "implemented",
                    "verified",
                    "task-complete",
                    {"verificationEvidence": "verified test closure"},
                ),
            ]
            final = json.loads(graph.read_text(encoding="utf-8"))
        self.assertEqual(
            [result.returncode for result in results],
            [0, 0, 0, 0, 0, 0],
        )
        statuses = {item["id"]: item["status"] for item in final["nodes"]}
        self.assertEqual(statuses["TASK-1"], "verified")
        self.assertEqual(statuses["TEST-1"], "passing")
        self.assertEqual(statuses["IMPL-1"], "verified")
        self.assertEqual(statuses["VERIFY-1"], "passing")

    def test_st_27_preview_requires_complete_explicit_resolutions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.upgrade_root(raw)
            preview = root / "preview.json"
            before = (
                root / "codeops" / "features" / "sample" / "traceability.json"
            ).read_bytes()
            preview_result = self.run_upgrade(root, preview)
            preview_payload = self.payload(preview_result)
            after_preview = (
                root / "codeops" / "features" / "sample" / "traceability.json"
            ).read_bytes()
            incomplete = root / "incomplete.json"
            incomplete.write_text(
                json.dumps({
                    "schema": 1,
                    "previewHash": preview_payload["previewHash"],
                    "decisions": {},
                }),
                encoding="utf-8",
            )
            apply_result = self.run_upgrade(
                root, preview, apply=True, resolutions=incomplete
            )
        self.assertEqual(preview_result.returncode, 0, preview_result.stderr)
        self.assertEqual(before, after_preview)
        self.assertEqual(apply_result.returncode, 1)

    def test_st_39_resolved_apply_is_valid_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.upgrade_root(raw)
            preview = root / "preview.json"
            preview_result = self.run_upgrade(root, preview)
            preview_payload = self.payload(preview_result)
            template = json.loads(
                (
                    ROOT
                    / "tests"
                    / "fixtures"
                    / "state-v1-upgrade"
                    / "resolutions-template.json"
                ).read_text(encoding="utf-8")
            )
            template["previewHash"] = preview_payload["previewHash"]
            resolutions = root / "resolutions.json"
            resolutions.write_text(json.dumps(template), encoding="utf-8")
            first = self.run_upgrade(
                root, preview, apply=True, resolutions=resolutions
            )
            second = self.run_upgrade(
                root, preview, apply=True, resolutions=resolutions
            )
            graph = json.loads(
                (
                    root
                    / "codeops"
                    / "features"
                    / "sample"
                    / "traceability.json"
                ).read_text(encoding="utf-8")
            )
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self.payload(second)["result"], "no-change")
        self.assertEqual(graph["schema"], 2)

    def test_st_47_non_identical_backup_collision_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = self.upgrade_root(raw)
            graph = (
                root / "codeops" / "features" / "sample" / "traceability.json"
            )
            backup = graph.with_name("traceability.schema1.backup.json")
            backup.write_text('{"different":true}\n', encoding="utf-8")
            preview = root / "preview.json"
            preview_result = self.run_upgrade(root, preview)
            preview_payload = self.payload(preview_result)
            template = json.loads(
                (
                    ROOT
                    / "tests"
                    / "fixtures"
                    / "state-v1-upgrade"
                    / "resolutions-template.json"
                ).read_text(encoding="utf-8")
            )
            template["previewHash"] = preview_payload["previewHash"]
            resolutions = root / "resolutions.json"
            resolutions.write_text(json.dumps(template), encoding="utf-8")
            before = graph.read_bytes()
            result = self.run_upgrade(
                root, preview, apply=True, resolutions=resolutions
            )
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(after, before)

    def test_st_44_recovery_refuses_when_owner_absence_is_unproven(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph = self.make_root(raw, [requirement()])
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            owner = {
                "pid": os.getpid(),
                "startTicks": Path(f"/proc/{os.getpid()}/stat").read_text().split()[21],
                "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            }
            (state / "op-1.lock").write_text(
                json.dumps({"operationId": "op-1", "owner": owner, "nonce": "lock-1"}),
                encoding="utf-8",
            )
            recovery = root / "recovery.json"
            recovery.write_text(
                json.dumps({
                    "schema": 1,
                    "operationId": "op-1",
                    "direction": "rollback",
                    "expectedLock": "lock-1",
                    "expectedOwner": owner,
                    "graphs": [],
                }),
                encoding="utf-8",
            )
            before = graph.read_bytes()
            result = self.run_command("transition-recover", root, recovery)
            payload = self.payload(result)
            after = graph.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["result"], "refused")
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
