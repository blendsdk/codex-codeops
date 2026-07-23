"""Normative target compatibility, gate predicates, and lifecycle summaries."""

from __future__ import annotations

from pathlib import Path

from .closure import Closure, build_closure
from .models import CONTRACT_MATURITIES, Node, StructuralProblem


TARGET_TYPES = {
    "requirements": {"requirement", "requirement-set"},
    "specifications": {"requirement", "specification", "invariant", "contract", "planning-group"},
    "plan": {"requirement", "task", "planning-group", "plan"},
    "audit": set(),
    "execution": {"plan"},
    "task-complete": {"task"},
    "feature-acceptance": {"feature"},
    "release": {"release"},
}

AUDIT_MAPPING = {
    "requirement": "requirements",
    "requirement-set": "requirements",
    "specification": "specifications",
    "invariant": "specifications",
    "contract": "specifications",
    "planning-group": "specifications",
    "criterion": "specifications",
    "plan": "execution",
    "test": "task-complete",
    "implementation": "task-complete",
    "verification": "task-complete",
    "ambiguity": "requirements",
    "decision": "requirements",
    "deferral": "requirements",
    "finding": "requirements",
    "feature": "feature-acceptance",
    "release": "release",
}


def audit_gate(node: Node) -> str:
    if node.node_type == "audit-artifact":
        return node.audit_stage or "requirements"
    if node.node_type == "task":
        return "plan" if node.status == "pending" else "task-complete"
    return AUDIT_MAPPING[node.node_type]


def compatibility_problem(gate: str, target: Node, source: Path) -> StructuralProblem | None:
    allowed = TARGET_TYPES.get(gate)
    if allowed is None:
        return StructuralProblem("unknown-gate", f"unknown gate {gate!r}", source, target.canonical_id)
    if gate == "audit" and target.node_type not in AUDIT_MAPPING and target.node_type not in {"task", "audit-artifact"}:
        return StructuralProblem(
            "incompatible-target",
            f"audit has no normative mapping for {target.node_type}",
            source,
            target.canonical_id,
        )
    if gate != "audit" and target.node_type not in allowed:
        return StructuralProblem(
            "incompatible-target",
            f"{gate} accepts target types {sorted(allowed)}; got {target.node_type}",
            source,
            target.canonical_id,
        )
    return None


def evaluate(
    gate: str,
    closure: Closure,
    nodes: dict[str, Node],
    sources: dict[str, Path],
) -> list[StructuralProblem]:
    problems: list[StructuralProblem] = []
    maturity = {value: index for index, value in enumerate(CONTRACT_MATURITIES)}
    for identity in closure.members:
        node = nodes[identity]
        required: set[str] = set()
        if node.status == "superseded":
            problems.append(
                StructuralProblem(
                    "superseded-evidence",
                    f"{identity} is superseded and cannot satisfy {gate}",
                    sources[identity],
                    identity,
                    {"path": closure.paths[identity]},
                )
            )
        if gate == "requirements":
            if node.node_type in {"requirement", "requirement-set", "criterion", "audit-artifact"}:
                required = {"approved"}
        elif gate == "specifications":
            if node.node_type in {"requirement", "specification", "invariant", "contract", "criterion", "planning-group", "audit-artifact"}:
                required = {"approved"}
        elif gate == "plan":
            if node.node_type in {"requirement", "specification", "invariant", "contract", "criterion", "planning-group", "plan", "audit-artifact"}:
                required = {"approved"}
            elif node.node_type == "task":
                required = {"pending"}
        elif gate == "execution":
            if node.node_type in {"plan", "specification", "invariant", "contract", "criterion"}:
                required = {"approved"}
            elif node.node_type == "task":
                required = {"pending", "implemented", "verified"}
            elif node.node_type == "test":
                required = {"planned", "red-confirmed", "passing"}
        elif gate == "task-complete":
            required = {
                "task": {"verified"},
                "test": {"passing"},
                "implementation": {"present", "verified"},
                "verification": {"passing"},
            }.get(node.node_type, set())
        elif gate in {"feature-acceptance", "release"}:
            if gate == "feature-acceptance" and node.node_type == "feature":
                required = {"approved"}
            elif gate == "release" and node.node_type == "release":
                required = {"approved"}
        if required and node.status not in required:
            problems.append(
                StructuralProblem(
                    "status-not-ready",
                    f"{identity} status {node.status!r} does not satisfy {gate}; expected {sorted(required)}",
                    sources[identity],
                    identity,
                    {"path": closure.paths[identity]},
                )
            )
        if node.node_type == "ambiguity" and (node.risk or "high") in {"high", "critical"} and node.status not in {"resolved", "deferred-approved"}:
            problems.append(StructuralProblem("material-ambiguity", f"{identity} is unresolved", sources[identity], identity, {"path": closure.paths[identity]}))
        if node.node_type == "finding" and (node.risk or "high") in {"high", "critical"} and node.status == "open":
            problems.append(StructuralProblem("blocking-finding", f"{identity} is open", sources[identity], identity, {"path": closure.paths[identity]}))
        if node.node_type == "deferral" and node.status != "approved":
            problems.append(StructuralProblem("unapproved-deferral", f"{identity} is {node.status}", sources[identity], identity, {"path": closure.paths[identity]}))
        if node.node_type == "decision" and node.status != "approved":
            problems.append(StructuralProblem("decision-not-current", f"{identity} is {node.status}", sources[identity], identity, {"path": closure.paths[identity]}))
        for edge in node.edges:
            if edge.relation == "consumes-contract" and edge.target in nodes:
                actual = nodes[edge.target].maturity or ""
                if maturity.get(actual, -1) < maturity.get(edge.required_maturity or "", 0):
                    problems.append(StructuralProblem("contract-maturity", f"{identity} requires {edge.required_maturity}; {edge.target} is {actual}", sources[identity], identity, {"path": closure.paths[identity] + (edge.target,)}))
    return problems


def evaluate_target(
    target: str,
    gate: str,
    nodes: dict[str, Node],
    sources: dict[str, Path],
    seen: frozenset[tuple[str, str]] = frozenset(),
) -> tuple[Closure, list[StructuralProblem]]:
    key = (target, gate)
    if key in seen:
        empty = build_closure(target, gate, nodes)
        return empty, [
            StructuralProblem(
                "composite-gate-cycle",
                f"recursive composite gate at {target} ({gate})",
                sources[target],
                target,
                {"path": (target,)},
            )
        ]
    closure = build_closure(target, gate, nodes)
    augmented_members = set(closure.members)
    augmented_paths = dict(closure.paths)
    evidence_additions: set[str] = set()
    if gate == "execution":
        for identity in closure.members:
            for edge in nodes[identity].edges:
                if edge.relation == "tested-by":
                    evidence_additions.add(edge.target)
    if gate == "task-complete":
        for owner_identity, owner in nodes.items():
            if any(
                edge.relation == "implemented-by" and edge.target == target
                for edge in owner.edges
            ):
                for edge in owner.edges:
                    if edge.relation in {"tested-by", "implemented-by", "verified-by"}:
                        evidence_additions.add(edge.target)
        for edge in nodes[target].edges:
            if edge.relation == "verified-by":
                evidence_additions.add(edge.target)
    for identity in sorted(evidence_additions):
        if identity in nodes:
            augmented_members.add(identity)
            augmented_paths.setdefault(identity, (target, identity))
    if augmented_members != set(closure.members):
        closure = Closure(
            tuple(sorted(augmented_members)),
            augmented_paths,
            closure.group_expansions,
            tuple(sorted(set(nodes) - augmented_members)),
        )
    problems = evaluate(gate, closure, nodes, sources)
    member_requests: list[tuple[str, str]] = []
    target_node = nodes[target]
    if gate == "feature-acceptance":
        member_requests.extend(
            (member, target_node.member_gates[member])
            for member in target_node.members
        )
    elif gate == "release":
        terminal_members = set(target_node.required)
        for identity in closure.members:
            for edge in nodes[identity].edges:
                if edge.relation == "release-coupled":
                    terminal_members.add(edge.target)
                    terminal_members.add(identity)
        terminal_members.discard(target)
        for member in sorted(terminal_members):
            member_type = nodes[member].node_type
            member_gate = {
                "feature": "feature-acceptance",
                "release": "release",
                "task": "task-complete",
                "plan": "execution",
                "requirement": "specifications",
                "requirement-set": "requirements",
                "specification": "specifications",
                "invariant": "specifications",
                "contract": "specifications",
            }.get(member_type, audit_gate(nodes[member]))
            member_requests.append((member, member_gate))
    merged_members = set(closure.members)
    merged_paths = dict(closure.paths)
    merged_groups = dict(closure.group_expansions)
    for member, member_gate in member_requests:
        member_node = nodes[member]
        internal_release_evidence = (
            gate == "release"
            and member_gate == "task-complete"
            and member_node.node_type in {"test", "implementation", "verification"}
        )
        incompatible = (
            None
            if internal_release_evidence
            else compatibility_problem(member_gate, member_node, sources[member])
        )
        if incompatible is not None:
            prefix = closure.paths.get(member, (target, member))
            problems.append(
                StructuralProblem(
                    incompatible.code,
                    incompatible.message,
                    incompatible.source,
                    incompatible.identity,
                    {"path": prefix},
                )
            )
            continue
        child, child_problems = evaluate_target(
            member, member_gate, nodes, sources, seen | {key}
        )
        if internal_release_evidence:
            terminal_status = {
                "test": "passing",
                "implementation": "verified",
                "verification": "passing",
            }[member_node.node_type]
            if member_node.status != terminal_status:
                child_problems.append(
                    StructuralProblem(
                        "release-terminal-evidence",
                        f"{member} must be {terminal_status} for release readiness",
                        sources[member],
                        member,
                        {"path": (member,)},
                    )
                )
        prefix = closure.paths.get(member, (target, member))
        for identity, path in child.paths.items():
            combined = prefix + path[1:] if path[0] == member else prefix + path
            prior = merged_paths.get(identity)
            if prior is None or (len(combined), combined) < (len(prior), prior):
                merged_paths[identity] = combined
        merged_members.update(child.members)
        merged_groups.update(child.group_expansions)
        for problem in child_problems:
            path = problem.details.get("path")
            details = dict(problem.details)
            if path:
                details["path"] = prefix + tuple(path)[1:]
            problems.append(
                StructuralProblem(
                    problem.code,
                    problem.message,
                    problem.source,
                    problem.identity,
                    details,
                )
            )
    merged = Closure(
        tuple(sorted(merged_members)),
        merged_paths,
        merged_groups,
        tuple(sorted(set(nodes) - merged_members)),
    )
    if gate == "plan" and target_node.node_type in {"requirement", "planning-group"}:
        owners = [
            node for node in nodes.values()
            if node.node_type == "plan"
            and any(
                edge.relation == "depends-on"
                and (
                    edge.target == target
                    or (
                        target_node.node_type == "planning-group"
                        and edge.target in target_node.members
                    )
                )
                for edge in node.edges
            )
        ]
        if not any(node.status == "approved" for node in owners):
            problems.append(StructuralProblem("approved-plan-required", f"{target} has no approved owning plan", sources[target], target, {"path": (target,)}))
    if gate == "execution":
        if not any(nodes[item].node_type == "test" and nodes[item].status in {"planned", "red-confirmed", "passing"} for item in merged.members):
            problems.append(StructuralProblem("planned-test-required", f"{target} has no planned test evidence", sources[target], target, {"path": (target,)}))
        if not target_node.evidence:
            problems.append(StructuralProblem("entry-evidence-required", f"{target} has no repository entry evidence", sources[target], target, {"path": (target,)}))
    return merged, problems


def lifecycle(node: Node) -> str:
    if node.node_type in {"requirement", "requirement-set"}:
        return "requirements"
    if node.node_type in {"specification", "invariant", "contract", "planning-group"}:
        return "specifications"
    if node.node_type == "plan":
        return "execution" if node.status == "approved" else "planning"
    if node.node_type == "task":
        return "complete" if node.status == "verified" else "execution"
    if node.node_type == "feature":
        return "acceptance"
    if node.node_type == "release":
        return "release"
    return "audit"


def valid_transitions(node: Node) -> list[str]:
    return {
        "draft": ["approved", "superseded"],
        "approved": ["stale", "superseded"],
        "stale": ["draft", "approved", "superseded"],
        "pending": ["implemented", "blocked"],
        "implemented": ["verified", "blocked", "stale"],
        "verified": ["stale", "superseded"],
    }.get(node.status, [])
