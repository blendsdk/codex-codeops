"""Stable JSON-ready rendering for schema-2 state results."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import StructuralProblem


def problem_json(problem: StructuralProblem, root: Path) -> dict[str, Any]:
    try:
        source = str(problem.source.relative_to(root))
    except ValueError:
        source = str(problem.source)
    return {
        "code": problem.code,
        "message": problem.message,
        "source": source,
        "identity": problem.identity,
        **dict(problem.details),
    }


def problem_text(problem: StructuralProblem, root: Path) -> str:
    item = problem_json(problem, root)
    path = item.get("path")
    suffix = f" | path: {' -> '.join(path)}" if path else ""
    return f"ERROR [{item['code']}]: {item['source']}: {item['message']}{suffix}"
