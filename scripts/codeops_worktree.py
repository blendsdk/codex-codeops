#!/usr/bin/env python3
"""Portable Git worktree command for native Codex sessions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_worktree_lib.model import (
    contained_worktree_path,
    git_root,
    list_worktrees,
    slugify_topic,
    validate_branch,
)
from scripts.codeops_worktree_lib.commands import create_worktree, remove_worktree
from scripts.codeops_platform.subprocesses import run_command


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    listing = subparsers.add_parser("list", aliases=["ls"])
    listing.add_argument("--root", type=Path, default=Path("."))
    listing.add_argument("--json", action="store_true")
    new = subparsers.add_parser("new")
    new.add_argument("topic")
    new.add_argument("--root", type=Path, default=Path("."))
    new.add_argument("--from", dest="base")
    new.add_argument("--branch")
    new.add_argument("--path", type=Path)
    new.add_argument("--launch", action="store_true")
    new.add_argument("--dry-run", action="store_true")
    new.add_argument("--json", action="store_true")
    remove = subparsers.add_parser("remove", aliases=["rm"])
    remove.add_argument("target")
    remove.add_argument("--root", type=Path, default=Path("."))
    remove.add_argument("--force", action="store_true")
    remove.add_argument("--delete-branch", action="store_true")
    remove.add_argument("--dry-run", action="store_true")
    remove.add_argument("--json", action="store_true")
    subparsers.add_parser("help")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "help":
        parser.print_help()
        return 0
    if args.command in {"list", "ls"}:
        try:
            worktrees = list_worktrees(args.root)
        except (OSError, ValueError) as exc:
            print(f"codeops-worktree: {exc}", file=sys.stderr)
            return 1
        payload = {"result": "listed", "worktrees": [item.to_json() for item in worktrees]}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            project = git_root(args.root)
            human = run_command(("git", "-C", str(project), "worktree", "list"), cwd=project)
            if human.exit_code != 0:
                print(human.stderr, end="", file=sys.stderr)
                return human.exit_code
            print(human.stdout, end="")
        return 0
    if args.command == "new":
        try:
            code, payload = create_worktree(
                args.root,
                args.topic,
                base=args.base,
                branch=args.branch,
                path=args.path,
                dry_run=args.dry_run,
                launch=args.launch,
            )
        except (OSError, ValueError) as exc:
            print(f"codeops-worktree: {exc}", file=sys.stderr)
            return 2
    else:
        try:
            code, payload = remove_worktree(
                args.root,
                args.target,
                force=args.force,
                delete_branch=args.delete_branch,
                dry_run=args.dry_run,
            )
        except (OSError, ValueError) as exc:
            print(f"codeops-worktree: {exc}", file=sys.stderr)
            return 2
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif code == 0:
        print(f"codeops-worktree: {payload['result']} {payload['path']}")
    else:
        print(f"codeops-worktree: {payload['error']}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
