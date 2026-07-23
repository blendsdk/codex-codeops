"""Deterministic discovery of live CodeOps artifact graphs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .models import StructuralProblem


@dataclass(frozen=True)
class Discovery:
    paths: tuple[Path, ...]
    problems: tuple[StructuralProblem, ...]


def discover_graphs(root: Path) -> list[Path]:
    return list(discover_state(root).paths)


def discover_state(root: Path) -> Discovery:
    problems: list[StructuralProblem] = []
    config = root / "codeops" / "codeops.json"
    if config.is_file():
        try:
            raw = json.loads(config.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return Discovery((), (StructuralProblem("invalid-config", f"cannot parse configuration: {exc}", config),))
        if not isinstance(raw, dict):
            return Discovery((), (StructuralProblem("invalid-config", "configuration must be an object", config),))
        artifacts = raw.get("artifacts")
        if not isinstance(artifacts, dict):
            return Discovery((), (StructuralProblem("invalid-config", "artifacts must be an object", config),))
        artifact_root = artifacts.get("root")
        if isinstance(artifact_root, str) and artifact_root:
            base = (root / artifact_root).resolve()
            if base != root.resolve() and root.resolve() not in base.parents:
                return Discovery((), (StructuralProblem("unsafe-config-root", f"artifacts.root escapes project root: {artifact_root}", config),))
            feature_root = base / "features"
            search_root = feature_root if feature_root.is_dir() else base
            return Discovery(tuple(sorted(search_root.glob("*/traceability.json"))), tuple(problems))
        return Discovery((), (StructuralProblem("invalid-config", "artifacts.root must be a non-empty string", config),))
    conventional = root / "codeops" / "features"
    if conventional.is_dir():
        return Discovery(tuple(sorted(conventional.glob("*/traceability.json"))), ())
    flat = root / "traceability.json"
    if flat.is_file():
        return Discovery((flat,), ())
    return Discovery((), ())
