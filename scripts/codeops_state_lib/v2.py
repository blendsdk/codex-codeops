"""Schema-2 command orchestration used by the thin state CLI."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from .models import CONTRACT_MATURITIES, Edge, Graph, Node, StructuralProblem
from .schema import parse_graph_v2, validate_portfolio_v2


def discover_v2_graphs(root: Path) -> list[Path]:
    conventional = root / "codeops" / "features"
    if conventional.is_dir():
        return sorted(conventional.glob("*/traceability.json"))
    flat = root / "traceability.json"
    if flat.is_file():
        return [flat]
    return sorted(root.glob("*/traceability.json"))


def has_schema_two(root: Path) -> bool:
    for path in discover_v2_graphs(root):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("schema") == 2:
            return True
    return False


def _render_problem(problem: StructuralProblem, root: Path) -> str:
    try:
        source = problem.source.relative_to(root)
    except ValueError:
        source = problem.source
    return f"ERROR [{problem.code}]: {source}: {problem.message}"


def _load(root: Path) -> tuple[list[Graph], list[StructuralProblem]]:
    graphs: list[Graph] = []
    problems: list[StructuralProblem] = []
    for path in discover_v2_graphs(root):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(StructuralProblem("invalid-json", f"cannot parse JSON: {exc}", path))
            continue
        if not isinstance(raw, dict) or raw.get("schema") != 2:
            continue
        graph, graph_problems = parse_graph_v2(path, root)
        problems.extend(graph_problems)
        if graph is not None:
            graphs.append(graph)
    if not graphs and not problems:
        problems.append(StructuralProblem("no-graphs", "no schema-2 traceability graphs found", root))
    problems.extend(validate_portfolio_v2(graphs))
    return graphs, problems


def _resolve_target(
    target: str | None,
    feature: str | None,
    nodes: dict[str, Node],
    root: Path,
) -> tuple[str | None, list[StructuralProblem]]:
    if target is None:
        return None, []
    if "/" not in target:
        if feature is None:
            return None, [
                StructuralProblem(
                    "ambiguous-target",
                    f"bare target {target!r} is not canonical; use --target FEATURE/{target} or add --feature FEATURE",
                    root,
                )
            ]
        target = f"{feature}/{target}"
    elif feature is not None and target.split("/", 1)[0] != feature:
        return None, [
            StructuralProblem(
                "target-feature-mismatch",
                f"--feature {feature!r} conflicts with canonical target {target!r}",
                root,
            )
        ]
    if target not in nodes:
        return None, [StructuralProblem("target-not-found", f"target not found: {target}", root)]
    return target, []


def _closure(target: str, nodes: dict[str, Node]) -> tuple[list[str], dict[str, list[str]]]:
    groups: dict[str, list[str]] = {}
    group_by_member: dict[str, str] = {}
    for identity, node in nodes.items():
        if node.node_type == "planning-group":
            groups[identity] = list(node.members)
            for member in node.members:
                group_by_member[member] = identity
    selected: set[str] = set()
    pending = deque([target])
    while pending:
        identity = pending.popleft()
        if identity in selected:
            continue
        selected.add(identity)
        group = group_by_member.get(identity)
        if group is not None:
            pending.extend(groups[group])
        node = nodes[identity]
        for edge in node.edges:
            if edge.relation in {"depends-on", "consumes-contract"}:
                pending.append(edge.target)
    active_groups = {
        group: members
        for group, members in groups.items()
        if any(member in selected for member in members)
    }
    return sorted(selected), active_groups


def _readiness_problems(
    gate: str,
    closure: list[str],
    nodes: dict[str, Node],
    sources: dict[str, Path],
) -> list[StructuralProblem]:
    problems: list[StructuralProblem] = []
    maturity_rank = {value: index for index, value in enumerate(CONTRACT_MATURITIES)}
    for identity in closure:
        node = nodes[identity]
        if gate == "requirements" and node.node_type in {"requirement", "criterion"} and node.status != "approved":
            problems.append(
                StructuralProblem(
                    "status-not-approved",
                    f"{node.node_type} {identity} is not approved",
                    sources[identity],
                    identity,
                )
            )
        for edge in node.edges:
            if edge.relation != "consumes-contract" or edge.target not in nodes:
                continue
            contract = nodes[edge.target]
            if maturity_rank.get(contract.maturity or "", -1) < maturity_rank.get(edge.required_maturity or "", 0):
                problems.append(
                    StructuralProblem(
                        "contract-maturity",
                        f"{identity} requires {edge.required_maturity} contract maturity but {edge.target} is {contract.maturity}",
                        sources[identity],
                        identity,
                    )
                )
    return problems


def _base_result(
    graphs: list[Graph],
    problems: list[StructuralProblem],
    root: Path,
) -> dict[str, Any]:
    return {
        "ready": not problems,
        "schema_versions": sorted({graph.schema for graph in graphs}),
        "graphs": len(graphs),
        "nodes": sum(len(graph.nodes) for graph in graphs),
        "problems": [_render_problem(problem, root) for problem in problems],
    }


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "readiness", "status"))
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature")
    parser.add_argument("--target")
    parser.add_argument("--gate")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    graphs, problems = _load(root)
    nodes = {node.canonical_id: node for graph in graphs for node in graph.nodes}
    sources = {node.canonical_id: graph.source for graph in graphs for node in graph.nodes}
    target, target_problems = _resolve_target(args.target, args.feature, nodes, root)
    problems.extend(target_problems)
    closure: list[str] = []
    group_expansions: dict[str, list[str]] = {}
    if args.command == "readiness":
        if target is not None and args.gate is None:
            problems.append(StructuralProblem("gate-required", "--gate is required with a schema-2 target", root))
        if args.gate is not None and target is None and not target_problems:
            problems.append(StructuralProblem("target-required", "--target is required with a schema-2 gate", root))
    if target is not None and not problems:
        closure, group_expansions = _closure(target, nodes)
        if args.command == "readiness":
            problems.extend(_readiness_problems(args.gate, closure, nodes, sources))
    result = _base_result(graphs, problems, root)
    result.update(
        {
            "gate": args.gate,
            "target": target,
            "closure": closure,
            "group_expansions": group_expansions,
        }
    )
    result["ready"] = not problems
    if args.as_json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"CodeOps graphs: {result['graphs']} | nodes: {result['nodes']}")
        if target is not None:
            print(f"Target: {target}")
        if args.gate is not None:
            print(f"Gate: {args.gate}")
        for problem in result["problems"]:
            print(problem)
        print("READY" if result["ready"] else "NOT READY")
    if args.command == "status":
        structural_codes = {
            "invalid-json",
            "invalid-root",
            "schema-version",
            "duplicate-identity",
            "dependency-cycle",
        }
        return 1 if any(problem.code in structural_codes for problem in problems) else 0
    return 0 if result["ready"] else 1
