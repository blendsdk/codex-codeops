#!/usr/bin/env python3
"""Validate and summarize durable CodeOps project state using only the standard library."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


NODE_TYPES = {
    "requirement", "ambiguity", "decision", "invariant", "specification",
    "criterion", "test", "task", "implementation", "verification", "finding",
    "deferral",
}
RISK = {"low", "medium", "high", "critical"}
TERMINAL_AMBIGUITY = {"resolved", "deferred-approved"}
APPROVED_CONTENT = {"approved", "superseded"}
BLOCKING_FINDINGS = {"critical", "major"}
TASK_RE = re.compile(r"^\s*- \[(?P<mark>[ x~])\]\s+(?P<body>.+)$", re.MULTILINE)
STATUS_BY_TYPE = {
    "ambiguity": {"open", "resolved", "deferred-approved", "superseded"},
    "decision": {"approved", "superseded"},
    "deferral": {"proposed", "approved", "expired", "resolved", "rejected"},
    "requirement": {"draft", "approved", "stale", "superseded"},
    "specification": {"draft", "approved", "stale", "superseded"},
    "criterion": {"draft", "approved", "stale", "superseded"},
    "invariant": {"draft", "approved", "stale", "superseded"},
    "test": {"planned", "red-confirmed", "passing", "blocked", "stale", "superseded"},
    "task": {"pending", "implemented", "verified", "blocked", "stale", "superseded"},
    "implementation": {"present", "verified", "stale", "superseded", "reverted"},
    "verification": {"planned", "passing", "failing", "blocked", "stale", "superseded"},
    "finding": {"open", "accepted", "resolved", "superseded"},
}


@dataclass
class Problem:
    level: str
    source: Path
    message: str

    def render(self, root: Path) -> str:
        try:
            source = self.source.relative_to(root)
        except ValueError:
            source = self.source
        return f"{self.level}: {source}: {self.message}"


@dataclass
class Graph:
    source: Path
    feature: str
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)


def load_json(path: Path, problems: list[Problem]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        problems.append(Problem("ERROR", path, f"cannot parse JSON: {exc}"))
        return None
    if not isinstance(value, dict):
        problems.append(Problem("ERROR", path, "root must be a JSON object"))
        return None
    return value


def discover_graphs(root: Path) -> list[Path]:
    ignored = {".git", "node_modules", ".codex", ".agents", "_archive"}
    return sorted(
        path for path in root.rglob("traceability.json")
        if not any(part in ignored for part in path.relative_to(root).parts)
    )


def validate_config(root: Path, problems: list[Problem]) -> dict[str, Any] | None:
    path = root / "codeops" / "codeops.json"
    if not path.exists():
        return None
    data = load_json(path, problems)
    if data is None:
        return None
    allowed = {"schema", "mode", "artifacts", "quality", "routing", "metrics"}
    unknown = set(data) - allowed
    if unknown:
        problems.append(Problem("ERROR", path, f"unknown fields {sorted(unknown)}"))
    if data.get("schema") != 1:
        problems.append(Problem("ERROR", path, "schema must equal 1"))
    if data.get("mode") not in {"strict", "adaptive"}:
        problems.append(Problem("ERROR", path, "mode must be strict or adaptive"))
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, dict):
        problems.append(Problem("ERROR", path, "artifacts must be an object"))
    else:
        if artifacts.get("layout") not in {"nested", "flat"}:
            problems.append(Problem("ERROR", path, "artifacts.layout must be nested or flat"))
        artifact_root = artifacts.get("root")
        if not isinstance(artifact_root, str) or not artifact_root:
            problems.append(Problem("ERROR", path, "artifacts.root must be a non-empty string"))
    quality = data.get("quality", {})
    if not isinstance(quality, dict):
        problems.append(Problem("ERROR", path, "quality must be an object"))
    elif data.get("mode") == "strict" and quality.get("independentReview") is False:
        problems.append(Problem("ERROR", path, "strict mode cannot disable independent review"))
    metrics = data.get("metrics", {})
    if not isinstance(metrics, dict) or not isinstance(metrics.get("enabled", False), bool):
        problems.append(Problem("ERROR", path, "metrics.enabled must be boolean"))
    return data


def validate_node_shape(node: Any, source: Path, index: int, problems: list[Problem]) -> bool:
    if not isinstance(node, dict):
        problems.append(Problem("ERROR", source, f"nodes[{index}] must be an object"))
        return False
    required = {"id", "type", "title", "status", "path", "links"}
    allowed = required | {"evidence", "risk"}
    missing = required - set(node)
    unknown = set(node) - allowed
    if missing:
        problems.append(Problem("ERROR", source, f"nodes[{index}] missing {sorted(missing)}"))
    if unknown:
        problems.append(Problem("ERROR", source, f"nodes[{index}] has unknown fields {sorted(unknown)}"))
    if missing or unknown:
        return False
    if not isinstance(node["id"], str) or not re.fullmatch(r"[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+", node["id"]):
        problems.append(Problem("ERROR", source, f"nodes[{index}].id is invalid"))
        return False
    if node["type"] not in NODE_TYPES:
        problems.append(Problem("ERROR", source, f"{node['id']} has unknown type {node['type']!r}"))
    for key in ("title", "status", "path"):
        if not isinstance(node[key], str) or not node[key].strip():
            problems.append(Problem("ERROR", source, f"{node['id']}.{key} must be non-empty"))
    for key in ("links", "evidence"):
        value = node.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            problems.append(Problem("ERROR", source, f"{node['id']}.{key} must be an array of strings"))
    if "risk" in node and node["risk"] not in RISK:
        problems.append(Problem("ERROR", source, f"{node['id']}.risk is invalid"))
    allowed_statuses = STATUS_BY_TYPE.get(node["type"], set())
    if node["status"] not in allowed_statuses:
        problems.append(Problem(
            "ERROR", source,
            f"{node['id']}.status {node['status']!r} is invalid for {node['type']}; expected {sorted(allowed_statuses)}",
        ))
    return True


def load_graph(path: Path, project_root: Path, problems: list[Problem]) -> Graph | None:
    data = load_json(path, problems)
    if data is None:
        return None
    unknown = set(data) - {"schema", "feature", "updated", "nodes"}
    if unknown:
        problems.append(Problem("ERROR", path, f"unknown root fields {sorted(unknown)}"))
    if data.get("schema") != 1:
        problems.append(Problem("ERROR", path, "schema must equal 1"))
    feature = data.get("feature")
    if not isinstance(feature, str) or not feature.strip():
        problems.append(Problem("ERROR", path, "feature must be a non-empty string"))
        feature = path.parent.name
    nodes = data.get("nodes")
    if not isinstance(nodes, list):
        problems.append(Problem("ERROR", path, "nodes must be an array"))
        return Graph(path, feature)
    graph = Graph(path, feature)
    for index, node in enumerate(nodes):
        if not validate_node_shape(node, path, index, problems):
            continue
        node_id = node["id"]
        if node_id in graph.nodes:
            problems.append(Problem("ERROR", path, f"duplicate node id {node_id}"))
            continue
        graph.nodes[node_id] = node
        artifact = (path.parent / node["path"]).resolve()
        if project_root not in (artifact, *artifact.parents):
            problems.append(Problem("ERROR", path, f"{node_id}.path escapes the project root"))
        elif not artifact.exists():
            problems.append(Problem("ERROR", path, f"{node_id}.path does not exist: {node['path']}"))
    return graph


def validate_relationships(graphs: list[Graph], root: Path, problems: list[Problem]) -> dict[str, dict[str, Any]]:
    all_nodes: dict[str, dict[str, Any]] = {}
    owners: dict[str, Path] = {}
    for graph in graphs:
        for node_id, node in graph.nodes.items():
            if node_id in all_nodes:
                problems.append(Problem("ERROR", graph.source, f"node id {node_id} also exists in {owners[node_id]}"))
            else:
                all_nodes[node_id] = node
                owners[node_id] = graph.source
    for graph in graphs:
        for node_id, node in graph.nodes.items():
            for target in node.get("links", []):
                if target not in all_nodes:
                    problems.append(Problem("ERROR", graph.source, f"{node_id} links to missing node {target}"))
            for evidence in node.get("evidence", []):
                path = (graph.source.parent / evidence).resolve()
                if root not in (path, *path.parents):
                    problems.append(Problem("ERROR", graph.source, f"{node_id} evidence escapes project root: {evidence}"))
                elif not path.exists():
                    problems.append(Problem("ERROR", graph.source, f"{node_id} evidence is missing: {evidence}"))
    return all_nodes


def incoming(nodes: dict[str, dict[str, Any]]) -> dict[str, set[str]]:
    result = {node_id: set() for node_id in nodes}
    for source, node in nodes.items():
        for target in node.get("links", []):
            if target in result:
                result[target].add(source)
    return result


def coverage_problems(nodes: dict[str, dict[str, Any]], source: Path) -> list[Problem]:
    problems: list[Problem] = []
    reverse = incoming(nodes)

    def linked_type(node_id: str, allowed: set[str]) -> bool:
        references = set(nodes[node_id].get("links", [])) | reverse[node_id]
        return any(nodes[ref]["type"] in allowed for ref in references if ref in nodes)

    expectations = {
        "requirement": {"specification", "invariant", "criterion"},
        "specification": {"requirement", "criterion", "task"},
        "criterion": {"requirement", "specification", "test", "task", "verification"},
        "test": {"criterion"},
        "task": {"specification", "criterion", "implementation"},
        "implementation": {"task", "verification"},
        "verification": {"criterion", "implementation"},
    }
    for node_id, node in nodes.items():
        expected = expectations.get(node["type"])
        if expected and node["status"] != "superseded" and not linked_type(node_id, expected):
            problems.append(Problem("ERROR", source, f"{node_id} ({node['type']}) has no trace to {sorted(expected)}"))
    return problems


def readiness(nodes: dict[str, dict[str, Any]], source: Path) -> list[Problem]:
    problems = coverage_problems(nodes, source)
    for node_id, node in nodes.items():
        node_type = node["type"]
        status = node["status"]
        risk = node.get("risk", "high")
        if node_type == "ambiguity" and status not in TERMINAL_AMBIGUITY and risk in {"high", "critical"}:
            problems.append(Problem("BLOCK", source, f"material ambiguity {node_id} is {status}"))
        elif node_type == "deferral" and status != "approved":
            problems.append(Problem("BLOCK", source, f"deferral {node_id} is not approved"))
        elif node_type == "finding" and status == "open" and risk in BLOCKING_FINDINGS:
            problems.append(Problem("BLOCK", source, f"blocking finding {node_id} is open"))
        elif node_type in {"requirement", "specification", "criterion", "invariant"} and status not in APPROVED_CONTENT:
            problems.append(Problem("BLOCK", source, f"{node_type} {node_id} is not approved"))
    problems.extend(invalidation_problems(nodes, source))
    return problems


def invalidation_problems(nodes: dict[str, dict[str, Any]], source: Path) -> list[Problem]:
    """Require approved downstream work to become stale when an ambiguity reopens."""
    problems: list[Problem] = []
    stale_statuses = {"stale", "draft", "planned", "blocked", "superseded"}
    downstream_types = {
        "requirement", "specification", "invariant", "criterion", "test",
        "task", "implementation", "verification",
    }
    for ambiguity_id, ambiguity in nodes.items():
        if ambiguity["type"] != "ambiguity":
            continue
        if ambiguity["status"] in TERMINAL_AMBIGUITY or ambiguity.get("risk", "high") not in {"high", "critical"}:
            continue
        pending = list(ambiguity.get("links", []))
        visited: set[str] = set()
        while pending:
            node_id = pending.pop()
            if node_id in visited or node_id not in nodes:
                continue
            visited.add(node_id)
            node = nodes[node_id]
            if node["type"] in downstream_types and node["status"] not in stale_statuses:
                problems.append(Problem(
                    "BLOCK", source,
                    f"{node_id} must be marked stale because material ambiguity {ambiguity_id} is open",
                ))
            pending.extend(node.get("links", []))
    return problems


def feature_lifecycle(graph: Graph, ready: bool) -> str:
    feature_nodes = list(graph.nodes.values())
    types = {node["type"] for node in feature_nodes}
    tasks = [node for node in feature_nodes if node["type"] == "task"]
    findings = [node for node in feature_nodes if node["type"] == "finding" and node["status"] == "open"]
    if "requirement" not in types:
        return "discovery"
    if "specification" not in types and "invariant" not in types:
        return "requirements"
    if not tasks:
        return "planning"
    if any(node["status"] in {"implemented", "verified", "blocked"} for node in tasks):
        if all(node["status"] == "verified" for node in tasks):
            completion_types = {
                "test": {"passing", "superseded"},
                "implementation": {"present", "verified", "superseded"},
                "verification": {"passing", "superseded"},
            }
            complete = all(
                node["status"] in completion_types[node["type"]]
                for node in feature_nodes if node["type"] in completion_types
            )
            return "complete" if complete and not findings else "reviewing"
        return "executing"
    return "ready" if ready else "planning"


def git_drift(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


def execution_progress(root: Path) -> tuple[int, int, int]:
    pending = implemented = verified = 0
    for path in root.rglob("99-execution-plan.md"):
        relative_parts = path.relative_to(root).parts
        if ".git" in relative_parts or "_archive" in relative_parts:
            continue
        for match in TASK_RE.finditer(path.read_text(encoding="utf-8")):
            mark = match.group("mark")
            if mark == "x":
                verified += 1
            elif mark == "~":
                implemented += 1
            else:
                pending += 1
    return pending, implemented, verified


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "readiness", "status"))
    parser.add_argument("--root", default=".", help="project root (default: current directory)")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    problems: list[Problem] = []
    config = validate_config(root, problems)
    paths = discover_graphs(root)
    if not paths:
        problems.append(Problem("ERROR", root, "no traceability.json files found"))
    graphs = [graph for path in paths if (graph := load_graph(path, root, problems)) is not None]
    nodes = validate_relationships(graphs, root, problems)
    if args.command in {"readiness", "status"} and nodes:
        problems.extend(readiness(nodes, root))
    pending, implemented, verified = execution_progress(root)
    blocking = sum(problem.level in {"ERROR", "BLOCK"} for problem in problems)
    graph_status = []
    for graph in graphs:
        graph_ids = set(graph.nodes)
        graph_problems = [problem for problem in readiness(graph.nodes, graph.source)]
        graph_ready = not any(problem.level in {"ERROR", "BLOCK"} for problem in graph_problems)
        graph_status.append({
            "feature": graph.feature,
            "lifecycle": feature_lifecycle(graph, graph_ready),
            "ready": graph_ready,
            "nodes": len(graph_ids),
        })
    drift = git_drift(root)
    result = {
        "ready": blocking == 0,
        "configured": config is not None,
        "graphs": len(graphs),
        "nodes": len(nodes),
        "features": graph_status,
        "git_drift": drift,
        "problems": [problem.render(root) for problem in problems],
        "tasks": {"pending": pending, "implemented": implemented, "verified": verified},
    }
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"CodeOps graphs: {result['graphs']} | nodes: {result['nodes']}")
        print(f"Tasks: {pending} pending | {implemented} implemented | {verified} verified")
        for feature in graph_status:
            print(f"Feature {feature['feature']}: {feature['lifecycle']} | {'ready' if feature['ready'] else 'blocked'}")
        if drift:
            print(f"Git drift: {len(drift)} path(s)")
        for problem in problems:
            print(problem.render(root))
        print("READY" if result["ready"] else "NOT READY")
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
