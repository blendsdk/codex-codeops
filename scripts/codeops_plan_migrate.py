#!/usr/bin/env python3
"""One-shot migration from traceability graphs to authoritative Markdown plans.

The command previews by default. ``--apply`` updates plan ``Implements`` metadata
and deletes obsolete feature ``traceability.json`` files only when every mapping
is unambiguous. It creates no replacement state or compatibility layer.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.codeops_plan import IMPLEMENTS_RE, inspect_plan, parse_implements
except ModuleNotFoundError:  # Direct execution adds scripts/, not the repository root, to sys.path.
    from codeops_plan import IMPLEMENTS_RE, inspect_plan, parse_implements


RD_ID_RE = re.compile(r"^RD-(?:[A-Za-z0-9]+-)*\d+$")
RD_FILE_RE = re.compile(r"^(RD-(?:[A-Za-z0-9]+-)*\d+)(?:[-.].*)?$", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[[^]]*\]\(([^)]+)\)")


@dataclass(frozen=True)
class PlanMigration:
    index: Path
    implements: tuple[str, ...]
    source: str
    updated_text: str
    changed: bool


@dataclass(frozen=True)
class Migration:
    root: Path
    plans: tuple[PlanMigration, ...]
    graphs: tuple[Path, ...]
    problems: tuple[str, ...]


def _qualify(feature: str, rd_id: str) -> str:
    return rd_id if "/" in rd_id else f"{feature}/{rd_id}"


def _rd_ids(feature_dir: Path) -> tuple[str, ...]:
    result: list[str] = []
    requirements = feature_dir / "requirements"
    if requirements.is_dir():
        for path in requirements.glob("RD-*.md"):
            match = RD_FILE_RE.match(path.name)
            if match:
                result.append(_qualify(feature_dir.name, match.group(1).upper()))
    return tuple(dict.fromkeys(sorted(result)))


def _roadmap_links(feature_dir: Path) -> dict[Path, tuple[str, ...]]:
    """Map plan indexes to RD IDs using the feature roadmap's Tracker rows."""
    roadmap = feature_dir / "00-roadmap.md"
    if not roadmap.is_file():
        return {}
    found: dict[Path, list[str]] = {}
    for line in roadmap.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not RD_ID_RE.fullmatch(cells[0]):
            continue
        for link in MARKDOWN_LINK_RE.findall(cells[3]):
            link_path = link.split("#", 1)[0]
            if not link_path.endswith("00-index.md"):
                continue
            index = (roadmap.parent / link_path).resolve()
            found.setdefault(index, []).append(_qualify(feature_dir.name, cells[0]))
    return {path: tuple(dict.fromkeys(ids)) for path, ids in found.items()}


def _replace_implements(index_text: str, implements: tuple[str, ...]) -> str:
    line = f"> **Implements**: {', '.join(implements)}"
    if IMPLEMENTS_RE.search(index_text):
        return IMPLEMENTS_RE.sub(line, index_text, count=1)
    lines = index_text.splitlines(keepends=True)
    insert_at = 1 if lines and lines[0].lstrip().startswith("#") else 0
    newline = "\r\n" if "\r\n" in index_text else "\n"
    insertion = line + newline
    if insert_at and len(lines) > insert_at and lines[insert_at].strip():
        insertion = newline + insertion + newline
    lines.insert(insert_at, insertion)
    return "".join(lines)


def inspect_migration(codeops_root: Path) -> Migration:
    root = codeops_root.resolve()
    problems: list[str] = []
    plans: list[PlanMigration] = []
    if root.name.lower() != "codeops" or not (root / "features").is_dir():
        return Migration(root, (), (), ("target must be a nested CodeOps directory named 'codeops' with features/",))

    feature_dirs = [path for path in (root / "features").iterdir() if path.is_dir()]
    archive = root / "_archive"
    if archive.is_dir():
        feature_dirs.extend(path for path in archive.iterdir() if path.is_dir())
    graphs = tuple(
        sorted(
            feature_dir / "traceability.json"
            for feature_dir in feature_dirs
            if (feature_dir / "traceability.json").is_file()
        )
    )
    for feature_dir in sorted(feature_dirs):
        plan_dirs = sorted((feature_dir / "plans").glob("*/99-execution-plan.md"))
        roadmap_links = _roadmap_links(feature_dir)
        feature_rds = _rd_ids(feature_dir)
        for execution in plan_dirs:
            plan_dir = execution.parent
            index = plan_dir / "00-index.md"
            if not index.is_file():
                problems.append(f"{index}: missing 00-index.md")
                continue
            index_text = index.read_text(encoding="utf-8")
            declared = tuple(_qualify(feature_dir.name, item) for item in parse_implements(index_text))
            if declared:
                implements, source = declared, "existing declaration"
            elif index.resolve() in roadmap_links:
                implements, source = roadmap_links[index.resolve()], "feature roadmap"
            elif len(plan_dirs) == 1 and len(feature_rds) == 1:
                implements, source = feature_rds, "single plan and single RD"
            else:
                problems.append(
                    f"{index}: cannot infer implemented RDs; add an Implements declaration or roadmap link"
                )
                continue
            updated = _replace_implements(index_text, implements)
            status = inspect_plan(plan_dir, root.parent)
            non_mapping_problems = tuple(
                problem for problem in status.problems if "must declare one or more RD" not in problem
            )
            problems.extend(f"{plan_dir}: {problem}" for problem in non_mapping_problems)
            plans.append(PlanMigration(index, implements, source, updated, updated != index_text))
    return Migration(root, tuple(plans), graphs, tuple(problems))


def _require_clean_git_tree(root: Path) -> str | None:
    probe = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode:
        return "--apply requires the codeops directory to be inside a Git repository"
    repo = Path(probe.stdout.strip()).resolve()
    status = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode:
        return "unable to inspect Git working tree"
    if status.stdout.strip():
        return "--apply requires a clean Git working tree"
    return None


def apply_migration(migration: Migration) -> None:
    for plan in migration.plans:
        plan.index.write_text(plan.updated_text, encoding="utf-8", newline="")
    for graph in migration.graphs:
        graph.unlink()


def render(migration: Migration, applying: bool) -> None:
    mode = "APPLY" if applying else "PREVIEW"
    print(f"codeops-plan-migrate: {mode} {migration.root}")
    for plan in migration.plans:
        relative = plan.index.relative_to(migration.root).as_posix()
        values = ", ".join(plan.implements)
        action = "UPDATE" if plan.changed else "KEEP"
        print(f"  {action} {relative}: {values} ({plan.source})")
    for graph in migration.graphs:
        print(f"  DELETE {graph.relative_to(migration.root).as_posix()}")
    for problem in migration.problems:
        print(f"  BLOCKED {problem}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("codeops", type=Path, help="nested codeops/ directory to migrate")
    parser.add_argument("--apply", action="store_true", help="apply the previewed Markdown edits and deletions")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    migration = inspect_migration(args.codeops)
    if migration.problems:
        render(migration, args.apply)
        return 1
    if args.apply:
        git_problem = _require_clean_git_tree(migration.root)
        if git_problem:
            print(f"codeops-plan-migrate: BLOCKED {git_problem}", file=sys.stderr)
            return 1
        apply_migration(migration)
    render(migration, args.apply)
    if not args.apply:
        print("Run again with --apply to perform this migration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
