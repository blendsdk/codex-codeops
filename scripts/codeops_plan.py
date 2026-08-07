#!/usr/bin/env python3
"""Derive CodeOps plan progress directly from Markdown artifacts.

This module is intentionally a read-only parser. Markdown remains authoritative;
the helper has no state store, transition API, revision counter, lock, or journal.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


IMPLEMENTS_RE = re.compile(r"^>\s*\*\*Implements\*\*:\s*(.+?)\s*$", re.MULTILINE)
RD_RE = re.compile(r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9][A-Za-z0-9_-]*/)?RD-\d+(?![A-Za-z0-9_-])")
TASK_RE = re.compile(r"^-\s*\[([ xX~!])\]\s+(.+?)\s*$", re.MULTILINE)
BLOCKED_REASON_RE = re.compile(r"(?:blocked|reason)\s*:\s*\S", re.IGNORECASE)


@dataclass(frozen=True)
class Task:
    marker: str
    text: str

    @property
    def state(self) -> str:
        return {" ": "not-started", "~": "verification-pending", "x": "verified", "!": "blocked"}[
            self.marker.lower()
        ]


@dataclass(frozen=True)
class PlanStatus:
    plan: str
    implements: tuple[str, ...]
    lifecycle: str
    total: int
    not_started: int
    verification_pending: int
    verified: int
    blocked: int
    next_task: str | None
    problems: tuple[str, ...]


def parse_implements(index_text: str) -> tuple[str, ...]:
    """Return the ordered, de-duplicated RD identifiers declared by a plan."""
    match = IMPLEMENTS_RE.search(index_text)
    if not match:
        return ()
    return tuple(dict.fromkeys(RD_RE.findall(match.group(1))))


def parse_tasks(execution_text: str) -> tuple[Task, ...]:
    """Parse only the four authoritative execution checklist markers."""
    return tuple(Task(marker.lower(), text.strip()) for marker, text in TASK_RE.findall(execution_text))


def next_task(tasks: tuple[Task, ...]) -> Task | None:
    """Resume verification first, otherwise start the first untouched task."""
    return next((task for task in tasks if task.marker == "~"), None) or next(
        (task for task in tasks if task.marker == " "), None
    )


def lifecycle(tasks: tuple[Task, ...]) -> str:
    """Derive the plan's Ready/Executing/Done/Blocked lifecycle from its checklist."""
    if any(task.marker == "!" for task in tasks):
        return "Blocked"
    if tasks and all(task.marker == "x" for task in tasks):
        return "Done"
    if any(task.marker in {"~", "x"} for task in tasks):
        return "Executing"
    return "Ready"


def inspect_plan(plan_dir: Path, root: Path | None = None) -> PlanStatus:
    """Inspect one plan directory without mutating it."""
    index_path = plan_dir / "00-index.md"
    execution_path = plan_dir / "99-execution-plan.md"
    problems: list[str] = []
    index_text = index_path.read_text(encoding="utf-8") if index_path.is_file() else ""
    execution_text = execution_path.read_text(encoding="utf-8") if execution_path.is_file() else ""
    if not index_path.is_file():
        problems.append("missing required 00-index.md")
    if not execution_path.is_file():
        problems.append("missing required 99-execution-plan.md")
    implements = parse_implements(index_text)
    if not implements:
        problems.append("00-index.md must declare one or more RD identifiers in **Implements**")
    tasks = parse_tasks(execution_text)
    if not tasks:
        problems.append("99-execution-plan.md contains no execution tasks")
    for task in tasks:
        if task.marker == "!" and not BLOCKED_REASON_RE.search(task.text):
            problems.append(f"blocked task lacks a visible 'Blocked: <reason>': {task.text}")
    counts = {marker: sum(task.marker == marker for task in tasks) for marker in (" ", "~", "x", "!")}
    candidate = next_task(tasks)
    display = str(plan_dir.resolve())
    if root is not None:
        try:
            display = plan_dir.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    return PlanStatus(
        plan=display,
        implements=implements,
        lifecycle=lifecycle(tasks),
        total=len(tasks),
        not_started=counts[" "],
        verification_pending=counts["~"],
        verified=counts["x"],
        blocked=counts["!"],
        next_task=candidate.text if candidate else None,
        problems=tuple(problems),
    )


def discover_plans(root: Path) -> tuple[Path, ...]:
    """Discover flat and nested plan directories by their execution plan."""
    paths = set((root / "plans").glob("*/99-execution-plan.md"))
    paths.update((root / "codeops" / "features").glob("*/plans/*/99-execution-plan.md"))
    return tuple(sorted(path.parent for path in paths))


def rd_delivery(statuses: tuple[PlanStatus, ...]) -> dict[str, str]:
    """Derive each RD's delivery state from its implementing plan or plans."""
    grouped: dict[str, list[str]] = {}
    for status in statuses:
        for rd_id in status.implements:
            grouped.setdefault(rd_id, []).append(status.lifecycle)
    result: dict[str, str] = {}
    for rd_id, states in grouped.items():
        if "Blocked" in states:
            result[rd_id] = "Blocked"
        elif states and all(state == "Done" for state in states):
            result[rd_id] = "Done"
        elif any(state == "Executing" for state in states):
            result[rd_id] = "Executing"
        else:
            result[rd_id] = "Ready"
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, help="inspect one plan directory")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    plan_dirs = (args.plan if args.plan.is_absolute() else root / args.plan,) if args.plan else discover_plans(root)
    statuses = tuple(inspect_plan(path, root) for path in plan_dirs)
    payload = {"plans": [asdict(status) for status in statuses], "requirements": rd_delivery(statuses)}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for status in statuses:
            progress = f"{status.verified}/{status.total} verified"
            print(f"{status.plan}: {status.lifecycle} ({progress})")
            if status.next_task:
                print(f"  next: {status.next_task}")
            for problem in status.problems:
                print(f"  ERROR: {problem}")
    return 1 if any(status.problems for status in statuses) else 0


if __name__ == "__main__":
    sys.exit(main())
