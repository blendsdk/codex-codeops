#!/usr/bin/env python3
"""Create and compare complete Git worktree snapshots without changing the real index.

Examples:
    python3 scripts/codeops_worktree_snapshot.py snapshot --root .
    python3 scripts/codeops_worktree_snapshot.py diff --root . --baseline <tree>
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path


OBJECT_ID_RE = re.compile(r"[0-9a-f]{40,64}")


class SnapshotError(RuntimeError):
    """Report a safe, user-facing snapshot failure."""


def run_git(root: Path, args: list[str], *, index_path: Path | None = None) -> str:
    """Run one Git command and return stdout, raising a concise error on failure."""
    environment = os.environ.copy()
    if index_path is not None:
        environment["GIT_INDEX_FILE"] = str(index_path)
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise SnapshotError(message)
    return result.stdout


def snapshot_worktree(root: Path) -> str:
    """Write the complete non-ignored worktree to a Git tree without staging files."""
    descriptor, raw_path = tempfile.mkstemp(prefix="codeops-phase-index-")
    os.close(descriptor)
    index_path = Path(raw_path)
    index_path.unlink()
    try:
        run_git(root, ["read-tree", "HEAD"], index_path=index_path)
        run_git(root, ["add", "-A", "--", "."], index_path=index_path)
        tree = run_git(root, ["write-tree"], index_path=index_path).strip()
    finally:
        index_path.unlink(missing_ok=True)
    if not OBJECT_ID_RE.fullmatch(tree):
        raise SnapshotError("Git returned an invalid tree identifier")
    return tree


def diff_worktree(root: Path, baseline: str) -> str:
    """Return a binary-safe diff from a baseline tree to the current worktree."""
    if not OBJECT_ID_RE.fullmatch(baseline):
        raise SnapshotError("baseline must be a full Git object identifier")
    run_git(root, ["cat-file", "-e", f"{baseline}^{{tree}}"])
    current = snapshot_worktree(root)
    return run_git(root, ["diff", "--binary", "--no-ext-diff", baseline, current])


def parse_args() -> argparse.Namespace:
    """Parse the snapshot or diff command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "diff"))
    parser.add_argument("--root", default=".", help="Git repository root")
    parser.add_argument("--baseline", help="baseline tree identifier required by diff")
    return parser.parse_args()


def main() -> int:
    """Execute the requested worktree snapshot operation."""
    args = parse_args()
    root = Path(args.root).resolve()
    try:
        if args.command == "snapshot":
            if args.baseline is not None:
                raise SnapshotError("--baseline is valid only with diff")
            print(snapshot_worktree(root))
        else:
            if args.baseline is None:
                raise SnapshotError("diff requires --baseline")
            print(diff_worktree(root, args.baseline), end="")
    except SnapshotError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
