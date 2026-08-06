#!/usr/bin/env python3
"""Create and compare complete Git worktree snapshots without changing the real index.

Examples:
    <CODEOPS_PYTHON> scripts/codeops_worktree_snapshot.py snapshot --root .
    <CODEOPS_PYTHON> scripts/codeops_worktree_snapshot.py diff --root . --baseline <tree>
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.codeops_platform.subprocesses import run_command, run_mutation_preflight
from scripts.codeops_state_lib.paths import NativePathProbe


OBJECT_ID_RE = re.compile(r"[0-9a-f]{40,64}")


class SnapshotError(RuntimeError):
    """Report a safe, user-facing snapshot failure."""


def run_git(root: Path, args: list[str], *, index_path: Path | None = None) -> str:
    """Run one Git command and return stdout, raising a concise error on failure."""
    environment = os.environ.copy()
    if index_path is not None:
        environment["GIT_INDEX_FILE"] = str(index_path)
    result = run_command(("git", "-C", str(root), *args), cwd=root, environment=environment)
    if result.exit_code != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise SnapshotError(message)
    return result.stdout


def snapshot_worktree(root: Path) -> str:
    """Write the complete non-ignored worktree to a Git tree without staging files."""
    probe = NativePathProbe()
    raw_common = run_git(root, ["rev-parse", "--git-common-dir"]).strip()
    common_dir = Path(raw_common)
    if not common_dir.is_absolute():
        common_dir = probe.canonical(root / common_dir)
    else:
        common_dir = probe.canonical(common_dir)
    index_path = common_dir / f"codeops-phase-index-{os.getpid()}"
    if index_path.exists():
        raise SnapshotError("temporary snapshot index already exists")
    targets = (common_dir / "objects", index_path)
    if run_mutation_preflight(root, targets, entrypoint_code="snapshot-write") != 0:
        raise SnapshotError("native mutation prerequisites are blocked")
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
    root = NativePathProbe().canonical(Path(args.root))
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
