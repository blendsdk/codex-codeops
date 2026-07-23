#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.codeops_state_lib import transitions
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


if __name__ == "__main__":
    unittest.main()
