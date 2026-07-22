#!/usr/bin/env python3
"""Safely materialize optional project-local Codex agents from CodeOps role templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MARKER = "# CODEOPS-GENERATED: install_agents.py schema=1"
ROLE_SOURCES = {
    "explorer": "codebase-scout.md",
    "design-challenger": "design-challenger.md",
    "performance-auditor": "perf-auditor.md",
    "correctness-reviewer": "phase-reviewer.md",
    "executor": "plan-task-executor.md",
    "demanding-executor": "plan-task-executor-opus.md",
    "preflight-auditor": "preflight-auditor.md",
    "security-auditor": "security-auditor.md",
    "spec-test-author": "spec-test-author.md",
    "financial-integrity-auditor": "financial-integrity-auditor.md",
    "concurrency-auditor": "concurrency-auditor.md",
    "semantics-reviewer": "semantics-reviewer.md",
}
WRITABLE = {"executor", "demanding-executor", "spec-test-author"}


def parse_template(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<header>.*?)\n---\n(?P<body>.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path}: missing YAML-like frontmatter")
    header: dict[str, str] = {}
    for line in match.group("header").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        header[key.strip()] = value.strip()
    for key in ("description",):
        if not header.get(key):
            raise ValueError(f"{path}: missing {key}")
    return header, match.group("body").strip()


def render(role: str, source: Path) -> str:
    header, body = parse_template(source)
    model = header.get("model")
    effort = header.get("effort", "high")
    lines = [
        MARKER,
        f"name = {json.dumps(role)}",
        f"description = {json.dumps(header['description'])}",
    ]
    if model:
        lines.append(f"model = {json.dumps(model)}")
    lines.extend([
        f"model_reasoning_effort = {json.dumps(effort)}",
        f"sandbox_mode = {json.dumps('workspace-write' if role in WRITABLE else 'read-only')}",
        f"developer_instructions = {json.dumps(body)}",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="target project root")
    parser.add_argument("--roles", help="comma-separated roles; default: all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plugin_root = Path(__file__).resolve().parent.parent
    project = Path(args.project).resolve()
    target_dir = project / ".codex" / "agents"
    roles = list(ROLE_SOURCES)
    if args.roles:
        roles = [role.strip() for role in args.roles.split(",") if role.strip()]
    unknown = sorted(set(roles) - set(ROLE_SOURCES))
    if unknown:
        print(f"Unknown roles: {', '.join(unknown)}", file=sys.stderr)
        return 2

    failed = False
    planned: list[tuple[Path, str]] = []
    for role in roles:
        destination = target_dir / f"{role}.toml"
        expected = render(role, plugin_root / "agent-templates" / ROLE_SOURCES[role])
        if destination.exists():
            actual = destination.read_text(encoding="utf-8")
            if not actual.startswith(MARKER):
                print(f"PRESERVE hand-authored {destination}")
                if args.check:
                    continue
                continue
            if actual == expected:
                print(f"OK {destination}")
                continue
            if args.check:
                print(f"DRIFT {destination}", file=sys.stderr)
                failed = True
                continue
        elif args.check:
            print(f"MISSING {destination}", file=sys.stderr)
            failed = True
            continue
        planned.append((destination, expected))

    if args.check:
        return 1 if failed else 0
    for destination, expected in planned:
        print(f"{'WOULD WRITE' if args.dry_run else 'WRITE'} {destination}")
        if not args.dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(expected, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
