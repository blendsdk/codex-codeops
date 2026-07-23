"""Lock-safe compare-and-swap transitions and explicit recovery."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from .discovery import discover_state
from .gates import compatibility_problem, evaluate_target
from .models import (
    Graph,
    Node,
    SemanticSource,
    SourceSelector,
    StructuralProblem,
)
from .rendering import problem_json
from .revisions import compute_revision
from .schema import parse_graph_v2, validate_portfolio_v2


CONTENT_TYPES = {
    "requirement",
    "requirement-set",
    "specification",
    "criterion",
    "invariant",
    "contract",
    "planning-group",
    "plan",
    "feature",
    "audit-artifact",
    "release",
}
SAFE_OPERATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
REQUEST_FIELDS = {
    "schema",
    "operationId",
    "target",
    "expected",
    "requested",
    "gate",
    "sourceUpdates",
    "validationAdditions",
    "validationRemovals",
    "staleReason",
    "evidence",
}


def _hash(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"cannot parse JSON: {exc}"
    if not isinstance(value, dict):
        return None, "JSON root must be an object"
    return value, None


def _load_v2(
    root: Path, refresh_target: str | None = None
) -> tuple[list[Graph], list[StructuralProblem]]:
    discovery = discover_state(root)
    graphs: list[Graph] = []
    problems: list[StructuralProblem] = list(discovery.problems)
    for path in discovery.paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(StructuralProblem("invalid-json", str(exc), path))
            continue
        if not isinstance(raw, dict) or raw.get("schema") != 2:
            continue
        parse_path = path
        temporary_path: Path | None = None
        feature = raw.get("feature")
        if (
            refresh_target is not None
            and isinstance(feature, str)
            and refresh_target.startswith(f"{feature}/")
            and isinstance(raw.get("nodes"), list)
        ):
            node_id = refresh_target.split("/", 1)[1]
            raw_node = next(
                (
                    item
                    for item in raw["nodes"]
                    if isinstance(item, dict) and item.get("id") == node_id
                ),
                None,
            )
            if raw_node is not None and isinstance(
                raw_node.get("semanticSources"), list
            ):
                try:
                    semantic_sources = tuple(
                        SemanticSource(
                            item["path"],
                            SourceSelector(
                                item["selector"]["kind"],
                                item["selector"].get("value"),
                            ),
                            item["normalization"],
                            item["digest"],
                        )
                        for item in raw_node["semanticSources"]
                    )
                    raw_node["revision"] = compute_revision(
                        root, semantic_sources
                    )
                    descriptor, temporary = tempfile.mkstemp(
                        prefix=f".{path.name}.refresh.",
                        suffix=".json",
                        dir=path.parent,
                    )
                    temporary_path = Path(temporary)
                    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                        json.dump(raw, handle)
                    parse_path = temporary_path
                except (KeyError, TypeError, ValueError, OSError, UnicodeError):
                    pass
        graph, graph_problems = parse_graph_v2(parse_path, root)
        if graph is not None and parse_path != path:
            graph = replace(graph, source=path)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        problems.extend(graph_problems)
        if graph is not None:
            graphs.append(graph)
    problems.extend(validate_portfolio_v2(graphs))
    return graphs, problems


def _allowed(node: Node, requested: str) -> bool:
    current = node.status
    if node.node_type in CONTENT_TYPES:
        return requested in {
            "draft": {"approved", "superseded"},
            "approved": {"stale", "superseded"},
            "stale": {"draft", "approved", "superseded"},
        }.get(current, set())
    return requested in {
        "test": {
            "planned": {"red-confirmed", "blocked"},
            "red-confirmed": {"passing", "blocked"},
            "passing": {"stale", "blocked"},
        },
        "task": {
            "pending": {"implemented", "blocked"},
            "implemented": {"verified", "blocked", "stale"},
            "verified": {"stale"},
        },
        "implementation": {
            "present": {"verified", "stale", "reverted"},
            "verified": {"stale", "reverted"},
        },
        "verification": {
            "planned": {"passing", "failing", "blocked"},
            "passing": {"stale"},
        },
        "ambiguity": {
            "open": {"resolved", "deferred-approved", "superseded"},
            "resolved": {"superseded"},
            "deferred-approved": {"resolved", "superseded"},
        },
        "finding": {
            "open": {"accepted", "resolved", "superseded"},
            "accepted": {"resolved", "superseded"},
            "resolved": {"superseded"},
        },
        "deferral": {
            "proposed": {"approved", "rejected"},
            "approved": {"expired", "resolved"},
            "expired": {"resolved"},
        },
    }.get(node.node_type, {}).get(current, set())


def _required_gate(node: Node, requested: str) -> str:
    if node.node_type in {"requirement", "requirement-set"}:
        return "requirements"
    if node.node_type in {
        "specification",
        "criterion",
        "invariant",
        "contract",
        "planning-group",
    }:
        return "specifications"
    if node.node_type == "plan":
        return "plan" if requested == "approved" else "execution"
    if node.node_type == "feature":
        return "feature-acceptance"
    if node.node_type == "release":
        return "release"
    if node.node_type == "task":
        return "plan" if node.status == "pending" and requested == "implemented" else "task-complete"
    if node.node_type in {"test", "implementation", "verification"}:
        return "task-complete"
    if node.node_type == "audit-artifact":
        return node.audit_stage or "requirements"
    return "requirements"


def _evidence_problem(node: Node, requested: str, request: dict[str, Any]) -> str | None:
    evidence = request["evidence"]
    if not isinstance(evidence, dict) or not all(
        isinstance(key, str) and isinstance(value, str) and value.strip()
        for key, value in evidence.items()
    ):
        return "evidence must be an object of non-empty string values"
    required: str | None = None
    if requested == "superseded":
        required = "replacement"
    elif requested == "blocked":
        required = "blocker"
    elif requested == "stale":
        required = "invalidation"
    elif node.status == "stale" and requested == "draft":
        required = "reopenDecision"
    elif node.node_type == "test" and requested == "red-confirmed":
        required = "redEvidence"
    elif node.node_type == "test" and requested == "passing":
        required = "greenEvidence"
    elif node.node_type == "task" and requested == "verified":
        required = "verificationEvidence"
    elif node.node_type == "implementation" and requested == "verified":
        required = "verificationEvidence"
    elif node.node_type == "implementation" and requested == "reverted":
        required = "rollbackEvidence"
    elif node.node_type == "verification" and requested in {"passing", "failing"}:
        required = "commandEvidence"
    elif node.node_type in {"ambiguity", "finding", "deferral"}:
        required = "userRuling"
    if required is not None and required not in evidence:
        return f"{node.status} -> {requested} requires evidence.{required}"
    if requested == "stale" and not request["staleReason"]:
        return "a stale transition requires staleReason"
    return None


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        try:
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            pass
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass


def _write_json(path: Path, value: dict[str, Any]) -> None:
    _atomic_write(
        path,
        (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )


def _sync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError:
        pass


def _process_identity(pid: int) -> dict[str, Any] | None:
    stat = Path(f"/proc/{pid}/stat")
    boot = Path("/proc/sys/kernel/random/boot_id")
    try:
        fields = stat.read_text(encoding="utf-8").split()
        return {
            "pid": pid,
            "startTicks": fields[21],
            "bootId": boot.read_text(encoding="utf-8").strip(),
        }
    except (OSError, IndexError):
        return None


def _owner_is_absent(owner: Any) -> bool | None:
    if not isinstance(owner, dict) or set(owner) != {"pid", "startTicks", "bootId"}:
        return None
    if (
        not isinstance(owner["pid"], int)
        or not isinstance(owner["startTicks"], str)
        or not isinstance(owner["bootId"], str)
    ):
        return None
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return None
    try:
        boot_id = (proc_root / "sys/kernel/random/boot_id").read_text(
            encoding="utf-8"
        ).strip()
    except OSError:
        return None
    if boot_id != owner["bootId"]:
        return True
    stat = proc_root / str(owner["pid"]) / "stat"
    try:
        fields = stat.read_text(encoding="utf-8").split()
    except FileNotFoundError:
        return True
    except OSError:
        return None
    try:
        return fields[21] != owner["startTicks"]
    except IndexError:
        return None


def _failure(
    root: Path,
    code: str,
    message: str,
    target: str | None = None,
    *,
    result: str = "refused",
    exit_code: int = 1,
    operation: str | None = None,
) -> tuple[int, dict[str, Any]]:
    problem = StructuralProblem(code, message, root, target)
    payload: dict[str, Any] = {
        "result": result,
        "target": target,
        "blockers": [problem_json(problem, root)],
    }
    if operation is not None:
        payload["operationId"] = operation
    return exit_code, payload


def _state_paths(root: Path, operation: str) -> tuple[Path, Path, Path, Path, Path]:
    state = root / "codeops" / ".state-transactions"
    return (
        state,
        state / f"{operation}.lock",
        state / f"{operation}.journal.json",
        state / f"{operation}.before",
        state / f"{operation}.after",
    )


def _validate_request(
    root: Path, request: dict[str, Any]
) -> tuple[str | None, str | None, str | None]:
    target = request.get("target")
    operation = request.get("operationId")
    if set(request) != REQUEST_FIELDS or request.get("schema") != 1:
        return None, target if isinstance(target, str) else None, "request fields or schema are invalid"
    if not isinstance(operation, str) or SAFE_OPERATION.fullmatch(operation) is None:
        return None, target if isinstance(target, str) else None, "operationId is not path-safe"
    expected = request.get("expected")
    requested = request.get("requested")
    if (
        not isinstance(target, str)
        or not isinstance(expected, dict)
        or set(expected) != {"status", "revision"}
        or not all(isinstance(expected.get(key), str) for key in ("status", "revision"))
        or not isinstance(requested, dict)
        or set(requested) != {"status"}
        or not isinstance(requested.get("status"), str)
        or not isinstance(request.get("gate"), str)
        or not isinstance(request.get("sourceUpdates"), list)
        or not isinstance(request.get("validationAdditions"), list)
        or not isinstance(request.get("validationRemovals"), list)
        or not isinstance(request.get("evidence"), dict)
        or (request.get("staleReason") is not None and not isinstance(request.get("staleReason"), str))
    ):
        return None, target if isinstance(target, str) else None, "request preconditions are incomplete"
    return operation, target, None


def _persisted_target_state(
    root: Path, target: str
) -> tuple[str, str] | None:
    feature, node_id = target.split("/", 1)
    for path in discover_state(root).paths:
        raw, _ = _read_json(path)
        if raw is None or raw.get("schema") != 2 or raw.get("feature") != feature:
            continue
        for item in raw.get("nodes", []):
            if (
                isinstance(item, dict)
                and item.get("id") == node_id
                and isinstance(item.get("status"), str)
                and isinstance(item.get("revision"), str)
            ):
                return item["status"], item["revision"]
    return None


def _project_raw(
    root: Path, raw: dict[str, Any], node: Node, request: dict[str, Any]
) -> bytes:
    raw_node = next(item for item in raw["nodes"] if item["id"] == node.node_id)
    raw_node["status"] = request["requested"]["status"]
    remove_keys = {
        (item.get("upstream"), item.get("relation"), item.get("gate"))
        for item in request["validationRemovals"]
        if isinstance(item, dict)
    }
    raw_node["validations"] = [
        item
        for item in raw_node["validations"]
        if (item.get("upstream"), item.get("relation"), item.get("gate"))
        not in remove_keys
    ] + request["validationAdditions"]
    for update in request["sourceUpdates"]:
        if not isinstance(update, dict) or set(update) != {"path"}:
            raise ValueError("sourceUpdates entries require only path")
        if not isinstance(update["path"], str):
            raise ValueError("sourceUpdates path must be a string")
        if update["path"] not in {item["path"] for item in raw_node["semanticSources"]}:
            raise ValueError(f"source update is not owned by target: {update['path']}")
    if request["sourceUpdates"]:
        raw_node["revision"] = compute_revision(root, node.semantic_sources)
    durable_evidence = [
        f"{key}:{value}" for key, value in sorted(request["evidence"].items())
    ]
    if durable_evidence:
        raw_node["evidence"] = sorted(
            set(raw_node.get("evidence", [])) | set(durable_evidence)
        )
    return (json.dumps(raw, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _parse_projected(
    path: Path, data: bytes, root: Path
) -> tuple[Graph | None, list[StructuralProblem]]:
    descriptor, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.projection.", suffix=".json", dir=path.parent
    )
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
        graph, problems = parse_graph_v2(temporary_path, root)
        return (replace(graph, source=path) if graph is not None else None), problems
    finally:
        temporary_path.unlink(missing_ok=True)


def _project_portfolio(
    root: Path,
    graphs: list[Graph],
    target: str,
    request: dict[str, Any],
) -> tuple[
    list[Graph],
    dict[Path, bytes],
    dict[Path, bytes],
    list[StructuralProblem],
]:
    nodes = {node.canonical_id: node for graph in graphs for node in graph.nodes}
    target_node = nodes[target]
    graph_by_identity = {
        node.canonical_id: graph for graph in graphs for node in graph.nodes
    }
    raw_by_path = {
        graph.source: json.loads(graph.source.read_text(encoding="utf-8"))
        for graph in graphs
    }
    target_graph = graph_by_identity[target]
    target_after = _project_raw(
        root, raw_by_path[target_graph.source], target_node, request
    )
    raw_by_path[target_graph.source] = json.loads(target_after.decode("utf-8"))

    invalidating = {
        "depends-on",
        "consumes-contract",
        "specified-by",
        "accepted-by",
        "tested-by",
        "implemented-by",
        "verified-by",
        "affected-by",
    }
    target_changed = (
        request["requested"]["status"] == "stale"
        or bool(request["sourceUpdates"])
    )
    if target_changed:
        pending = [target]
        invalidated = {target}
        while pending:
            changed = pending.pop(0)
            for identity, current in sorted(nodes.items()):
                owner_graph = graph_by_identity[identity]
                raw_owner = next(
                    item
                    for item in raw_by_path[owner_graph.source]["nodes"]
                    if item["id"] == current.node_id
                )
                release_edges = [
                    edge
                    for edge in current.edges
                    if edge.target == changed and edge.relation == "release-coupled"
                ]
                if release_edges:
                    raw_owner["validations"] = [
                        item
                        for item in raw_owner["validations"]
                        if not (
                            item.get("upstream") == changed
                            and item.get("relation") == "release-coupled"
                            and item.get("gate") == "release"
                        )
                    ]
                depends = any(
                    edge.target == changed and edge.relation in invalidating
                    for edge in current.edges
                )
                group_depends = (
                    current.node_type == "planning-group"
                    and changed in current.members
                )
                if not (depends or group_depends) or identity in invalidated:
                    continue
                if current.status not in {
                    "approved",
                    "implemented",
                    "verified",
                    "passing",
                }:
                    continue
                if "stale" not in {
                    "approved": {"stale"},
                    "implemented": {"stale"},
                    "verified": {"stale"},
                    "passing": {"stale"},
                }[current.status]:
                    continue
                raw_owner["status"] = "stale"
                invalidated.add(identity)
                pending.append(identity)

    before = {graph.source: graph.source.read_bytes() for graph in graphs}
    after = {
        path: (json.dumps(raw, indent=2, sort_keys=True) + "\n").encode("utf-8")
        for path, raw in raw_by_path.items()
        if (json.dumps(raw, indent=2, sort_keys=True) + "\n").encode("utf-8")
        != before[path]
    }
    projected: list[Graph] = []
    problems: list[StructuralProblem] = []
    for graph in graphs:
        data = after.get(graph.source, before[graph.source])
        parsed, parse_problems = _parse_projected(graph.source, data, root)
        problems.extend(parse_problems)
        if parsed is not None:
            projected.append(parsed)
    problems.extend(validate_portfolio_v2(projected))
    return projected, before, after, problems


def _rollback(
    committed: list[Path], before: dict[Path, bytes]
) -> bool:
    try:
        for path in reversed(committed):
            _atomic_write(path, before[path])
        return all(path.read_bytes() == before[path] for path in committed)
    except OSError:
        return False


def _evidence_transition_problems(
    target: str,
    node: Node,
    requested_status: str,
    nodes: dict[str, Node],
    sources: dict[str, Path],
) -> list[StructuralProblem]:
    terminal = {
        "test": "passing",
        "task": "verified",
        "implementation": "verified",
        "verification": "passing",
    }.get(node.node_type)
    if requested_status != terminal:
        return []
    if node.node_type == "task":
        owners = [target]
    else:
        relation = {
            "test": "tested-by",
            "implementation": "implemented-by",
            "verification": "verified-by",
        }[node.node_type]
        owners = sorted(
            identity
            for identity, owner in nodes.items()
            if any(
                edge.relation == relation and edge.target == target
                for edge in owner.edges
            )
        )
    if not owners:
        return [
            StructuralProblem(
                "transition-evidence",
                f"{target} has no owning task-complete closure",
                sources[target],
                target,
                {"path": (target,)},
            )
        ]
    if node.node_type != "task":
        return []
    problems: list[StructuralProblem] = []
    for owner in owners:
        incompatible = compatibility_problem(
            "task-complete", nodes[owner], sources[owner]
        )
        if incompatible is not None:
            problems.append(incompatible)
            continue
        _, owner_problems = evaluate_target(
            owner, "task-complete", nodes, sources
        )
        problems.extend(owner_problems)
    return problems


def transition(root: Path, request_path: Path) -> tuple[int, dict[str, Any]]:
    request, error = _read_json(request_path)
    if request is None:
        return _failure(root, "invalid-request", error or "invalid request")
    operation, target, error = _validate_request(root, request)
    if operation is None or target is None:
        return _failure(root, "invalid-request", error or "invalid request", target)

    state, lock, journal, before_path, after_path = _state_paths(root, operation)
    state.mkdir(parents=True, exist_ok=True)
    active_lock = state / "active.lock"
    completed = state / f"{operation}.completed.json"
    if completed.exists():
        return _failure(
            root,
            "operation-id-reused",
            f"operationId {operation} has a completed recovery record",
            target,
            operation=operation,
        )
    if journal.exists() or before_path.exists() or after_path.exists():
        return _failure(
            root,
            "recovery-required",
            f"operation {operation} has retained recovery state",
            target,
            result="recovery-required",
            exit_code=2,
            operation=operation,
        )
    nonce = uuid.uuid4().hex
    owner = _process_identity(os.getpid())
    if owner is None:
        return _failure(
            root,
            "owner-proof-unavailable",
            "this platform cannot record process start identity",
            target,
            operation=operation,
        )
    try:
        descriptor = os.open(
            lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
    except FileExistsError:
        return _failure(
            root,
            "transition-locked",
            f"transition lock exists: {lock.name}",
            target,
            operation=operation,
        )
    try:
        active_descriptor = os.open(
            active_lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
    except FileExistsError:
        os.close(descriptor)
        lock.unlink()
        return _failure(
            root,
            "transition-locked",
            "another transition owns the active writer lock",
            target,
            operation=operation,
        )

    preserve_recovery = False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "schema": 1,
                    "operationId": operation,
                    "nonce": nonce,
                    "owner": owner,
                },
                handle,
            )
            handle.flush()
            os.fsync(handle.fileno())
        _sync_directory(state)
        with os.fdopen(active_descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "schema": 1,
                    "operationId": operation,
                    "owner": owner,
                    "nonce": nonce,
                },
                handle,
                sort_keys=True,
            )
            handle.flush()
            os.fsync(handle.fileno())
        _sync_directory(state)

        persisted_state = _persisted_target_state(root, target)
        graphs, structural = _load_v2(
            root, target if request["sourceUpdates"] else None
        )
        if structural:
            return 1, {
                "result": "refused",
                "target": target,
                "operationId": operation,
                "blockers": [problem_json(problem, root) for problem in structural],
            }
        nodes = {node.canonical_id: node for graph in graphs for node in graph.nodes}
        sources = {
            node.canonical_id: graph.source for graph in graphs for node in graph.nodes
        }
        node = nodes.get(target)
        if node is None:
            return _failure(root, "target-not-found", f"target not found: {target}", target)
        graph = next(graph for graph in graphs if graph.feature == node.feature)
        expected = request["expected"]
        cas_status, cas_revision = (
            persisted_state
            if persisted_state is not None
            else (node.status, node.revision)
        )
        if cas_status != expected["status"] or cas_revision != expected["revision"]:
            return _failure(
                root,
                "compare-and-swap",
                "expected status or revision does not match",
                target,
                operation=operation,
            )
        requested_status = request["requested"]["status"]
        snapshot_refresh = (
            requested_status == node.status
            and bool(request["validationAdditions"] or request["validationRemovals"])
            and not request["sourceUpdates"]
        )
        if not _allowed(node, requested_status) and not snapshot_refresh:
            return _failure(
                root,
                "invalid-transition",
                f"{node.status} -> {requested_status} is not allowed for {node.node_type}",
                target,
                operation=operation,
            )
        evidence_error = (
            None
            if snapshot_refresh
            else _evidence_problem(node, requested_status, request)
        )
        if evidence_error is not None:
            return _failure(
                root,
                "transition-evidence",
                evidence_error,
                target,
                operation=operation,
            )
        replacement = request["evidence"].get("replacement")
        if (
            requested_status == "superseded"
            and (
                replacement not in nodes
                or replacement == target
                or nodes[replacement].node_type != node.node_type
                or nodes[replacement].status
                not in {"approved", "verified", "passing"}
            )
        ):
            return _failure(
                root,
                "transition-evidence",
                "replacement must name a distinct current canonical target",
                target,
                operation=operation,
            )
        required_gate = (
            request["gate"]
            if snapshot_refresh
            else _required_gate(node, requested_status)
        )
        if snapshot_refresh and any(
            not isinstance(item, dict) or item.get("gate") != required_gate
            for item in request["validationAdditions"] + request["validationRemovals"]
        ):
            return _failure(
                root,
                "invalid-transition-gate",
                "snapshot refresh entries must all use the requested governing gate",
                target,
                operation=operation,
            )
        if request["gate"] != required_gate:
            return _failure(
                root,
                "invalid-transition-gate",
                f"{node.node_type} {node.status} -> {requested_status} requires gate {required_gate}",
                target,
                operation=operation,
            )
        try:
            projected_graphs, before, after, projected_problems = _project_portfolio(
                root, graphs, target, request
            )
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            return _failure(
                root, "invalid-request", str(exc), target, operation=operation
            )
        if projected_problems:
            return 1, {
                "result": "refused",
                "target": target,
                "operationId": operation,
                "blockers": [
                    problem_json(problem, root) for problem in projected_problems
                ],
            }
        projected_nodes = {
            item.canonical_id: item
            for projected_graph in projected_graphs
            for item in projected_graph.nodes
        }
        projected_sources = {
            item.canonical_id: projected_graph.source
            for projected_graph in projected_graphs
            for item in projected_graph.nodes
        }
        approval = node.status in {"draft", "stale"} and requested_status == "approved"
        gate_nodes = projected_nodes if approval or snapshot_refresh else nodes
        gate_sources = projected_sources if approval or snapshot_refresh else sources
        gate_node = gate_nodes[target]
        evidence_routed = (
            node.node_type in {"test", "implementation", "verification"}
            or (
                node.node_type == "task"
                and not (
                    node.status == "pending"
                    and requested_status == "implemented"
                )
            )
        )
        if evidence_routed:
            gate_problems = _evidence_transition_problems(
                target,
                node,
                requested_status,
                projected_nodes,
                projected_sources,
            )
        else:
            incompatible = compatibility_problem(
                required_gate, gate_node, graph.source
            )
            gate_problems = (
                [incompatible]
                if incompatible is not None
                else evaluate_target(
                    target, required_gate, gate_nodes, gate_sources
                )[1]
            )
        if gate_problems:
            return 1, {
                "result": "refused",
                "target": target,
                "operationId": operation,
                "blockers": [
                    problem_json(problem, root) for problem in gate_problems
                ],
            }

        ordered_paths = sorted(after, key=lambda path: str(path.relative_to(root)))
        image_pairs: dict[Path, tuple[Path, Path]] = {}
        for index, path in enumerate(ordered_paths):
            before_image = state / f"{operation}.{index}.before"
            after_image = state / f"{operation}.{index}.after"
            _atomic_write(before_image, before[path])
            _atomic_write(after_image, after[path])
            image_pairs[path] = before_image, after_image
        journal_value = {
            "schema": 1,
            "operationId": operation,
            "lockNonce": nonce,
            "direction": None,
            "owner": owner,
            "graphs": [{
                "path": str(path.relative_to(root)),
                "beforeHash": _hash(before[path]),
                "afterHash": _hash(after[path]),
                "beforeImage": image_pairs[path][0].name,
                "afterImage": image_pairs[path][1].name,
                "committed": False,
            } for path in ordered_paths],
        }
        _write_json(journal, journal_value)
        committed_paths: list[Path] = []
        try:
            for index, path in enumerate(ordered_paths):
                _atomic_write(path, after[path])
                committed_paths.append(path)
                journal_value["graphs"][index]["committed"] = True
                _write_json(journal, journal_value)
            post_graphs, post_problems = _load_v2(root)
            if post_problems:
                raise ValueError("post-write portfolio validation failed")
            post_nodes = {
                item.canonical_id: item
                for post_graph in post_graphs
                for item in post_graph.nodes
            }
            post_sources = {
                item.canonical_id: post_graph.source
                for post_graph in post_graphs
                for item in post_graph.nodes
            }
            if approval or snapshot_refresh:
                _, post_gate_problems = evaluate_target(
                    target, required_gate, post_nodes, post_sources
                )
                if post_gate_problems:
                    raise ValueError("post-write governing gate validation failed")
            elif evidence_routed:
                post_gate_problems = _evidence_transition_problems(
                    target,
                    node,
                    requested_status,
                    post_nodes,
                    post_sources,
                )
                if post_gate_problems:
                    raise ValueError("post-write evidence gate validation failed")
        except Exception as exc:
            if _rollback(committed_paths, before):
                return _failure(
                    root,
                    "post-write-validation",
                    f"write was restored after failure: {exc}",
                    target,
                    operation=operation,
                )
            preserve_recovery = True
            return _failure(
                root,
                "post-write-validation",
                f"rollback could not be proven: {exc}",
                target,
                result="recovery-required",
                exit_code=2,
                operation=operation,
            )
        return 0, {
            "result": "committed",
            "operationId": operation,
            "target": target,
            "graphs": [
                {
                    "path": str(path.relative_to(root)),
                    "beforeHash": _hash(before[path]),
                    "afterHash": _hash(after[path]),
                }
                for path in ordered_paths
            ],
            "postWriteValidation": "passed",
            "blockers": [],
        }
    finally:
        if not preserve_recovery:
            recovery_images = list(state.glob(f"{operation}.*.before")) + list(
                state.glob(f"{operation}.*.after")
            )
            for path in (
                journal,
                before_path,
                after_path,
                lock,
                active_lock,
                *recovery_images,
            ):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass


def _safe_graph_path(root: Path, value: Any) -> Path | None:
    if not isinstance(value, str):
        return None
    candidate = (root / value).resolve()
    if candidate == root or root not in candidate.parents:
        return None
    return candidate


def _exclusive_recovery_lock(
    path: Path,
    operation: str,
    nonce: str,
) -> tuple[dict[str, Any] | None, str | None]:
    owner = _process_identity(os.getpid())
    if owner is None:
        return None, "recovery process identity is unavailable"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        existing, error = _read_json(path)
        if (
            existing is None
            or existing.get("operationId") != operation
            or existing.get("nonce") != nonce
        ):
            return None, error or "recovery lock belongs to another operation"
        if _owner_is_absent(existing.get("owner")) is not True:
            return None, "existing recovery owner absence is unproven"
        stale = path.with_name(f"{path.name}.stale-{uuid.uuid4().hex}")
        try:
            os.replace(path, stale)
            descriptor = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except OSError as exc:
            return None, f"cannot take over stale recovery lock: {exc}"
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "schema": 1,
                "operationId": operation,
                "nonce": nonce,
                "owner": owner,
            },
            handle,
            sort_keys=True,
        )
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory(path.parent)
    return owner, None


def _claim_active_lock(
    path: Path,
    operation: str,
    nonce: str,
    prior_owner: dict[str, Any],
    recovery_owner: dict[str, Any],
) -> tuple[Path | None, str | None]:
    stale_claim: Path | None = None
    existing, _ = _read_json(path)
    if existing is not None:
        if (
            existing.get("operationId") != operation
            or existing.get("nonce") != nonce
            or existing.get("owner") != prior_owner
        ):
            return None, "active writer lock belongs to another operation"
        stale_claim = path.with_name(f"{path.name}.stale-{uuid.uuid4().hex}")
        try:
            os.replace(path, stale_claim)
        except OSError as exc:
            return None, f"cannot quarantine stale active lock: {exc}"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return stale_claim, "a new writer acquired the active lock"
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "schema": 1,
                "mode": "recovery",
                "operationId": operation,
                "nonce": nonce,
                "owner": recovery_owner,
            },
            handle,
            sort_keys=True,
        )
        handle.flush()
        os.fsync(handle.fileno())
    _sync_directory(path.parent)
    return stale_claim, None


def _release_owned_lock(
    path: Path,
    operation: str,
    nonce: str,
    owner: dict[str, Any],
) -> None:
    value, _ = _read_json(path)
    if (
        value is not None
        and value.get("operationId") == operation
        and value.get("nonce") == nonce
        and value.get("owner") == owner
    ):
        path.unlink(missing_ok=True)


def recover(root: Path, request_path: Path) -> tuple[int, dict[str, Any]]:
    request, error = _read_json(request_path)
    if request is None:
        return _failure(root, "invalid-request", error or "invalid request")
    operation = request.get("operationId")
    direction = request.get("direction")
    if (
        request.get("schema") != 1
        or not isinstance(operation, str)
        or SAFE_OPERATION.fullmatch(operation) is None
        or direction not in {"roll-forward", "rollback"}
        or not isinstance(request.get("expectedLock"), str)
        or not isinstance(request.get("expectedOwner"), dict)
        or not isinstance(request.get("graphs"), list)
    ):
        return _failure(root, "invalid-request", "recovery request is invalid")
    state, lock, journal, before_path, after_path = _state_paths(root, operation)
    completed = state / f"{operation}.completed.json"
    completed_value, _ = _read_json(completed)
    if completed_value is not None:
        if (
            completed_value.get("direction") == direction
            and completed_value.get("graphs") == request["graphs"]
        ):
            return 0, {
                "result": "already-recovered",
                "operationId": operation,
                "direction": direction,
                "blockers": [],
            }
        return _failure(
            root,
            "recovery-direction-conflict",
            "completed recovery does not match this request",
            operation=operation,
        )
    lock_value, lock_error = _read_json(lock)
    if lock_value is None:
        return _failure(
            root,
            "recovery-state-not-found",
            lock_error or f"no lock for {operation}",
            operation=operation,
        )
    if lock_value.get("nonce") != request["expectedLock"]:
        return _failure(
            root,
            "recovery-lock-mismatch",
            "expected lock nonce does not match",
            operation=operation,
        )
    if lock_value.get("owner") != request["expectedOwner"]:
        return _failure(
            root,
            "recovery-owner-mismatch",
            "expected owner identity does not match the lock",
            operation=operation,
        )
    absent = _owner_is_absent(lock_value.get("owner"))
    if absent is not True:
        return _failure(
            root,
            "owner-absence-unproven",
            "recorded process absence cannot be proven",
            result="refused",
            operation=operation,
        )
    active_lock = state / "active.lock"
    active_value, _ = _read_json(active_lock)
    prior_active_owner = request["expectedOwner"]
    if active_value is not None:
        same_operation = (
            active_value.get("operationId") == operation
            and active_value.get("nonce") == request["expectedLock"]
        )
        recovery_resume = (
            same_operation
            and active_value.get("mode") == "recovery"
            and _owner_is_absent(active_value.get("owner")) is True
        )
        original_owner = (
            same_operation
            and active_value.get("owner") == request["expectedOwner"]
        )
        if not (recovery_resume or original_owner):
            return _failure(
                root,
                "active-lock-mismatch",
                "active writer lock belongs to another operation or live recovery",
                operation=operation,
            )
        prior_active_owner = active_value["owner"]
    recovery_lock = state / f"{operation}.recovery.lock"
    recovery_owner, recovery_error = _exclusive_recovery_lock(
        recovery_lock, operation, request["expectedLock"]
    )
    if recovery_owner is None:
        return _failure(
            root,
            "recovery-locked",
            recovery_error or "another recovery owns this operation",
            operation=operation,
        )
    stale_active, active_error = _claim_active_lock(
        active_lock,
        operation,
        request["expectedLock"],
        prior_active_owner,
        recovery_owner,
    )
    if active_error is not None:
        _release_owned_lock(
            recovery_lock,
            operation,
            request["expectedLock"],
            recovery_owner,
        )
        return _failure(
            root,
            "active-lock-mismatch",
            active_error,
            operation=operation,
        )

    def release_claim() -> None:
        _release_owned_lock(
            active_lock,
            operation,
            request["expectedLock"],
            recovery_owner,
        )
        _release_owned_lock(
            recovery_lock,
            operation,
            request["expectedLock"],
            recovery_owner,
        )
        if stale_active is not None:
            stale_active.unlink(missing_ok=True)

    journal_value, journal_error = _read_json(journal)
    if journal_value is None:
        if not request["graphs"] and not journal.exists():
            completed_payload = {
                "schema": 1,
                "operationId": operation,
                "direction": direction,
                "graphs": [],
            }
            _write_json(completed, completed_payload)
            lock.unlink(missing_ok=True)
            release_claim()
            return 0, {
                "result": "recovered",
                "operationId": operation,
                "direction": direction,
                "blockers": [],
            }
        release_claim()
        return _failure(
            root,
            "recovery-state-not-found",
            journal_error or f"no journal for {operation}",
            operation=operation,
        )
    if (
        journal_value.get("operationId") != operation
        or journal_value.get("lockNonce") != request["expectedLock"]
        or journal_value.get("owner") != request["expectedOwner"]
        or journal_value.get("schema") != 1
    ):
        release_claim()
        return _failure(
            root,
            "recovery-journal-mismatch",
            "journal identity does not match the recovery lock",
            operation=operation,
        )
    prior_direction = journal_value.get("direction")
    if prior_direction not in {None, direction}:
        release_claim()
        return _failure(
            root,
            "recovery-direction-conflict",
            "recovery direction cannot change after recovery starts",
            operation=operation,
        )
    journal_graphs = journal_value.get("graphs")
    if not isinstance(journal_graphs, list) or request["graphs"] != [
        {
            "path": item.get("path"),
            "beforeHash": item.get("beforeHash"),
            "afterHash": item.get("afterHash"),
        }
        for item in journal_graphs
        if isinstance(item, dict)
    ]:
        release_claim()
        return _failure(
            root,
            "recovery-hash-mismatch",
            "recovery graph hashes do not match the journal",
            operation=operation,
        )
    paths = [item.get("path") for item in journal_graphs if isinstance(item, dict)]
    images = [
        item.get(key)
        for item in journal_graphs
        if isinstance(item, dict)
        for key in ("beforeImage", "afterImage")
    ]
    valid_hash = re.compile(r"^sha256:[0-9a-f]{64}$")
    if (
        len(paths) != len(journal_graphs)
        or len(set(paths)) != len(paths)
        or len(set(images)) != len(images)
        or any(
            not isinstance(item, dict)
            or not isinstance(item.get("committed"), bool)
            or valid_hash.fullmatch(str(item.get("beforeHash"))) is None
            or valid_hash.fullmatch(str(item.get("afterHash"))) is None
            or any(
                not isinstance(item.get(key), str)
                or Path(item[key]).name != item[key]
                for key in ("beforeImage", "afterImage")
            )
            for item in journal_graphs
        )
    ):
        release_claim()
        return _failure(
            root,
            "invalid-recovery-journal",
            "journal graph records are not closed, unique, and hash-valid",
            operation=operation,
        )

    journal_value["direction"] = direction
    try:
        _write_json(journal, journal_value)
    except OSError as exc:
        release_claim()
        return _failure(
            root,
            "recovery-journal-write",
            f"cannot persist recovery direction: {exc}",
            operation=operation,
        )
    ordered = list(reversed(journal_graphs)) if direction == "rollback" else journal_graphs
    desired_key = "beforeHash" if direction == "rollback" else "afterHash"
    allowed_key = "afterHash" if direction == "rollback" else "beforeHash"
    image_key = "beforeImage" if direction == "rollback" else "afterImage"
    changed = False
    for item in ordered:
        graph_path = _safe_graph_path(root, item.get("path"))
        if graph_path is None or not graph_path.is_file():
            if not changed:
                release_claim()
            return _failure(
                root,
                "unsafe-recovery-path",
                "journal graph path is unsafe or missing",
                result="recovery-required" if changed else "refused",
                exit_code=2 if changed else 1,
                operation=operation,
            )
        image_name = item.get(image_key)
        if not isinstance(image_name, str) or Path(image_name).name != image_name:
            if not changed:
                release_claim()
            return _failure(
                root,
                "unsafe-recovery-path",
                "journal recovery image path is unsafe",
                result="recovery-required" if changed else "refused",
                exit_code=2 if changed else 1,
                operation=operation,
            )
        image_path = state / image_name
        if not image_path.is_file():
            if not changed:
                release_claim()
            return _failure(
                root,
                "recovery-image-missing",
                "journal recovery image is missing",
                result="recovery-required" if changed else "refused",
                exit_code=2 if changed else 1,
                operation=operation,
            )
        desired = image_path.read_bytes()
        current_hash = _hash(graph_path.read_bytes())
        if current_hash == item.get(desired_key):
            continue
        if current_hash != item.get(allowed_key) or _hash(desired) != item.get(desired_key):
            if not changed:
                release_claim()
            return _failure(
                root,
                "recovery-hash-mismatch",
                "current or recovery image hash is unexpected",
                result="recovery-required" if changed else "refused",
                exit_code=2 if changed else 1,
                operation=operation,
            )
        try:
            _atomic_write(graph_path, desired)
        except OSError as exc:
            return _failure(
                root,
                "recovery-write-failed",
                f"recovery write failed with retained state: {exc}",
                result="recovery-required",
                exit_code=2,
                operation=operation,
            )
        changed = True

    graphs, problems = _load_v2(root)
    if problems or not graphs:
        return _failure(
            root,
            "post-recovery-validation",
            "recovered portfolio did not validate",
            result="recovery-required",
            exit_code=2,
            operation=operation,
        )
    try:
        _write_json(
            completed,
            {
                "schema": 1,
                "operationId": operation,
                "direction": direction,
                "graphs": request["graphs"],
            },
        )
    except OSError as exc:
        return _failure(
            root,
            "recovery-completion-write",
            f"recovery completed but its durable record failed: {exc}",
            result="recovery-required",
            exit_code=2,
            operation=operation,
        )
    image_paths = {
        state / item[key]
        for item in journal_graphs
        for key in ("beforeImage", "afterImage")
        if isinstance(item, dict)
        and isinstance(item.get(key), str)
        and Path(item[key]).name == item[key]
    }
    release_claim()
    for path in (
        journal,
        lock,
        *image_paths,
    ):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    return 0, {
        "result": "recovered" if changed else "already-recovered",
        "operationId": operation,
        "direction": direction,
        "blockers": [],
    }
