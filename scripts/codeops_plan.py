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


IMPLEMENTS_RE = re.compile(r"^>[ \t]*\*\*Implements\*\*:[ \t]*(.+?)[ \t]*$", re.MULTILINE)
TARGET_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9_][A-Za-z0-9_-]*/)?"
    r"(?:RD-(?:[A-Za-z0-9]+-)*\d+|T-\d+|REQ-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)"
    r"(?![A-Za-z0-9_-])"
)
TASK_RE = re.compile(r"^-\s*\[([ xX~!])\]\s+(.+?)\s*$", re.MULTILINE)
BLOCKED_REASON_RE = re.compile(r"(?:blocked|reason)\s*:\s*\S", re.IGNORECASE)
_PROGRESS_WIDTH = 10
_PROGRESS_FILLED = "█"
_PROGRESS_EMPTY = "░"


@dataclass(frozen=True)
class Task:
    """One authoritative Markdown checklist task and its derived state."""

    marker: str
    text: str

    @property
    def state(self) -> str:
        """Return the stable user-facing state represented by the task marker."""
        return {" ": "not-started", "~": "verification-pending", "x": "verified", "!": "blocked"}[
            self.marker.lower()
        ]


@dataclass(frozen=True)
class PlanStatus:
    """Read-only lifecycle, progress, and diagnostics derived for one plan."""

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
    """Return ordered, de-duplicated requirement or tracker targets for a plan."""
    match = IMPLEMENTS_RE.search(index_text)
    if not match:
        return ()
    return tuple(dict.fromkeys(TARGET_RE.findall(match.group(1))))


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


def render_progress(verified: int, total: int) -> str:
    """Render verified task progress with both visual and textual context.

    The bar deliberately rounds filled cells down so it never visually suggests that a completion
    threshold has been reached early. The accompanying rounded percentage and exact fraction make
    the display understandable when block glyphs are unavailable or difficult to distinguish.

    Args:
        verified: Number of tasks whose verification passed.
        total: Total number of tasks in the checklist.

    Returns:
        A single user-facing progress line containing ten cells, counts, and percentage.

    Raises:
        ValueError: If either count is negative or verified exceeds total.
        TypeError: If either count is not an integer.

    Example:
        >>> render_progress(1, 3)
        'Progress: [███░░░░░░░] 1/3 tasks (33%)'
    """
    if isinstance(verified, bool) or not isinstance(verified, int):
        raise TypeError("verified must be an integer")
    if isinstance(total, bool) or not isinstance(total, int):
        raise TypeError("total must be an integer")
    if verified < 0 or total < 0:
        raise ValueError("task counts cannot be negative")
    if verified > total:
        raise ValueError("verified tasks cannot exceed total tasks")

    filled = (verified * _PROGRESS_WIDTH // total) if total else 0
    percentage = round(verified / total * 100) if total else 0
    cells = (_PROGRESS_FILLED * filled) + (_PROGRESS_EMPTY * (_PROGRESS_WIDTH - filled))
    return f"Progress: [{cells}] {verified}/{total} tasks ({percentage}%)"


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
        problems.append("00-index.md must declare one or more requirement or tracker targets in **Implements**")
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
            if not rd_id.rsplit("/", 1)[-1].startswith("RD-"):
                continue
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
    """Build the command-line parser for read-only plan inspection."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--plan", type=Path, help="inspect one plan directory")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true")
    output.add_argument(
        "--progress-bar",
        action="store_true",
        help="render verified task progress as an accessible ten-cell bar",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Inspect selected plans and write the requested read-only representation to stdout."""
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    plan_dirs = (args.plan if args.plan.is_absolute() else root / args.plan,) if args.plan else discover_plans(root)
    statuses = tuple(inspect_plan(path, root) for path in plan_dirs)
    payload = {"plans": [asdict(status) for status in statuses], "requirements": rd_delivery(statuses)}
    if args.json:
        print(json.dumps(payload, indent=2))
    elif args.progress_bar:
        for status in statuses:
            print(render_progress(status.verified, status.total))
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
