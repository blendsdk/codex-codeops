"""Version-aware command orchestration for CodeOps state."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import legacy
from .closure import build_scope_closure
from .discovery import discover_graphs, discover_state
from .gates import (
    TARGET_TYPES,
    audit_gate,
    compatibility_problem,
    evaluate_target,
    lifecycle,
    valid_transitions,
)
from .models import Graph, Node, StructuralProblem
from .migration import apply_upgrade, make_preview
from .rendering import problem_json, problem_text
from .schema import parse_graph_v2, validate_portfolio_v2
from .transitions import recover, transition


GLOBAL_CODES = {
    "invalid-config",
    "unsafe-config-root",
    "duplicate-identity",
    "ambiguous-target",
    "target-feature-mismatch",
}


@dataclass
class Loaded:
    graphs: list[Graph]
    problems: list[StructuralProblem]
    schema1_features: dict[str, set[str]]
    schema1_objects: dict[str, legacy.Graph]
    schema1_graphs: int
    schema1_nodes: int


def discover_v2_graphs(root: Path) -> list[Path]:
    return discover_graphs(root)


def has_schema_two(root: Path) -> bool:
    for path in discover_v2_graphs(root):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(value, dict) and value.get("schema") == 2:
            return True
    return False


def _load(root: Path) -> Loaded:
    discovery = discover_state(root)
    graphs: list[Graph] = []
    problems = list(discovery.problems)
    schema1_features: dict[str, set[str]] = {}
    schema1_graphs: list[legacy.Graph] = []
    source_features: dict[Path, str] = {}
    legacy_problems: list[legacy.Problem] = []
    if (root / "codeops" / "codeops.json").is_file():
        config_problems: list[legacy.Problem] = []
        legacy.validate_config(root, config_problems)
        problems.extend(
            StructuralProblem("invalid-config", problem.message, problem.source)
            for problem in config_problems
        )
    for path in discovery.paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append(StructuralProblem("invalid-json", f"cannot parse JSON: {exc}", path))
            continue
        if not isinstance(raw, dict):
            problems.append(StructuralProblem("invalid-root", "root must be an object", path))
            continue
        feature = raw.get("feature") if isinstance(raw.get("feature"), str) else path.parent.name
        source_features[path] = feature
        if raw.get("schema") == 1:
            graph = legacy.load_graph(path, root, legacy_problems)
            if graph is not None:
                schema1_graphs.append(graph)
                schema1_features[graph.feature] = set(graph.nodes)
            continue
        if raw.get("schema") != 2:
            problems.append(
                StructuralProblem(
                    "schema-version",
                    f"unsupported graph schema {raw.get('schema')!r}",
                    path,
                    details={"feature": feature},
                )
            )
            continue
        graph, graph_problems = parse_graph_v2(path, root)
        problems.extend(
            StructuralProblem(
                problem.code,
                problem.message,
                problem.source,
                problem.identity,
                {**dict(problem.details), "feature": feature},
            )
            for problem in graph_problems
        )
        if graph is not None:
            graphs.append(graph)
    if schema1_graphs:
        legacy.validate_relationships(schema1_graphs, root, legacy_problems)
    for problem in legacy_problems:
        feature = source_features.get(problem.source)
        problems.append(
            StructuralProblem(
                "schema1-invalid",
                problem.message,
                problem.source,
                details={"feature": feature, "schema": 1},
            )
        )
    for problem in validate_portfolio_v2(graphs):
        problems.append(
            StructuralProblem(
                problem.code,
                problem.message,
                problem.source,
                problem.identity,
                {
                    **dict(problem.details),
                    "feature": source_features.get(problem.source),
                },
            )
        )
    for graph in graphs:
        legacy_ids = schema1_features.get(graph.feature, set())
        for node in graph.nodes:
            if node.node_id in legacy_ids:
                problems.append(
                    StructuralProblem(
                        "duplicate-identity",
                        f"canonical identity {node.canonical_id} exists in both schema 1 and schema 2",
                        graph.source,
                        node.canonical_id,
                        {"feature": graph.feature},
                    )
                )
    if not graphs and not schema1_graphs and not problems:
        problems.append(StructuralProblem("no-graphs", "no live traceability graphs found", root))
    return Loaded(
        graphs,
        problems,
        schema1_features,
        {graph.feature: graph for graph in schema1_graphs},
        len(schema1_graphs),
        sum(len(graph.nodes) for graph in schema1_graphs),
    )


def _canonical_target(
    target: str | None,
    feature: str | None,
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
        return f"{feature}/{target}", []
    if feature is not None and target.split("/", 1)[0] != feature:
        return None, [
            StructuralProblem(
                "target-feature-mismatch",
                f"--feature {feature!r} conflicts with canonical target {target!r}",
                root,
            )
        ]
    return target, []


def _scope_problems(
    problems: list[StructuralProblem],
    target: str,
    paths: dict[str, tuple[str, ...]],
    root: Path,
) -> tuple[list[StructuralProblem], list[dict[str, Any]]]:
    entered_features = {identity.split("/", 1)[0] for identity in paths}
    blocking: list[StructuralProblem] = []
    diagnostics: list[dict[str, Any]] = []
    for problem in problems:
        feature = problem.details.get("feature")
        is_global = problem.code in GLOBAL_CODES or feature is None
        if not is_global and feature not in entered_features:
            diagnostics.append(problem_json(problem, root))
            continue
        details = dict(problem.details)
        if "path" not in details:
            if problem.identity in paths:
                details["path"] = paths[problem.identity]
            elif isinstance(feature, str):
                candidates = [
                    path for identity, path in paths.items()
                    if identity.split("/", 1)[0] == feature
                ]
                if candidates:
                    details["path"] = min(candidates, key=lambda item: (len(item), item))
        if problem.code == "dangling-edge":
            match = re.search(r"missing node (\S+)$", problem.message)
            if match is not None and match.group(1) in paths:
                details["path"] = paths[match.group(1)]
        blocking.append(
            StructuralProblem(
                problem.code,
                problem.message,
                problem.source,
                problem.identity,
                details,
            )
        )
    return blocking, diagnostics


def _stale_snapshots(target: Node, nodes: dict[str, Node]) -> list[dict[str, str]]:
    stale: list[dict[str, str]] = []
    for snapshot in target.validations:
        upstream = nodes.get(snapshot.upstream)
        actual = upstream.revision if upstream is not None else "missing"
        if actual != snapshot.revision:
            stale.append(
                {
                    "upstream": snapshot.upstream,
                    "relation": snapshot.relation,
                    "gate": snapshot.gate,
                    "expected": snapshot.revision,
                    "actual": actual,
                }
            )
    return stale


def _base_result(loaded: Loaded, problems: list[StructuralProblem], root: Path) -> dict[str, Any]:
    versions = ({2} if loaded.graphs else set()) | ({1} if loaded.schema1_graphs else set())
    return {
        "ready": not problems,
        "schema_versions": sorted(versions),
        "graphs": len(loaded.graphs) + loaded.schema1_graphs,
        "nodes": sum(len(graph.nodes) for graph in loaded.graphs) + loaded.schema1_nodes,
        "problems": [problem_text(problem, root) for problem in problems],
    }


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "validate",
            "readiness",
            "status",
            "transition",
            "transition-recover",
            "traceability-upgrade",
        ),
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--feature")
    parser.add_argument("--target")
    parser.add_argument("--gate")
    parser.add_argument("--request")
    parser.add_argument("--preview")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--resolutions")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.command == "traceability-upgrade":
        if args.feature is None or args.preview is None:
            parser.error("traceability-upgrade requires --feature and --preview")
        preview_path = Path(args.preview)
        if not preview_path.is_absolute():
            preview_path = (Path.cwd() / preview_path).resolve()
        if args.apply:
            if args.resolutions is None:
                parser.error("traceability-upgrade --apply requires --resolutions")
            resolutions_path = Path(args.resolutions)
            if not resolutions_path.is_absolute():
                resolutions_path = (Path.cwd() / resolutions_path).resolve()
            code, result = apply_upgrade(
                root, args.feature, preview_path, resolutions_path
            )
        else:
            code, result = make_preview(root, args.feature, preview_path)
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{result['result']}: {result.get('feature', args.feature)}")
            for blocker in result.get("blockers", []):
                if isinstance(blocker, dict):
                    print(f"{blocker['code']}: {blocker['message']}")
                else:
                    print(blocker)
        return code
    if args.command in {"transition", "transition-recover"}:
        if args.request is None:
            parser.error(f"{args.command} requires --request")
        request_path = Path(args.request)
        if not request_path.is_absolute():
            request_path = (Path.cwd() / request_path).resolve()
        code, result = (
            transition(root, request_path)
            if args.command == "transition"
            else recover(root, request_path)
        )
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print(f"{result['result']}: {result.get('target') or result.get('operationId', '')}")
            for blocker in result.get("blockers", []):
                print(f"{blocker['code']}: {blocker['message']}")
        return code
    loaded = _load(root)
    nodes = {node.canonical_id: node for graph in loaded.graphs for node in graph.nodes}
    sources = {node.canonical_id: graph.source for graph in loaded.graphs for node in graph.nodes}
    target, target_problems = _canonical_target(args.target, args.feature, root)
    problems = list(loaded.problems) + target_problems
    diagnostics: list[dict[str, Any]] = []
    closure_members: list[str] = []
    groups: dict[str, list[str]] = {}
    blockers: list[dict[str, Any]] = []
    status_gate_results: dict[str, dict[str, Any]] = {}

    if target is None and args.feature in loaded.schema1_features and args.gate is None:
        graph = loaded.schema1_objects[args.feature]
        legacy_gate_problems = legacy.readiness(graph.nodes, graph.source)
        converted = [
            StructuralProblem("schema1-readiness", problem.message, problem.source)
            for problem in legacy_gate_problems
        ]
        result = _base_result(loaded, converted, root)
        result.update(
            {
                "selected_feature": args.feature,
                "features": [{
                    "feature": graph.feature,
                    "lifecycle": legacy.feature_lifecycle(graph, not converted),
                    "ready": not converted,
                    "nodes": len(graph.nodes),
                }],
                "blockers": [problem_json(problem, root) for problem in converted],
                "diagnostics": [],
            }
        )
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print("READY" if result["ready"] else "NOT READY")
        return 0 if args.command == "status" or result["ready"] else 1
    if target is not None:
        target_feature, target_id = target.split("/", 1)
        if target_id in loaded.schema1_features.get(target_feature, set()):
            problems = [
                StructuralProblem(
                    "upgrade-required",
                    f"typed target readiness requires schema 2; run traceability-upgrade preview for feature {target_feature}",
                    root,
                    target,
                    {"feature": target_feature, "schema": 1},
                )
            ]
        else:
            paths: dict[str, tuple[str, ...]] = {target: (target,)}
            if target in nodes:
                target_node = nodes[target]
                scope_gates: list[str] = []
                if args.command == "readiness" and args.gate is not None:
                    if compatibility_problem(args.gate, target_node, sources[target]) is None:
                        scope_gates.append(
                            audit_gate(target_node) if args.gate == "audit" else args.gate
                        )
                elif args.command == "status":
                    for gate, accepted in TARGET_TYPES.items():
                        if gate == "audit" or target_node.node_type in accepted:
                            scope_gates.append(
                                audit_gate(target_node) if gate == "audit" else gate
                            )
                for scope_gate in sorted(set(scope_gates)):
                    scoped = build_scope_closure(target, scope_gate, nodes)
                    for identity, path in scoped.paths.items():
                        prior = paths.get(identity)
                        if prior is None or (len(path), path) < (len(prior), prior):
                            paths[identity] = path
            problems, diagnostics = _scope_problems(problems, target, paths, root)
            for identity, path in paths.items():
                feature_name, node_id = identity.split("/", 1)
                if node_id in loaded.schema1_features.get(feature_name, set()):
                    problems.append(
                        StructuralProblem(
                            "upgrade-required",
                            f"dependency {identity} uses schema 1 and must be upgraded before typed readiness",
                            root,
                            identity,
                            {"feature": feature_name, "schema": 1, "path": path},
                        )
                    )
            if target not in nodes and not any(
                problem.details.get("feature") == target_feature for problem in problems
            ):
                problems.append(
                    StructuralProblem("target-not-found", f"target not found: {target}", root)
                )
    if args.command == "readiness":
        if target is not None and args.gate is None:
            problems.append(StructuralProblem("gate-required", "--gate is required with a schema-2 target", root))
        if args.gate is not None and target is None and not target_problems:
            problems.append(StructuralProblem("target-required", "--target is required with a schema-2 gate", root))

    gate_problems: list[StructuralProblem] = []
    if target is not None and target in nodes and not problems:
        target_node = nodes[target]
        if args.command == "readiness" and args.gate is not None:
            incompatible = compatibility_problem(args.gate, target_node, sources[target])
            if incompatible is not None:
                gate_problems.append(incompatible)
            else:
                effective = audit_gate(target_node) if args.gate == "audit" else args.gate
                closure, gate_problems = evaluate_target(target, effective, nodes, sources)
                closure_members = list(closure.members)
                groups = {key: list(value) for key, value in closure.group_expansions.items()}
        elif args.command == "status":
            for gate, accepted in TARGET_TYPES.items():
                if gate != "audit" and target_node.node_type not in accepted:
                    continue
                effective = audit_gate(target_node) if gate == "audit" else gate
                closure, verdict_problems = evaluate_target(target, effective, nodes, sources)
                status_gate_results[gate] = {
                    "ready": not verdict_problems,
                    "blockers": [problem_json(problem, root) for problem in verdict_problems],
                }
                closure_members = sorted(set(closure_members) | set(closure.members))
                groups.update({key: list(value) for key, value in closure.group_expansions.items()})
            gate_problems = [
                problem
                for result in status_gate_results.values()
                for problem in ()
            ]
    problems.extend(gate_problems)
    blockers = [problem_json(problem, root) for problem in problems]
    result = _base_result(loaded, problems, root)
    result.update(
        {
            "gate": args.gate,
            "target": target,
            "closure": closure_members,
            "group_expansions": groups,
            "blockers": blockers,
            "diagnostics": diagnostics,
        }
    )
    if target is not None and target in nodes and args.command == "status":
        target_node = nodes[target]
        all_gate_blockers = [
            blocker
            for summary in status_gate_results.values()
            for blocker in summary["blockers"]
        ]
        result.update(
            {
                "ready": bool(status_gate_results) and all(
                    summary["ready"] for summary in status_gate_results.values()
                ),
                "status": target_node.status,
                "lifecycle": lifecycle(target_node),
                "revision": target_node.revision,
                "stale_snapshots": _stale_snapshots(target_node, nodes),
                "valid_transitions": valid_transitions(target_node),
                "gates": status_gate_results,
                "blockers": all_gate_blockers,
            }
        )
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
        return 1 if problems else 0
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(run(sys.argv[1:]))
