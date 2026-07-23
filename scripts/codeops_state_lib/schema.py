"""Schema-2 parsing and structural graph validation."""

from __future__ import annotations

import json
import hashlib
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable

from .models import (
    AGGREGATE_TYPES,
    CONTRACT_MATURITIES,
    GATES,
    NODE_STATUSES,
    RELATIONS,
    Edge,
    Graph,
    Node,
    SemanticSource,
    SourceSelector,
    StructuralProblem,
    ValidationSnapshot,
)


FEATURE_RE = re.compile(r"^(?:[A-Za-z0-9]|_[A-Za-z0-9])[A-Za-z0-9._-]*$")
NODE_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$")
REVISION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CANONICAL_ID_RE = re.compile(
    r"^(?:[A-Za-z0-9]|_[A-Za-z0-9])[A-Za-z0-9._-]*/[A-Z][A-Z0-9]*-[A-Za-z0-9._-]+$"
)
NORMALIZATION = "utf8-lf-trim-trailing-v1"

GATEABLE_TYPES = frozenset(
    {
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
        "task",
    }
)

RELATION_MATRIX: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "specified-by": (
        frozenset({"requirement"}),
        frozenset({"specification", "invariant"}),
    ),
    "accepted-by": (
        frozenset({"requirement", "specification", "invariant", "contract"}),
        frozenset({"criterion"}),
    ),
    "tested-by": (frozenset({"criterion"}), frozenset({"test"})),
    "implemented-by": (
        frozenset({"specification", "criterion", "plan"}),
        frozenset({"task", "implementation"}),
    ),
    "verified-by": (
        frozenset({"criterion", "task", "implementation"}),
        frozenset({"verification"}),
    ),
    "affected-by": (
        frozenset(NODE_STATUSES) - frozenset({"ambiguity", "decision", "finding"}),
        frozenset({"ambiguity", "decision", "deferral", "finding"}),
    ),
    "depends-on": (GATEABLE_TYPES, GATEABLE_TYPES),
    "consumes-contract": (
        frozenset({"requirement", "specification", "plan", "task", "feature", "release"}),
        frozenset({"contract"}),
    ),
    "related": (frozenset(NODE_STATUSES), frozenset(NODE_STATUSES)),
    "release-coupled": (
        frozenset({"feature", "requirement", "contract", "release"}),
        frozenset({"feature", "requirement", "contract", "release"}),
    ),
}


def _problem(source: Path, code: str, message: str, identity: str | None = None) -> StructuralProblem:
    return StructuralProblem(code, message, source, identity)


def _safe_project_path(project_root: Path, value: str) -> Path | None:
    candidate = (project_root / value).resolve()
    root = project_root.resolve()
    return candidate if candidate == root or root in candidate.parents else None


def _normalized_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def _heading_section(text: str, heading: str) -> str | None:
    matches: list[tuple[int, int]] = []
    lines = text.splitlines()
    heading_re = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
    fence_re = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$")
    fence_character: str | None = None
    fence_length = 0
    for index, line in enumerate(lines):
        fence = fence_re.match(line)
        if fence is not None:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif (
                marker[0] == fence_character
                and len(marker) >= fence_length
                and not fence.group(2).strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue
        match = heading_re.fullmatch(line)
        if match is None:
            continue
        title = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2))
        if title == heading:
            matches.append((index, len(match.group(1))))
    if len(matches) != 1:
        return None
    start, level = matches[0]
    end = len(lines)
    fence_character = None
    fence_length = 0
    for index in range(start + 1, len(lines)):
        fence = fence_re.match(lines[index])
        if fence is not None:
            marker = fence.group(1)
            if fence_character is None:
                fence_character = marker[0]
                fence_length = len(marker)
            elif (
                marker[0] == fence_character
                and len(marker) >= fence_length
                and not fence.group(2).strip()
            ):
                fence_character = None
                fence_length = 0
            continue
        if fence_character is not None:
            continue
        match = heading_re.fullmatch(lines[index])
        if match is not None and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).rstrip("\n") + "\n"


def _source_revision(
    sources: tuple[SemanticSource, ...],
    graph_path: Path,
    project_root: Path,
) -> tuple[str | None, str | None]:
    selected: list[tuple[tuple[str, str, str], str]] = []
    for source in sources:
        resolved = _safe_project_path(project_root, source.path)
        if resolved is None or not resolved.is_file():
            return None, "source-selection"
        try:
            text = _normalized_text(resolved)
        except UnicodeDecodeError:
            return None, "source-not-utf8"
        if source.selector.kind == "heading":
            text = _heading_section(text, source.selector.value or "")
            if text is None:
                return None, "source-selection"
        selected.append(
            (
                (source.path, source.selector.kind, source.selector.value or ""),
                text,
            )
        )
    payload = "".join(text for _, text in sorted(selected))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest(), None


def _is_rfc3339_utc(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def _strings(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def parse_graph_v2(path: Path, project_root: Path) -> tuple[Graph | None, list[StructuralProblem]]:
    problems: list[StructuralProblem] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [_problem(path, "invalid-json", f"cannot parse JSON: {exc}")]
    if not isinstance(raw, dict):
        return None, [_problem(path, "invalid-root", "root must be a JSON object")]
    allowed_root = {"schema", "feature", "updated", "nodes"}
    unknown_root = set(raw) - allowed_root
    if unknown_root:
        problems.append(_problem(path, "unknown-field", f"unknown root fields {sorted(unknown_root)}"))
    if raw.get("schema") != 2:
        problems.append(_problem(path, "schema-version", "schema must equal 2"))
        return None, problems
    feature = raw.get("feature")
    if not isinstance(feature, str) or not FEATURE_RE.fullmatch(feature):
        problems.append(_problem(path, "invalid-feature", "feature is invalid"))
        return None, problems
    if "updated" in raw and not isinstance(raw["updated"], str):
        problems.append(_problem(path, "invalid-updated", "updated must be a string"))
    raw_nodes = raw.get("nodes")
    if not isinstance(raw_nodes, list):
        problems.append(_problem(path, "invalid-nodes", "nodes must be an array"))
        return Graph(2, feature, (), path, raw.get("updated")), problems

    nodes: list[Node] = []
    seen_ids: set[str] = set()
    for index, value in enumerate(raw_nodes):
        node, node_problems = _parse_node(value, feature, path, project_root, index)
        problems.extend(node_problems)
        if node is None:
            continue
        if node.node_id in seen_ids:
            problems.append(
                _problem(
                    path,
                    "duplicate-identity",
                    f"duplicate canonical identity {node.canonical_id}",
                    node.canonical_id,
                )
            )
            continue
        seen_ids.add(node.node_id)
        nodes.append(node)
    return Graph(2, feature, tuple(nodes), path, raw.get("updated")), problems


def _parse_node(
    raw: Any,
    feature: str,
    path: Path,
    project_root: Path,
    index: int,
) -> tuple[Node | None, list[StructuralProblem]]:
    problems: list[StructuralProblem] = []
    prefix = f"nodes[{index}]"
    if not isinstance(raw, dict):
        return None, [_problem(path, "invalid-node", f"{prefix} must be an object")]
    required = {
        "id",
        "type",
        "title",
        "status",
        "semanticSources",
        "revision",
        "edges",
        "validations",
    }
    optional = {
        "maturity",
        "members",
        "memberGates",
        "auditStage",
        "required",
        "optional",
        "excluded",
        "evidence",
        "risk",
    }
    missing = required - set(raw)
    unknown = set(raw) - required - optional
    if missing:
        problems.append(_problem(path, "missing-field", f"{prefix} missing {sorted(missing)}"))
    if unknown:
        problems.append(_problem(path, "unknown-field", f"{prefix} has unknown fields {sorted(unknown)}"))
    if missing or unknown:
        return None, problems
    node_id = raw["id"]
    node_type = raw["type"]
    identity = f"{feature}/{node_id}" if isinstance(node_id, str) else None
    if not isinstance(node_id, str) or not NODE_ID_RE.fullmatch(node_id):
        problems.append(_problem(path, "invalid-node-id", f"{prefix}.id is invalid", identity))
    if node_type not in NODE_STATUSES:
        problems.append(_problem(path, "invalid-node-type", f"{prefix}.type is invalid", identity))
    if not isinstance(raw["title"], str) or not raw["title"].strip():
        problems.append(_problem(path, "invalid-title", f"{prefix}.title must be non-empty", identity))
    if (
        node_type in NODE_STATUSES
        and (
            not isinstance(raw["status"], str)
            or raw["status"] not in NODE_STATUSES[node_type]
        )
    ):
        problems.append(
            _problem(
                path,
                "invalid-status",
                f"{identity}.status {raw['status']!r} is invalid for {node_type}",
                identity,
            )
        )
    if not isinstance(raw["revision"], str) or not REVISION_RE.fullmatch(raw["revision"]):
        problems.append(_problem(path, "invalid-revision", f"{identity}.revision is invalid", identity))

    sources = _parse_sources(raw["semanticSources"], path, project_root, identity, problems)
    edges = _parse_edges(raw["edges"], path, identity, problems)
    validations = _parse_validations(raw["validations"], path, identity, problems)
    members = _strings(raw.get("members", []))
    required_members = _strings(raw.get("required", []))
    optional_members = _strings(raw.get("optional", []))
    excluded_members = _strings(raw.get("excluded", []))
    evidence = _strings(raw.get("evidence", []))
    for field_name, parsed in (
        ("members", members),
        ("required", required_members),
        ("optional", optional_members),
        ("excluded", excluded_members),
        ("evidence", evidence),
    ):
        if parsed is None:
            problems.append(_problem(path, "invalid-field", f"{identity}.{field_name} must be an array of strings", identity))
    if problems or not isinstance(node_id, str) or node_type not in NODE_STATUSES:
        return None, problems
    member_gates = raw.get("memberGates", {})
    if not isinstance(member_gates, dict) or not all(
        isinstance(key, str) and value in {"task-complete", "feature-acceptance", "release"}
        for key, value in member_gates.items()
    ):
        problems.append(_problem(path, "invalid-member-gates", f"{identity}.memberGates is invalid", identity))
        member_gates = {}
    audit_stage = raw.get("auditStage")
    if node_type == "audit-artifact":
        allowed_stages = GATES - {"audit"}
        if audit_stage not in allowed_stages:
            problems.append(_problem(path, "invalid-audit-stage", f"{identity}.auditStage is required and must name a non-audit gate", identity))
    elif audit_stage is not None:
        problems.append(_problem(path, "invalid-audit-stage", f"{identity} may not carry auditStage", identity))
    if node_type == "release":
        missing_release = {"required", "optional", "excluded"} - set(raw)
        if missing_release:
            problems.append(_problem(path, "missing-release-members", f"{identity} missing {sorted(missing_release)}", identity))
    elif {"required", "optional", "excluded"} & set(raw):
        problems.append(_problem(path, "invalid-release-members", f"{identity} may not carry release membership", identity))
    if raw.get("risk") is not None and raw["risk"] not in {"low", "medium", "high", "critical"}:
        problems.append(_problem(path, "invalid-risk", f"{identity}.risk is invalid", identity))
    if evidence is not None and (
        any(not item for item in evidence) or len(set(evidence)) != len(evidence)
    ):
        problems.append(_problem(path, "invalid-evidence", f"{identity}.evidence must contain unique non-empty strings", identity))
    for field_name, values in (
        ("members", members),
        ("required", required_members),
        ("optional", optional_members),
        ("excluded", excluded_members),
    ):
        if values is not None and any(not CANONICAL_ID_RE.fullmatch(item) for item in values):
            problems.append(_problem(path, "invalid-identity", f"{identity}.{field_name} contains a non-canonical identity", identity))
    if problems:
        return None, problems
    computed_revision, source_error = _source_revision(sources, path, project_root)
    if computed_revision is None:
        if source_error == "source-not-utf8":
            problems.append(_problem(path, "source-not-utf8", f"{identity} semantic source is not valid UTF-8", identity))
        else:
            problems.append(_problem(path, "source-selection", f"{identity} source selector must match exactly one normalized ATX heading", identity))
        return None, problems
    if raw["revision"] != computed_revision:
        problems.append(_problem(path, "revision-mismatch", f"{identity}.revision does not match semantic sources", identity))
        return None, problems
    return (
        Node(
            feature=feature,
            node_id=node_id,
            node_type=node_type,
            title=raw["title"],
            status=raw["status"],
            semantic_sources=sources,
            revision=raw["revision"],
            edges=edges,
            validations=validations,
            maturity=raw.get("maturity"),
            members=members or (),
            member_gates=MappingProxyType(dict(sorted(member_gates.items()))),
            audit_stage=audit_stage,
            required=required_members or (),
            optional=optional_members or (),
            excluded=excluded_members or (),
            evidence=evidence or (),
            risk=raw.get("risk"),
        ),
        problems,
    )


def _parse_sources(
    raw: Any,
    graph_path: Path,
    project_root: Path,
    identity: str | None,
    problems: list[StructuralProblem],
) -> tuple[SemanticSource, ...]:
    if not isinstance(raw, list) or not raw:
        problems.append(_problem(graph_path, "invalid-sources", f"{identity}.semanticSources must be non-empty", identity))
        return ()
    result: list[SemanticSource] = []
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            problems.append(_problem(graph_path, "invalid-source", f"{identity}.semanticSources[{index}] is invalid", identity))
            continue
        selector = value.get("selector")
        selector_kind = selector.get("kind") if isinstance(selector, dict) else None
        selector_value = selector.get("value") if isinstance(selector, dict) else None
        valid_selector = selector_kind == "whole-file" and set(selector) == {"kind"}
        valid_selector |= (
            selector_kind == "heading"
            and isinstance(selector_value, str)
            and bool(selector_value)
            and set(selector) == {"kind", "value"}
        )
        source_path = value.get("path")
        if (
            set(value) != {"path", "selector", "normalization", "digest"}
            or not isinstance(source_path, str)
            or not source_path
            or not valid_selector
            or value.get("normalization") != NORMALIZATION
            or value.get("digest") != "sha256"
        ):
            problems.append(_problem(graph_path, "invalid-source", f"{identity}.semanticSources[{index}] is invalid", identity))
            continue
        resolved = _safe_project_path(project_root, source_path)
        if resolved is None:
            problems.append(_problem(graph_path, "path-escape", f"{identity} source escapes project root: {source_path}", identity))
        elif not resolved.is_file():
            problems.append(_problem(graph_path, "missing-source", f"{identity} source is missing: {source_path}", identity))
        result.append(
            SemanticSource(
                source_path,
                SourceSelector(selector_kind, selector_value),
                NORMALIZATION,
                "sha256",
            )
        )
    return tuple(result)


def _parse_edges(
    raw: Any,
    path: Path,
    identity: str | None,
    problems: list[StructuralProblem],
) -> tuple[Edge, ...]:
    if not isinstance(raw, list):
        problems.append(_problem(path, "invalid-edges", f"{identity}.edges must be an array", identity))
        return ()
    result: list[Edge] = []
    seen: set[tuple[str, str]] = set()
    inverse = {"blocks": "depends-on", "provides-contract": "consumes-contract"}
    for index, value in enumerate(raw):
        if not isinstance(value, dict):
            problems.append(_problem(path, "invalid-edge", f"{identity}.edges[{index}] is invalid", identity))
            continue
        relation = value.get("relation")
        target = value.get("target")
        if relation in inverse:
            problems.append(
                _problem(
                    path,
                    "persisted-inverse",
                    f"{identity} persists {relation}; store canonical relation {inverse[relation]}",
                    identity,
                )
            )
            continue
        allowed_fields = {"relation", "target", "requiredMaturity"}
        if (
            relation not in RELATIONS
            or not isinstance(target, str)
            or not CANONICAL_ID_RE.fullmatch(target)
            or set(value) - allowed_fields
        ):
            problems.append(_problem(path, "invalid-edge", f"{identity}.edges[{index}] is invalid", identity))
            continue
        maturity = value.get("requiredMaturity")
        if relation == "consumes-contract":
            if maturity not in CONTRACT_MATURITIES:
                problems.append(_problem(path, "invalid-maturity", f"{identity} consumes-contract requires valid requiredMaturity", identity))
        elif maturity is not None:
            problems.append(_problem(path, "invalid-maturity", f"{identity} may set requiredMaturity only on consumes-contract", identity))
        key = (relation, target)
        if key in seen:
            problems.append(_problem(path, "duplicate-edge", f"{identity} has duplicate {relation} edge to {target}", identity))
            continue
        seen.add(key)
        result.append(Edge(relation, target, maturity))
    return tuple(result)


def _parse_validations(
    raw: Any,
    path: Path,
    identity: str | None,
    problems: list[StructuralProblem],
) -> tuple[ValidationSnapshot, ...]:
    if not isinstance(raw, list):
        problems.append(_problem(path, "invalid-validations", f"{identity}.validations must be an array", identity))
        return ()
    result: list[ValidationSnapshot] = []
    seen: set[tuple[str, str, str]] = set()
    for index, value in enumerate(raw):
        required = {"upstream", "relation", "revision", "gate", "validatedAt"}
        if not isinstance(value, dict) or set(value) != required:
            problems.append(_problem(path, "invalid-validation", f"{identity}.validations[{index}] is invalid", identity))
            continue
        snapshot = ValidationSnapshot(
            value["upstream"],
            value["relation"],
            value["revision"],
            value["gate"],
            value["validatedAt"],
        )
        if (
            not isinstance(snapshot.upstream, str)
            or not CANONICAL_ID_RE.fullmatch(snapshot.upstream)
            or snapshot.relation not in {"depends-on", "consumes-contract", "release-coupled"}
            or not isinstance(snapshot.revision, str)
            or not REVISION_RE.fullmatch(snapshot.revision)
            or snapshot.gate not in GATES
            or not _is_rfc3339_utc(snapshot.validated_at)
        ):
            problems.append(_problem(path, "invalid-validation", f"{identity}.validations[{index}] is invalid", identity))
            continue
        if snapshot.key in seen:
            problems.append(_problem(path, "duplicate-validation", f"{identity} has duplicate validation {snapshot.key}", identity))
            continue
        seen.add(snapshot.key)
        result.append(snapshot)
    return tuple(sorted(result, key=lambda item: item.key))


def validate_portfolio_v2(graphs: Iterable[Graph]) -> list[StructuralProblem]:
    graph_list = list(graphs)
    problems: list[StructuralProblem] = []
    nodes: dict[str, Node] = {}
    owners: dict[str, Path] = {}
    for graph in graph_list:
        for node in graph.nodes:
            if node.canonical_id in nodes:
                problems.append(
                    _problem(
                        graph.source,
                        "duplicate-identity",
                        f"duplicate canonical identity {node.canonical_id}; first declared in {owners[node.canonical_id]}",
                        node.canonical_id,
                    )
                )
            else:
                nodes[node.canonical_id] = node
                owners[node.canonical_id] = graph.source
    group_owner: dict[tuple[str, str], str] = {}
    for node in nodes.values():
        problems.extend(_validate_node_semantics(node, nodes, owners[node.canonical_id], group_owner))
    problems.extend(_relationship_pair_problems(nodes, owners))
    problems.extend(_cycle_problems(nodes, owners))
    return problems


def _relationship_pair_problems(
    nodes: dict[str, Node],
    owners: dict[str, Path],
) -> list[StructuralProblem]:
    problems: list[StructuralProblem] = []
    symmetric_seen: dict[tuple[str, str, str], str] = {}
    for identity in sorted(nodes):
        for edge in nodes[identity].edges:
            if edge.relation not in {"related", "release-coupled"} or edge.target not in nodes:
                continue
            left, right = sorted((identity, edge.target))
            key = (edge.relation, left, right)
            prior = symmetric_seen.get(key)
            if prior is not None:
                problems.append(
                    _problem(
                        owners[identity],
                        "redundant-relationship",
                        f"{identity} redundantly stores reverse {edge.relation} relationship already owned by {prior}; store it once",
                        identity,
                    )
                )
            else:
                symmetric_seen[key] = identity
    return problems


def _validate_node_semantics(
    node: Node,
    nodes: dict[str, Node],
    source: Path,
    group_owner: dict[tuple[str, str], str],
) -> list[StructuralProblem]:
    problems: list[StructuralProblem] = []
    identity = node.canonical_id
    if node.node_type == "contract":
        if node.maturity not in CONTRACT_MATURITIES:
            problems.append(_problem(source, "invalid-maturity", f"{identity} requires contract maturity", identity))
    elif node.maturity is not None:
        problems.append(_problem(source, "invalid-maturity", f"{identity} may not carry maturity", identity))
    if node.node_type in AGGREGATE_TYPES:
        if not node.members or tuple(sorted(set(node.members))) != node.members:
            problems.append(_problem(source, "invalid-members", f"{identity}.members must be sorted, unique, and non-empty", identity))
    elif node.members:
        problems.append(_problem(source, "invalid-members", f"{identity} may not carry members", identity))
    if node.node_type == "feature":
        if set(node.member_gates) != set(node.members):
            problems.append(_problem(source, "invalid-member-gates", f"{identity}.memberGates must exactly cover members", identity))
    elif node.member_gates:
        problems.append(_problem(source, "invalid-member-gates", f"{identity} may not carry memberGates", identity))
    if node.node_type == "planning-group":
        for member in node.members:
            key = ("all", member)
            if key in group_owner:
                problems.append(_problem(source, "multiple-groups", f"{member} belongs to both {group_owner[key]} and {identity}", identity))
            group_owner[key] = identity
    release_sets = [set(node.required), set(node.optional), set(node.excluded)]
    if node.node_type == "release":
        for field_name, values in (
            ("required", node.required),
            ("optional", node.optional),
            ("excluded", node.excluded),
        ):
            if len(values) != len(set(values)):
                problems.append(
                    _problem(
                        source,
                        "duplicate-release-member",
                        f"{identity}.{field_name} must contain unique members",
                        identity,
                    )
                )
        overlap = (release_sets[0] & release_sets[1]) | (release_sets[0] & release_sets[2]) | (release_sets[1] & release_sets[2])
        if overlap:
            problems.append(_problem(source, "release-membership-conflict", f"{identity} has conflicting release members {sorted(overlap)}", identity))
    elif any(release_sets):
        problems.append(_problem(source, "invalid-release-members", f"{identity} may not carry release membership", identity))
    for member in (*node.members, *node.required, *node.optional, *node.excluded):
        if member not in nodes:
            problems.append(_problem(source, "missing-member", f"{identity} names missing member {member}", identity))
    for edge in node.edges:
        target = nodes.get(edge.target)
        if target is None:
            problems.append(_problem(source, "dangling-edge", f"{identity} {edge.relation} targets missing node {edge.target}", identity))
            continue
        if edge.target == identity:
            problems.append(_problem(source, "self-edge", f"{identity} has self {edge.relation} edge", identity))
            continue
        allowed_sources, allowed_targets = RELATION_MATRIX[edge.relation]
        if node.node_type not in allowed_sources or target.node_type not in allowed_targets:
            problems.append(
                _problem(
                    source,
                    "illegal-edge",
                    f"{identity} ({node.node_type}) {edge.relation} {edge.target} ({target.node_type}) is not allowed",
                    identity,
                )
            )
    return problems


def _cycle_problems(nodes: dict[str, Node], owners: dict[str, Path]) -> list[StructuralProblem]:
    group_by_member: dict[str, str] = {}
    for node in nodes.values():
        if node.node_type == "planning-group":
            for member in node.members:
                group_by_member[member] = node.canonical_id

    def vertex(identity: str) -> str:
        return group_by_member.get(identity, identity)

    adjacency: dict[str, set[str]] = defaultdict(set)
    for node in nodes.values():
        source_vertex = vertex(node.canonical_id)
        for edge in node.edges:
            if edge.relation not in {"depends-on", "consumes-contract"} or edge.target not in nodes:
                continue
            target_vertex = vertex(edge.target)
            if source_vertex != target_vertex:
                adjacency[source_vertex].add(target_vertex)
    state: dict[str, int] = {}
    stack: list[str] = []
    problems: list[StructuralProblem] = []

    def visit(current: str) -> bool:
        state[current] = 1
        stack.append(current)
        for target in sorted(adjacency[current]):
            if state.get(target, 0) == 0:
                if visit(target):
                    return True
            elif state.get(target) == 1:
                start = stack.index(target)
                cycle = stack[start:] + [target]
                owner_identity = cycle[0]
                problems.append(
                    _problem(
                        owners.get(owner_identity, next(iter(owners.values()))),
                        "dependency-cycle",
                        "blocking dependency cycle: " + " -> ".join(cycle),
                        owner_identity,
                    )
                )
                return True
        stack.pop()
        state[current] = 2
        return False

    for identity in sorted(set(nodes) | set(adjacency)):
        if state.get(identity, 0) == 0 and visit(identity):
            break
    return problems
