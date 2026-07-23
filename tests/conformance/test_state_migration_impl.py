#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import shutil
from pathlib import Path
from unittest import mock

from scripts.codeops_state_lib import migration, transitions
from scripts.codeops_state_lib.models import StructuralProblem
from scripts.codeops_state_lib.revisions import normalize_utf8


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "codeops_state.py"
ARTIFACT = b"# Artifact\n"
REVISION = "sha256:" + hashlib.sha256(ARTIFACT).hexdigest()
ABSENT_OWNER = {
    "pid": 999999,
    "startTicks": "1",
    "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
}


def graph(status: str = "draft") -> dict[str, object]:
    return {
        "schema": 2,
        "feature": "sample",
        "nodes": [{
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
            "edges": [],
            "validations": [],
        }],
    }


class TransitionImplementationTests(unittest.TestCase):
    def make_root(self, raw: str) -> tuple[Path, Path]:
        root = Path(raw)
        (root / "artifact.md").write_bytes(ARTIFACT)
        graph_path = root / "codeops" / "features" / "sample" / "traceability.json"
        graph_path.parent.mkdir(parents=True)
        graph_path.write_text(json.dumps(graph(), indent=2) + "\n", encoding="utf-8")
        return root, graph_path

    def write_transition(self, root: Path, operation: str) -> Path:
        request = root / f"{operation}.json"
        request.write_text(json.dumps({
            "schema": 1,
            "operationId": operation,
            "target": "sample/RD-001",
            "expected": {"status": "draft", "revision": REVISION},
            "requested": {"status": "approved"},
            "gate": "requirements",
            "sourceUpdates": [],
            "validationAdditions": [],
            "validationRemovals": [],
            "staleReason": None,
            "evidence": {},
        }), encoding="utf-8")
        return request

    def command(self, command: str, root: Path, request: Path) -> list[str]:
        return [
            sys.executable,
            str(SCRIPT),
            command,
            "--root",
            str(root),
            "--request",
            str(request),
            "--json",
        ]

    def make_upgrade(self, raw: str) -> tuple[Path, Path, Path]:
        root = Path(raw)
        fixture = ROOT / "tests" / "fixtures" / "state-v1-upgrade" / "ambiguous"
        shutil.copytree(fixture, root, dirs_exist_ok=True)
        preview = root / "preview.json"
        code, payload = migration.make_preview(root, "sample", preview)
        self.assertEqual(code, 0, payload)
        template = json.loads(
            (
                ROOT
                / "tests"
                / "fixtures"
                / "state-v1-upgrade"
                / "resolutions-template.json"
            ).read_text(encoding="utf-8")
        )
        template["previewHash"] = payload["previewHash"]
        resolutions = root / "resolutions.json"
        resolutions.write_text(json.dumps(template), encoding="utf-8")
        return root, preview, resolutions

    def test_st_37_concurrent_compare_and_swap_has_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            requests = [self.write_transition(root, f"op-{index}") for index in (1, 2)]
            processes = [
                subprocess.Popen(self.command("transition", root, request), stdout=subprocess.PIPE, text=True)
                for request in requests
            ]
            results = []
            for process in processes:
                stdout, _ = process.communicate()
                results.append((process.returncode, json.loads(stdout)))
            committed = json.loads(graph_path.read_text(encoding="utf-8"))
        self.assertEqual([code for code, _ in results].count(0), 1, results)
        self.assertEqual(committed["nodes"][0]["status"], "approved")

    def test_existing_lock_is_never_silently_removed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, _ = self.make_root(raw)
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            active = state / "active.lock"
            active.write_text('{"operationId":"prior"}', encoding="utf-8")
            request = self.write_transition(root, "op-1")
            result = subprocess.run(self.command("transition", root, request), capture_output=True, text=True)
            payload = json.loads(result.stdout)
            retained = active.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(payload["blockers"][0]["code"], "transition-locked")
        self.assertEqual(retained, b'{"operationId":"prior"}')

    def test_st_48_recovery_repeat_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            before = graph_path.read_bytes()
            after = (json.dumps(graph("approved"), indent=2) + "\n").encode()
            graph_path.write_bytes(after)
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            (state / "op-1.before").write_bytes(before)
            (state / "op-1.after").write_bytes(after)
            (state / "op-1.lock").write_text(
                json.dumps({"operationId": "op-1", "owner": ABSENT_OWNER, "nonce": "n-1"}),
                encoding="utf-8",
            )
            record = {
                "path": str(graph_path.relative_to(root)),
                "beforeHash": "sha256:" + hashlib.sha256(before).hexdigest(),
                "afterHash": "sha256:" + hashlib.sha256(after).hexdigest(),
            }
            (state / "op-1.journal.json").write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "lockNonce": "n-1",
                "owner": ABSENT_OWNER,
                "direction": None,
                "graphs": [{
                    **record,
                    "beforeImage": "op-1.before",
                    "afterImage": "op-1.after",
                    "committed": True,
                }],
            }), encoding="utf-8")
            request = root / "recovery.json"
            request.write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "direction": "rollback",
                "expectedLock": "n-1",
                "expectedOwner": ABSENT_OWNER,
                "graphs": [record],
            }), encoding="utf-8")
            first = subprocess.run(self.command("transition-recover", root, request), capture_output=True, text=True)
            second = subprocess.run(self.command("transition-recover", root, request), capture_output=True, text=True)
            restored = graph_path.read_bytes()
        self.assertEqual(first.returncode, 0, first.stdout)
        self.assertEqual(json.loads(first.stdout)["result"], "recovered")
        self.assertEqual(second.returncode, 0, second.stdout)
        self.assertEqual(json.loads(second.stdout)["result"], "already-recovered")
        self.assertEqual(restored, before)

    def test_st_46_interrupted_journal_rolls_forward(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            before = graph_path.read_bytes()
            after = (json.dumps(graph("approved"), indent=2) + "\n").encode()
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            (state / "op-1.before").write_bytes(before)
            (state / "op-1.after").write_bytes(after)
            (state / "op-1.lock").write_text(
                json.dumps({"operationId": "op-1", "owner": ABSENT_OWNER, "nonce": "n-1"}),
                encoding="utf-8",
            )
            record = {
                "path": str(graph_path.relative_to(root)),
                "beforeHash": "sha256:" + hashlib.sha256(before).hexdigest(),
                "afterHash": "sha256:" + hashlib.sha256(after).hexdigest(),
            }
            (state / "op-1.journal.json").write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "lockNonce": "n-1",
                "owner": ABSENT_OWNER,
                "direction": None,
                "graphs": [{
                    **record,
                    "beforeImage": "op-1.before",
                    "afterImage": "op-1.after",
                    "committed": False,
                }],
            }), encoding="utf-8")
            request = root / "recovery.json"
            request.write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "direction": "roll-forward",
                "expectedLock": "n-1",
                "expectedOwner": ABSENT_OWNER,
                "graphs": [record],
            }), encoding="utf-8")
            result = subprocess.run(
                self.command("transition-recover", root, request),
                capture_output=True,
                text=True,
            )
            committed = graph_path.read_bytes()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["result"], "recovered")
        self.assertEqual(committed, after)

    def test_st_45_post_write_validation_restores_before_image(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            before = graph_path.read_bytes()
            request = self.write_transition(root, "op-1")
            real_load = transitions._load_v2
            calls = 0

            def fail_post_write(
                project_root: Path, refresh_target: str | None = None
            ):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return real_load(project_root, refresh_target)
                return [], [
                    StructuralProblem(
                        "injected-post-write-failure",
                        "post-write validation failed",
                        graph_path,
                    )
                ]

            with mock.patch.object(
                transitions, "_load_v2", side_effect=fail_post_write
            ):
                code, payload = transitions.transition(root, request)
            restored = graph_path.read_bytes()
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "post-write-validation")
        self.assertEqual(restored, before)

    def test_recovery_refuses_moved_or_escaping_graph(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, _ = self.make_root(raw)
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            (state / "op-1.lock").write_text(
                json.dumps({"operationId": "op-1", "owner": ABSENT_OWNER, "nonce": "n-1"}), encoding="utf-8"
            )
            record = {
                "path": "../outside.json",
                "beforeHash": "sha256:" + ("0" * 64),
                "afterHash": "sha256:" + ("1" * 64),
            }
            (state / "op-1.journal.json").write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "lockNonce": "n-1",
                "owner": ABSENT_OWNER,
                "direction": None,
                "graphs": [{
                    **record,
                    "beforeImage": "op-1.before",
                    "afterImage": "op-1.after",
                    "committed": False,
                }],
            }), encoding="utf-8")
            request = root / "recovery.json"
            request.write_text(json.dumps({
                "schema": 1,
                "operationId": "op-1",
                "direction": "rollback",
                "expectedLock": "n-1",
                "expectedOwner": ABSENT_OWNER,
                "graphs": [record],
            }), encoding="utf-8")
            result = subprocess.run(self.command("transition-recover", root, request), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["blockers"][0]["code"], "unsafe-recovery-path")

    def test_cross_platform_normalization_is_stable(self) -> None:
        variants = (b"\xef\xbb\xbfline  \r\nnext\t\r\n", b"line\nnext\n")
        normalized = [normalize_utf8(value).encode() for value in variants]
        self.assertEqual(normalized[0], normalized[1])
        self.assertEqual(
            hashlib.sha256(normalized[0]).hexdigest(),
            hashlib.sha256(normalized[1]).hexdigest(),
        )

    def test_operation_id_cannot_escape_transaction_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, _ = self.make_root(raw)
            request = self.write_transition(root, "safe")
            payload = json.loads(request.read_text(encoding="utf-8"))
            payload["operationId"] = "../escape"
            request.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(self.command("transition", root, request), capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["blockers"][0]["code"], "invalid-request")

    def test_revision_change_invalidates_downstream_graph_in_same_journal(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, upstream_path = self.make_root(raw)
            upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
            upstream["nodes"][0]["status"] = "approved"
            upstream_path.write_text(json.dumps(upstream, indent=2) + "\n", encoding="utf-8")
            consumer_path = root / "codeops" / "features" / "consumer" / "traceability.json"
            consumer_path.parent.mkdir(parents=True)
            consumer = graph("approved")
            consumer["feature"] = "consumer"
            consumer["nodes"][0]["edges"] = [
                {"relation": "depends-on", "target": "sample/RD-001"}
            ]
            consumer["nodes"][0]["validations"] = [{
                "upstream": "sample/RD-001",
                "relation": "depends-on",
                "revision": REVISION,
                "gate": "requirements",
                "validatedAt": "2026-07-23T00:00:00Z",
            }]
            consumer_path.write_text(json.dumps(consumer, indent=2) + "\n", encoding="utf-8")
            request = self.write_transition(root, "op-1")
            payload = json.loads(request.read_text(encoding="utf-8"))
            payload["expected"]["status"] = "approved"
            payload["requested"]["status"] = "stale"
            payload["staleReason"] = "semantic source changed"
            payload["evidence"] = {"invalidation": "source digest changed"}
            request.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                self.command("transition", root, request),
                capture_output=True,
                text=True,
            )
            response = json.loads(result.stdout)
            downstream = json.loads(consumer_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, response)
        self.assertEqual(len(response["graphs"]), 2)
        self.assertEqual(downstream["nodes"][0]["status"], "stale")

    def test_transitive_invalidation_reaches_cross_graph_fixed_point(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, upstream_path = self.make_root(raw)
            upstream = json.loads(upstream_path.read_text(encoding="utf-8"))
            upstream["nodes"][0]["status"] = "approved"
            upstream_path.write_text(json.dumps(upstream, indent=2) + "\n", encoding="utf-8")
            prior = "sample/RD-001"
            paths: list[Path] = []
            for feature in ("middle", "downstream"):
                path = root / "codeops" / "features" / feature / "traceability.json"
                path.parent.mkdir(parents=True)
                value = graph("approved")
                value["feature"] = feature
                value["nodes"][0]["edges"] = [
                    {"relation": "depends-on", "target": prior}
                ]
                path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
                paths.append(path)
                prior = f"{feature}/RD-001"
            request = self.write_transition(root, "op-transitive")
            payload = json.loads(request.read_text(encoding="utf-8"))
            payload["expected"]["status"] = "approved"
            payload["requested"]["status"] = "stale"
            payload["staleReason"] = "upstream invalidated"
            payload["evidence"] = {"invalidation": "upstream invalidated"}
            request.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                self.command("transition", root, request),
                capture_output=True,
                text=True,
            )
            response = json.loads(result.stdout)
            statuses = [
                json.loads(path.read_text(encoding="utf-8"))["nodes"][0]["status"]
                for path in paths
            ]
        self.assertEqual(result.returncode, 0, response)
        self.assertEqual(len(response["graphs"]), 3)
        self.assertEqual(statuses, ["stale", "stale"])

    def test_revision_refresh_repairs_only_targeted_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            value = json.loads(graph_path.read_text(encoding="utf-8"))
            value["nodes"][0]["status"] = "approved"
            graph_path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            (root / "artifact.md").write_text("# Changed\n", encoding="utf-8")
            request = self.write_transition(root, "op-refresh")
            payload = json.loads(request.read_text(encoding="utf-8"))
            payload["expected"]["status"] = "approved"
            payload["requested"]["status"] = "stale"
            payload["sourceUpdates"] = [{"path": "artifact.md"}]
            payload["staleReason"] = "semantic source changed"
            payload["evidence"] = {"invalidation": "semantic source changed"}
            request.write_text(json.dumps(payload), encoding="utf-8")
            result = subprocess.run(
                self.command("transition", root, request),
                capture_output=True,
                text=True,
            )
            response = json.loads(result.stdout)
            changed = json.loads(graph_path.read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, response)
        self.assertEqual(changed["nodes"][0]["status"], "stale")
        self.assertEqual(
            changed["nodes"][0]["revision"],
            "sha256:" + hashlib.sha256(b"# Changed\n").hexdigest(),
        )

    def test_completed_operation_id_cannot_be_reused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, graph_path = self.make_root(raw)
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            (state / "op-1.completed.json").write_text(
                json.dumps({
                    "schema": 1,
                    "operationId": "op-1",
                    "direction": "rollback",
                    "graphs": [],
                }),
                encoding="utf-8",
            )
            request = self.write_transition(root, "op-1")
            before = graph_path.read_bytes()
            result = subprocess.run(
                self.command("transition", root, request),
                capture_output=True,
                text=True,
            )
            response = json.loads(result.stdout)
            after = graph_path.read_bytes()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(response["blockers"][0]["code"], "operation-id-reused")
        self.assertEqual(after, before)

    def test_upgrade_rejects_malformed_and_changed_resolutions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            before = graph.read_bytes()
            malformed = json.loads(resolutions.read_text(encoding="utf-8"))
            malformed["decisions"]["unknown:item"] = {"relation": "related"}
            resolutions.write_text(json.dumps(malformed), encoding="utf-8")
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
            after = graph.read_bytes()
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "incomplete-resolutions")
        self.assertEqual(after, before)

    def test_upgrade_refuses_preview_source_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            value = json.loads(preview.read_text(encoding="utf-8"))
            value["source"]["path"] = "../outside.json"
            value["previewHash"] = migration._preview_hash(value)
            preview.write_text(json.dumps(value), encoding="utf-8")
            resolution_value = json.loads(resolutions.read_text(encoding="utf-8"))
            resolution_value["previewHash"] = value["previewHash"]
            resolutions.write_text(json.dumps(resolution_value), encoding="utf-8")
            before = graph.read_bytes()
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
            after = graph.read_bytes()
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "unsafe-upgrade-path")
        self.assertEqual(after, before)

    def test_upgrade_backup_permission_failure_is_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            before = graph.read_bytes()
            real_open = transitions.os.open

            def fail_backup(path: str | Path, flags: int, mode: int = 0o777) -> int:
                if Path(path).name == "traceability.schema1.backup.json":
                    raise PermissionError("backup denied")
                return real_open(path, flags, mode)

            with mock.patch.object(
                transitions.os, "open", side_effect=fail_backup
            ):
                code, payload = migration.apply_upgrade(
                    root, "sample", preview, resolutions
                )
            after = graph.read_bytes()
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "backup-write")
        self.assertEqual(after, before)

    def test_upgrade_rejects_self_rehashed_preview_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            value = json.loads(preview.read_text(encoding="utf-8"))
            value["preservedNodes"][0]["status"] = "draft"
            value["previewHash"] = migration._preview_hash(value)
            preview.write_text(json.dumps(value), encoding="utf-8")
            resolution_value = json.loads(resolutions.read_text(encoding="utf-8"))
            resolution_value["previewHash"] = value["previewHash"]
            resolutions.write_text(json.dumps(resolution_value), encoding="utf-8")
            before = graph.read_bytes()
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
            after = graph.read_bytes()
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "changed-preview")
        self.assertEqual(after, before)

    def test_preview_cannot_alias_live_graph_or_semantic_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = ROOT / "tests" / "fixtures" / "state-v1-upgrade" / "ambiguous"
            shutil.copytree(fixture, root, dirs_exist_ok=True)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            artifact = root / "codeops" / "features" / "sample" / "artifact.md"
            graph_before = graph.read_bytes()
            artifact_before = artifact.read_bytes()
            graph_code, graph_payload = migration.make_preview(
                root, "sample", graph
            )
            source_code, source_payload = migration.make_preview(
                root, "sample", artifact
            )
            graph_after = graph.read_bytes()
            artifact_after = artifact.read_bytes()
        self.assertEqual(graph_code, 1, graph_payload)
        self.assertEqual(source_code, 1, source_payload)
        self.assertEqual(graph_before, graph_after)
        self.assertEqual(artifact_before, artifact_after)

    def test_idempotence_refuses_divergent_schema_two_destination(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
            self.assertEqual(code, 0, payload)
            graph = root / "codeops" / "features" / "sample" / "traceability.json"
            value = json.loads(graph.read_text(encoding="utf-8"))
            value["nodes"][0]["title"] = "Diverged"
            graph.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
        self.assertEqual(code, 1, payload)
        self.assertEqual(payload["blockers"][0]["code"], "divergent-destination")

    def test_upgrade_preserves_explicit_cross_feature_relation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fixture = ROOT / "tests" / "fixtures" / "state-v1-upgrade" / "ambiguous"
            shutil.copytree(fixture, root, dirs_exist_ok=True)
            sample_graph = root / "codeops" / "features" / "sample" / "traceability.json"
            sample = json.loads(sample_graph.read_text(encoding="utf-8"))
            sample["nodes"][0]["links"].append("identity/RD-001")
            sample_graph.write_text(json.dumps(sample, indent=2), encoding="utf-8")
            (root / "artifact.md").write_bytes(ARTIFACT)
            identity_path = root / "codeops" / "features" / "identity" / "traceability.json"
            identity_path.parent.mkdir(parents=True)
            identity = graph("approved")
            identity["feature"] = "identity"
            identity_path.write_text(
                json.dumps(identity, indent=2) + "\n", encoding="utf-8"
            )
            preview = root / "preview.json"
            code, preview_payload = migration.make_preview(
                root, "sample", preview
            )
            self.assertEqual(code, 0, preview_payload)
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
            template["decisions"]["edge:RD-001:identity/RD-001"] = {
                "relation": "depends-on"
            }
            resolutions = root / "resolutions.json"
            resolutions.write_text(json.dumps(template), encoding="utf-8")
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
            migrated = json.loads(sample_graph.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, payload)
        edges = migrated["nodes"][0]["edges"]
        self.assertIn(
            {"relation": "depends-on", "target": "identity/RD-001"}, edges
        )

    def test_prior_rollback_generation_does_not_block_new_apply_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root, preview, resolutions = self.make_upgrade(raw)
            preview_value = json.loads(preview.read_text(encoding="utf-8"))
            state = root / "codeops" / ".state-transactions"
            state.mkdir()
            old_operation = (
                "upgrade-sample-"
                + preview_value["previewHash"].split(":", 1)[-1][:16]
            )
            (state / f"{old_operation}.completed.json").write_text(
                json.dumps({
                    "schema": 1,
                    "operationId": old_operation,
                    "direction": "rollback",
                    "graphs": [],
                }),
                encoding="utf-8",
            )
            code, payload = migration.apply_upgrade(
                root, "sample", preview, resolutions
            )
        self.assertEqual(code, 0, payload)
        self.assertEqual(payload["result"], "committed")


if __name__ == "__main__":
    unittest.main()
