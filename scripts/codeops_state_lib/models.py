"""Immutable domain models shared by CodeOps state commands."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping


GATES = frozenset(
    {
        "requirements",
        "specifications",
        "plan",
        "audit",
        "execution",
        "task-complete",
        "feature-acceptance",
        "release",
    }
)

NODE_STATUSES: Mapping[str, frozenset[str]] = {
    node_type: frozenset({"draft", "approved", "stale", "superseded"})
    for node_type in (
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
    )
}
NODE_STATUSES = {
    **NODE_STATUSES,
    "ambiguity": frozenset({"open", "resolved", "deferred-approved", "superseded"}),
    "decision": frozenset({"approved", "stale", "superseded"}),
    "deferral": frozenset(
        {"proposed", "approved", "expired", "resolved", "rejected"}
    ),
    "test": frozenset(
        {"planned", "red-confirmed", "passing", "blocked", "stale", "superseded"}
    ),
    "task": frozenset(
        {"pending", "implemented", "verified", "blocked", "stale", "superseded"}
    ),
    "implementation": frozenset(
        {"present", "verified", "stale", "superseded", "reverted"}
    ),
    "verification": frozenset(
        {"planned", "passing", "failing", "blocked", "stale", "superseded"}
    ),
    "finding": frozenset({"open", "accepted", "resolved", "superseded"}),
}

RELATIONS = frozenset(
    {
        "specified-by",
        "accepted-by",
        "tested-by",
        "implemented-by",
        "verified-by",
        "affected-by",
        "depends-on",
        "consumes-contract",
        "related",
        "release-coupled",
    }
)

CONTRACT_MATURITIES = ("provisional", "stable", "frozen")
AGGREGATE_TYPES = frozenset({"requirement-set", "feature", "planning-group"})


@dataclass(frozen=True, slots=True)
class SourceSelector:
    kind: str
    value: str | None = None


@dataclass(frozen=True, slots=True)
class SemanticSource:
    path: str
    selector: SourceSelector
    normalization: str
    digest: str


@dataclass(frozen=True, slots=True)
class Edge:
    relation: str
    target: str
    required_maturity: str | None = None


@dataclass(frozen=True, slots=True)
class ValidationSnapshot:
    upstream: str
    relation: str
    revision: str
    gate: str
    validated_at: str

    @property
    def key(self) -> tuple[str, str, str]:
        return self.upstream, self.relation, self.gate


@dataclass(frozen=True, slots=True)
class Node:
    feature: str
    node_id: str
    node_type: str
    title: str
    status: str
    semantic_sources: tuple[SemanticSource, ...]
    revision: str
    edges: tuple[Edge, ...]
    validations: tuple[ValidationSnapshot, ...]
    maturity: str | None = None
    members: tuple[str, ...] = ()
    member_gates: Mapping[str, str] = field(
        default_factory=lambda: MappingProxyType({})
    )
    audit_stage: str | None = None
    required: tuple[str, ...] = ()
    optional: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    risk: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "member_gates",
            MappingProxyType(dict(sorted(self.member_gates.items()))),
        )

    @property
    def canonical_id(self) -> str:
        return f"{self.feature}/{self.node_id}"


@dataclass(frozen=True, slots=True)
class Graph:
    schema: int
    feature: str
    nodes: tuple[Node, ...]
    source: Path
    updated: str | None = None

    @property
    def identities(self) -> tuple[str, ...]:
        return tuple(node.canonical_id for node in self.nodes)

    def by_identity(self) -> dict[str, Node]:
        return {node.canonical_id: node for node in self.nodes}


@dataclass(frozen=True, slots=True)
class StructuralProblem:
    code: str
    message: str
    source: Path
    identity: str | None = None
    details: Mapping[str, Any] = field(default_factory=dict)
