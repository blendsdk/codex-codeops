"""Explicit schema-one to schema-two traceability migration."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from . import legacy
from .discovery import discover_state
from .revisions import compute_revision
from .schema import RELATION_MATRIX, parse_graph_v2, validate_portfolio_v2
from .models import SemanticSource, SourceSelector
from .transitions import _atomic_write, _hash, replace_graph_atomically


PREVIEW_KIND = "codeops-traceability-upgrade-preview"
RESOLUTION_KIND = "codeops-traceability-upgrade-resolutions"


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _preview_hash(value: dict[str, Any]) -> str:
    unhashed = {key: item for key, item in value.items() if key != "previewHash"}
    return _hash(_canonical_json(unhashed))


def _safe_output(root: Path, path: Path) -> bool:
    resolved = path.resolve()
    project = root.resolve()
    return resolved == project or project in resolved.parents


def _find_schema_one(root: Path, feature: str) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for path in discover_state(root).paths:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if (
            isinstance(raw, dict)
            and raw.get("schema") == 1
            and raw.get("feature") == feature
        ):
            matches.append((path, raw))
    if len(matches) != 1:
        return None, None, f"expected one schema-1 graph for {feature}; found {len(matches)}"
    return matches[0][0], matches[0][1], None


def _relation_choices(source_type: str, target_type: str) -> list[str]:
    choices = [
        relation
        for relation, (sources, targets) in RELATION_MATRIX.items()
        if source_type in sources and target_type in targets
    ]
    return sorted(set(choices) | {"omit"})


def _build_preview(
    root: Path,
    feature: str,
    source: Path,
    raw: dict[str, Any],
    *,
    logical_source: Path | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    problems: list[legacy.Problem] = []
    graph = legacy.load_graph(source, root, problems)
    if graph is None or problems:
        return None, [
            {"code": "invalid-schema1", "message": problem.message}
            for problem in problems
        ]
    nodes = {item["id"]: item for item in raw["nodes"]}
    portfolio_types: dict[str, str] = {}
    for graph_path in discover_state(root).paths:
        graph_raw, _ = _read_object(graph_path)
        if graph_raw is None or not isinstance(graph_raw.get("feature"), str):
            continue
        for item in graph_raw.get("nodes", []):
            if (
                isinstance(item, dict)
                and isinstance(item.get("id"), str)
                and isinstance(item.get("type"), str)
            ):
                portfolio_types[
                    f"{graph_raw['feature']}/{item['id']}"
                ] = item["type"]
    unresolved: list[dict[str, Any]] = []
    for node_id, node in sorted(nodes.items()):
        unresolved.append({
            "id": f"source:{node_id}",
            "kind": "source-selector",
            "node": node_id,
            "path": str(
                (source.parent / node["path"]).resolve().relative_to(root.resolve())
            ),
            "choices": ["whole-file", "heading"],
        })
        for linked in sorted(node["links"]):
            canonical_target = (
                linked if "/" in linked else f"{feature}/{linked}"
            )
            target_type = portfolio_types.get(canonical_target)
            choices = (
                _relation_choices(node["type"], target_type)
                if target_type is not None
                else ["omit"]
            )
            unresolved.append({
                "id": f"edge:{node_id}:{linked}",
                "kind": "relationship",
                "source": node_id,
                "target": canonical_target,
                "choices": choices,
            })
    logical = logical_source or source
    preview: dict[str, Any] = {
        "schema": 1,
        "kind": PREVIEW_KIND,
        "feature": feature,
        "source": {
            "path": str(logical.relative_to(root)),
            "hash": _hash(source.read_bytes()),
            "schema": 1,
        },
        "destination": str(logical.relative_to(root)),
        "preservedNodes": [
            {
                key: node[key]
                for key in ("id", "type", "title", "status", "path")
            }
            | {
                "evidence": node.get("evidence", []),
                "risk": node.get("risk"),
            }
            for node in sorted(raw["nodes"], key=lambda item: item["id"])
        ],
        "unresolved": unresolved,
        "blockers": ["resolution-required"] if unresolved else [],
    }
    preview["previewHash"] = _preview_hash(preview)
    return preview, []


def _protected_preview_paths(root: Path) -> set[Path]:
    protected = {path.resolve() for path in discover_state(root).paths}
    config = root / "codeops" / "codeops.json"
    if config.exists():
        protected.add(config.resolve())
    for graph_path in discover_state(root).paths:
        raw, _ = _read_object(graph_path)
        if raw is None:
            continue
        if raw.get("schema") == 1:
            for node in raw.get("nodes", []):
                if isinstance(node, dict) and isinstance(node.get("path"), str):
                    protected.add((graph_path.parent / node["path"]).resolve())
        elif raw.get("schema") == 2:
            for node in raw.get("nodes", []):
                if not isinstance(node, dict):
                    continue
                for source in node.get("semanticSources", []):
                    if isinstance(source, dict) and isinstance(source.get("path"), str):
                        protected.add((root / source["path"]).resolve())
        protected.add(graph_path.with_name("traceability.schema1.backup.json").resolve())
    return protected


def make_preview(root: Path, feature: str, preview_path: Path) -> tuple[int, dict[str, Any]]:
    if not _safe_output(root, preview_path):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "unsafe-preview-path", "message": "preview path escapes root"}],
        }
    if (
        preview_path.resolve() in _protected_preview_paths(root)
        or (root / "codeops" / ".state-transactions").resolve()
        in preview_path.resolve().parents
    ):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "preview-path-collision", "message": "preview path is a protected project artifact"}],
        }
    source, raw, error = _find_schema_one(root, feature)
    if source is None or raw is None:
        existing = root / "codeops" / "features" / feature / "traceability.json"
        if existing.is_file():
            try:
                value = json.loads(existing.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                value = None
            if isinstance(value, dict) and value.get("schema") == 2:
                return 0, {
                    "result": "already-upgraded",
                    "feature": feature,
                    "destination": str(existing.relative_to(root)),
                    "blockers": [],
                }
        return 1, {
            "result": "refused",
            "blockers": [{"code": "schema1-source", "message": error or "source not found"}],
        }
    preview, blockers = _build_preview(root, feature, source, raw)
    if preview is None:
        return 1, {"result": "refused", "blockers": blockers}
    preview_bytes = _canonical_json(preview)
    if preview_path.exists() and preview_path.read_bytes() != preview_bytes:
        return 1, {
            "result": "refused",
            "blockers": [{"code": "preview-collision", "message": "non-identical preview exists"}],
        }
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    if not preview_path.exists():
        descriptor = os.open(
            preview_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(preview_bytes)
            handle.flush()
            os.fsync(handle.fileno())
    return 0, {
        "result": "preview",
        "feature": feature,
        "preview": str(preview_path.relative_to(root)),
        "previewHash": preview["previewHash"],
        "unresolved": preview["unresolved"],
        "blockers": preview["blockers"],
    }


def _read_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)
    return (value, None) if isinstance(value, dict) else (None, "root must be an object")


def _portfolio_projection_problems(
    root: Path,
    source: Path,
    projected: Any,
) -> list[Any]:
    graphs = [replace(projected, source=source)]
    problems: list[Any] = []
    for path in discover_state(root).paths:
        if path.resolve() == source.resolve():
            continue
        raw, _ = _read_object(path)
        if raw is None or raw.get("schema") != 2:
            continue
        graph, graph_problems = parse_graph_v2(path, root)
        problems.extend(graph_problems)
        if graph is not None:
            graphs.append(graph)
    problems.extend(validate_portfolio_v2(graphs))
    return problems


def _resolved_graph(
    root: Path,
    preview: dict[str, Any],
    resolutions: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    blockers: list[dict[str, str]] = []
    expected_ids = {item["id"] for item in preview["unresolved"]}
    decisions = resolutions.get("decisions")
    if not isinstance(decisions, dict) or set(decisions) != expected_ids:
        return None, [{
            "code": "incomplete-resolutions",
            "message": "resolutions must contain every unresolved id and no unknown id",
        }]
    preserved = {item["id"]: item for item in preview["preservedNodes"]}
    edges: dict[str, list[dict[str, str]]] = {identity: [] for identity in preserved}
    sources: dict[str, dict[str, Any]] = {}
    for unresolved in preview["unresolved"]:
        decision = decisions[unresolved["id"]]
        if not isinstance(decision, dict):
            blockers.append({"code": "invalid-resolution", "message": unresolved["id"]})
            continue
        if unresolved["kind"] == "relationship":
            if set(decision) != {"relation"}:
                blockers.append({"code": "invalid-resolution", "message": unresolved["id"]})
                continue
            relation = decision.get("relation")
            if relation not in unresolved["choices"]:
                blockers.append({"code": "invalid-resolution", "message": unresolved["id"]})
                continue
            if relation != "omit":
                target = unresolved["target"]
                canonical = (
                    target
                    if "/" in target
                    else f"{preview['feature']}/{target}"
                )
                edges[unresolved["source"]].append({
                    "relation": relation,
                    "target": canonical,
                })
        else:
            selector = decision.get("selector")
            if (
                set(decision) != {"selector"}
                or
                not isinstance(selector, dict)
                or selector.get("kind") not in unresolved["choices"]
                or set(selector) - {"kind", "value"}
                or (
                    selector.get("kind") == "heading"
                    and not isinstance(selector.get("value"), str)
                )
            ):
                blockers.append({"code": "invalid-resolution", "message": unresolved["id"]})
                continue
            sources[unresolved["node"]] = {
                "path": unresolved["path"],
                "selector": selector,
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            }
    if blockers:
        return None, blockers
    nodes: list[dict[str, Any]] = []
    for identity, item in sorted(preserved.items()):
        source = sources[identity]
        semantic = SemanticSource(
            source["path"],
            SourceSelector(source["selector"]["kind"], source["selector"].get("value")),
            source["normalization"],
            source["digest"],
        )
        node = {
            "id": identity,
            "type": item["type"],
            "title": item["title"],
            "status": item["status"],
            "semanticSources": [source],
            "revision": compute_revision(root, (semantic,)),
            "edges": sorted(edges[identity], key=lambda edge: (edge["relation"], edge["target"])),
            "validations": [],
        }
        if item["evidence"]:
            node["evidence"] = item["evidence"]
        if item["risk"] is not None:
            node["risk"] = item["risk"]
        nodes.append(node)
    return {
        "schema": 2,
        "feature": preview["feature"],
        "nodes": nodes,
    }, []


def apply_upgrade(
    root: Path,
    feature: str,
    preview_path: Path,
    resolutions_path: Path,
) -> tuple[int, dict[str, Any]]:
    if not _safe_output(root, preview_path) or not _safe_output(root, resolutions_path):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "unsafe-upgrade-path", "message": "input path escapes root"}],
        }
    preview, preview_error = _read_object(preview_path)
    resolutions, resolution_error = _read_object(resolutions_path)
    if preview is None or resolutions is None:
        return 1, {
            "result": "refused",
            "blockers": [{
                "code": "invalid-upgrade-input",
                "message": preview_error or resolution_error or "invalid input",
            }],
        }
    if (
        set(preview)
        != {
            "schema",
            "kind",
            "feature",
            "source",
            "destination",
            "preservedNodes",
            "unresolved",
            "blockers",
            "previewHash",
        }
        or set(resolutions) != {"schema", "previewHash", "decisions"}
        or
        preview.get("schema") != 1
        or preview.get("kind") != PREVIEW_KIND
        or preview.get("feature") != feature
        or preview.get("previewHash") != _preview_hash(preview)
        or resolutions.get("schema") != 1
        or resolutions.get("previewHash") != preview.get("previewHash")
    ):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "changed-preview", "message": "preview/resolution identity mismatch"}],
        }
    source_value = preview.get("source")
    if (
        not isinstance(source_value, dict)
        or set(source_value) != {"path", "hash", "schema"}
        or not isinstance(source_value.get("path"), str)
        or not isinstance(preview.get("destination"), str)
    ):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "invalid-preview", "message": "preview source shape is invalid"}],
        }
    source = (root / source_value["path"]).resolve()
    if not _safe_output(root, source):
        return 1, {
            "result": "refused",
            "blockers": [{"code": "unsafe-upgrade-path", "message": "source path escapes root"}],
        }
    backup = source.with_name("traceability.schema1.backup.json")
    if not source.is_file():
        return 1, {
            "result": "refused",
            "blockers": [{"code": "source-missing", "message": "schema-1 source is missing"}],
        }
    current = source.read_bytes()
    try:
        current_raw = json.loads(current.decode("utf-8"))
        current_schema = current_raw.get("schema")
    except (UnicodeError, json.JSONDecodeError, AttributeError):
        current_schema = None
    canonical_preview: dict[str, Any] | None = None
    canonical_blockers: list[dict[str, str]] = []
    if current_schema == 1:
        canonical_preview, canonical_blockers = _build_preview(
            root, feature, source, current_raw
        )
    elif current_schema == 2 and backup.is_file():
        backup_raw, backup_error = _read_object(backup)
        if backup_raw is None or backup_raw.get("schema") != 1:
            return 1, {
                "result": "refused",
                "blockers": [{"code": "invalid-backup", "message": backup_error or "backup is not schema 1"}],
            }
        canonical_preview, canonical_blockers = _build_preview(
            root,
            feature,
            backup,
            backup_raw,
            logical_source=source,
        )
    if canonical_preview is None or canonical_blockers:
        return 1, {
            "result": "refused",
            "blockers": canonical_blockers or [{"code": "schema1-source", "message": "no canonical schema-1 source"}],
        }
    if canonical_preview != preview:
        return 1, {
            "result": "refused",
            "blockers": [{"code": "changed-preview", "message": "preview does not match regenerated canonical source preview"}],
        }
    try:
        graph, blockers = _resolved_graph(root, preview, resolutions)
    except (KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        return 1, {
            "result": "refused",
            "blockers": [{"code": "invalid-resolution", "message": str(exc)}],
        }
    if graph is None:
        return 1, {"result": "refused", "blockers": blockers}
    after = _canonical_json(graph)
    if current_schema == 2:
        parsed, parse_problems = parse_graph_v2(source, root)
        portfolio_problems = (
            _portfolio_projection_problems(root, source, parsed)
            if parsed is not None
            else []
        )
        if current == after and parsed is not None and not parse_problems and not portfolio_problems:
            return 0, {
                "result": "no-change",
                "feature": feature,
                "destination": preview["destination"],
                "backup": str(backup.relative_to(root)),
                "destinationHash": _hash(after),
                "blockers": [],
            }
        return 1, {
            "result": "refused",
            "blockers": [{"code": "divergent-destination", "message": "current schema-2 graph differs from resolved projection"}],
        }
    temporary = source.with_name(f".{source.name}.upgrade-check.json")
    try:
        _atomic_write(temporary, after)
        parsed, parse_problems = parse_graph_v2(temporary, root)
    except OSError as exc:
        return 1, {
            "result": "refused",
            "blockers": [{"code": "projection-write", "message": str(exc)}],
        }
    finally:
        temporary.unlink(missing_ok=True)
    portfolio_problems = (
        _portfolio_projection_problems(root, source, parsed)
        if parsed is not None
        else []
    )
    if parsed is None or parse_problems or portfolio_problems:
        return 1, {
            "result": "refused",
            "blockers": [{"code": "invalid-projection", "message": "resolved graph is invalid"}],
        }
    operation = (
        "upgrade-"
        + re.sub(r"[^A-Za-z0-9._-]", "-", feature)
        + "-"
        + preview["previewHash"].split(":", 1)[-1][:16]
        + "-"
        + uuid.uuid4().hex[:12]
    )
    code, result = replace_graph_atomically(
        root,
        source,
        after,
        operation,
        expected_hash=preview["source"]["hash"],
        backup=backup,
    )
    if code != 0:
        return code, result
    result.update({
        "result": "committed",
        "feature": feature,
        "destination": preview["destination"],
        "backup": str(backup.relative_to(root)),
    })
    return 0, result
