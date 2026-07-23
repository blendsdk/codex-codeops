"""Target, trace, dependency, planning-group, and release closure."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from .models import Node


TRACE_BY_GATE = {
    "requirements": {"accepted-by", "affected-by"},
    "specifications": {"specified-by", "accepted-by", "affected-by"},
    "plan": {"specified-by", "accepted-by", "affected-by"},
    "execution": {"specified-by", "accepted-by", "implemented-by", "affected-by"},
    "task-complete": {"tested-by", "implemented-by", "verified-by", "affected-by"},
}


@dataclass(frozen=True)
class Closure:
    members: tuple[str, ...]
    paths: dict[str, tuple[str, ...]]
    group_expansions: dict[str, tuple[str, ...]]
    excluded: tuple[str, ...]


def dependency_paths(target: str, nodes: dict[str, Node]) -> dict[str, tuple[str, ...]]:
    """Return real shortest paths, retaining dangling endpoint identities."""
    paths: dict[str, tuple[str, ...]] = {target: (target,)}
    pending = deque([target])
    while pending:
        identity = pending.popleft()
        node = nodes.get(identity)
        if node is None:
            continue
        additions = [
            edge.target
            for edge in node.edges
            if edge.relation in {"depends-on", "consumes-contract", "release-coupled"}
        ]
        if node.node_type in {"feature", "planning-group", "requirement-set"}:
            additions.extend(node.members)
        if node.node_type == "release":
            additions.extend(node.required)
        for addition in sorted(set(additions)):
            if addition in paths:
                continue
            paths[addition] = paths[identity] + (addition,)
            if addition in nodes:
                pending.append(addition)
    return paths


def build_closure(target: str, gate: str, nodes: dict[str, Node]) -> Closure:
    groups = {
        identity: tuple(node.members)
        for identity, node in nodes.items()
        if node.node_type == "planning-group"
    }
    group_by_member = {
        member: identity for identity, members in groups.items() for member in members
    }
    release_coupled: dict[str, set[str]] = {}
    if gate == "release":
        for identity, node in nodes.items():
            for edge in node.edges:
                if edge.relation == "release-coupled":
                    release_coupled.setdefault(identity, set()).add(edge.target)
                    release_coupled.setdefault(edge.target, set()).add(identity)
    paths: dict[str, tuple[str, ...]] = {target: (target,)}
    pending = deque([target])
    active_groups: dict[str, tuple[str, ...]] = {}
    while pending:
        identity = pending.popleft()
        node = nodes[identity]
        additions: list[str] = []
        group = group_by_member.get(identity)
        if group:
            active_groups[group] = groups[group]
            additions.extend(groups[group])
        additions.extend(
            edge.target
            for edge in node.edges
            if edge.relation in {"depends-on", "consumes-contract"}
            or edge.relation == "affected-by"
            or edge.relation in TRACE_BY_GATE.get(gate, set())
            or (gate == "release" and edge.relation == "release-coupled")
        )
        if gate == "release":
            additions.extend(release_coupled.get(identity, ()))
        if node.node_type == "requirement-set":
            additions.extend(node.members)
        if gate == "feature-acceptance" and identity == target:
            additions.extend(node.members)
        if gate == "release" and identity == target:
            additions.extend(node.required)
        for addition in sorted(set(additions)):
            if addition in paths:
                continue
            paths[addition] = paths[identity] + (addition,)
            if addition in nodes:
                pending.append(addition)
    members = tuple(sorted(paths))
    excluded = tuple(sorted(set(nodes) - set(members)))
    return Closure(members, paths, active_groups, excluded)


def build_scope_closure(
    target: str,
    gate: str,
    nodes: dict[str, Node],
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> Closure:
    """Build gate-aware structural scope, including recursive aggregate obligations."""
    key = (target, gate)
    base = build_closure(target, gate, nodes)
    if key in seen or target not in nodes:
        return base
    requests: list[tuple[str, str]] = []
    node = nodes[target]
    if gate == "feature-acceptance":
        requests.extend(
            (member, node.member_gates[member])
            for member in node.members
            if member in nodes
        )
    elif gate == "release":
        terminal = set(node.required)
        for identity in base.members:
            current = nodes.get(identity)
            if current is None:
                continue
            for edge in current.edges:
                if edge.relation == "release-coupled":
                    terminal.add(identity)
                    terminal.add(edge.target)
        terminal.discard(target)
        mapping = {
            "feature": "feature-acceptance",
            "release": "release",
            "task": "task-complete",
            "plan": "execution",
            "requirement": "specifications",
            "requirement-set": "requirements",
            "specification": "specifications",
            "invariant": "specifications",
            "contract": "specifications",
            "criterion": "specifications",
            "test": "task-complete",
            "implementation": "task-complete",
            "verification": "task-complete",
            "ambiguity": "requirements",
            "decision": "requirements",
            "deferral": "requirements",
            "finding": "requirements",
        }
        requests.extend(
            (member, mapping[nodes[member].node_type])
            for member in sorted(terminal)
            if member in nodes and nodes[member].node_type in mapping
        )
    members = set(base.members)
    paths = dict(base.paths)
    groups = dict(base.group_expansions)
    for member, member_gate in requests:
        child = build_scope_closure(member, member_gate, nodes, seen | {key})
        prefix = paths.get(member, (target, member))
        members.update(child.members)
        groups.update(child.group_expansions)
        for identity, path in child.paths.items():
            combined = prefix + path[1:] if path and path[0] == member else prefix + path
            prior = paths.get(identity)
            if prior is None or (len(combined), combined) < (len(prior), prior):
                paths[identity] = combined
    return Closure(
        tuple(sorted(members)),
        paths,
        groups,
        tuple(sorted(set(nodes) - members)),
    )
