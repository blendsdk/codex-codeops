"""Canonical semantic revisions and relationship-specific snapshot validation."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .closure import TRACE_BY_GATE
from .models import Node, SemanticSource, StructuralProblem


def normalize_utf8(data: bytes) -> str:
    text = data.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip(" \t") for line in text.split("\n")).rstrip("\n") + "\n"


def heading_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    heading_re = re.compile(r"^[ ]{0,3}(#{1,6})[ \t]+(.+?)[ \t]*$")
    fence_re = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$")
    matches: list[tuple[int, int]] = []
    fence: tuple[str, int] | None = None
    for index, line in enumerate(lines):
        marker = fence_re.match(line)
        if marker is not None:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not marker.group(2).strip():
                fence = None
            continue
        if fence is not None:
            continue
        match = heading_re.fullmatch(line)
        if match is not None:
            title = re.sub(r"[ \t]+#+[ \t]*$", "", match.group(2))
            if title == heading:
                matches.append((index, len(match.group(1))))
    if len(matches) != 1:
        return None
    start, level = matches[0]
    end = len(lines)
    fence = None
    for index in range(start + 1, len(lines)):
        marker = fence_re.match(lines[index])
        if marker is not None:
            token = marker.group(1)
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not marker.group(2).strip():
                fence = None
            continue
        if fence is not None:
            continue
        match = heading_re.fullmatch(lines[index])
        if match is not None and len(match.group(1)) <= level:
            end = index
            break
    return "\n".join(lines[start:end]).rstrip("\n") + "\n"


def compute_revision(root: Path, sources: tuple[SemanticSource, ...]) -> str:
    selected: list[tuple[tuple[str, str, str], str]] = []
    for source in sources:
        path = (root / source.path).resolve()
        if path != root.resolve() and root.resolve() not in path.parents:
            raise ValueError(f"source escapes project root: {source.path}")
        text = normalize_utf8(path.read_bytes())
        if source.selector.kind == "heading":
            section = heading_section(text, source.selector.value or "")
            if section is None:
                raise ValueError(
                    f"heading selector must match exactly once: {source.selector.value}"
                )
            text = section
        selected.append(
            ((source.path, source.selector.kind, source.selector.value or ""), text)
        )
    payload = "".join(text for _, text in sorted(selected))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def snapshot_problems(
    gate: str,
    members: tuple[str, ...],
    paths: dict[str, tuple[str, ...]],
    nodes: dict[str, Node],
    sources: dict[str, Path],
) -> list[StructuralProblem]:
    problems: list[StructuralProblem] = []
    required_relations = {
        "depends-on",
        "consumes-contract",
        *(TRACE_BY_GATE.get(gate, set()) - {"affected-by"}),
    }
    if gate == "release":
        required_relations.add("release-coupled")
    for identity in members:
        node = nodes[identity]
        required = {
            (edge.target, edge.relation, gate)
            for edge in node.edges
            if edge.relation in required_relations
            and edge.relation != "related"
            and edge.target in members
        }
        snapshots = {
            snapshot.key: snapshot
            for snapshot in node.validations
            if snapshot.gate == gate
        }
        for key in sorted(required - set(snapshots)):
            upstream, relation, snapshot_gate = key
            problems.append(
                StructuralProblem(
                    "missing-snapshot",
                    f"{identity} lacks a {snapshot_gate} snapshot for {relation} {upstream}",
                    sources[identity],
                    identity,
                    {
                        "path": paths.get(identity, (identity,)) + (upstream,),
                        "upstream": upstream,
                        "relation": relation,
                        "gate": snapshot_gate,
                    },
                )
            )
        for key in sorted(set(snapshots) - required):
            snapshot = snapshots[key]
            problems.append(
                StructuralProblem(
                    "extraneous-snapshot",
                    f"{identity} snapshot has no persisted {snapshot.relation} relationship to {snapshot.upstream}",
                    sources[identity],
                    identity,
                    {
                        "path": paths.get(identity, (identity,)),
                        "upstream": snapshot.upstream,
                        "relation": snapshot.relation,
                        "gate": snapshot.gate,
                    },
                )
            )
        for key in sorted(required & set(snapshots)):
            snapshot = snapshots[key]
            upstream = nodes.get(snapshot.upstream)
            actual = upstream.revision if upstream is not None else "missing"
            if actual == snapshot.revision:
                continue
            problems.append(
                StructuralProblem(
                    "stale-snapshot",
                    f"{identity} snapshot for {snapshot.upstream} expected {snapshot.revision} but found {actual}",
                    sources[identity],
                    identity,
                    {
                        "path": paths.get(identity, (identity,)) + (
                            (() if snapshot.upstream == identity else (snapshot.upstream,))
                        ),
                        "upstream": snapshot.upstream,
                        "expected": snapshot.revision,
                        "actual": actual,
                        "relation": snapshot.relation,
                        "gate": snapshot.gate,
                    },
                )
            )
    return problems
