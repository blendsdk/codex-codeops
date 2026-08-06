"""Read-only Git worktree discovery and Windows-safe input validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
import re

from scripts.codeops_platform.subprocesses import run_command


SAFE_BRANCH = re.compile(r"^(?!/)(?!.*(?:\.\.|//|@\{|\\))[A-Za-z0-9][A-Za-z0-9._/-]*[A-Za-z0-9]$")


@dataclass(frozen=True, slots=True)
class Worktree:
    path: Path
    head: str | None
    branch: str | None
    detached: bool = False
    locked: bool = False
    prunable: bool = False

    def to_json(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "head": self.head,
            "branch": self.branch,
            "detached": self.detached,
            "locked": self.locked,
            "prunable": self.prunable,
        }


def git_root(candidate: Path) -> Path:
    result = run_command(("git", "-C", str(candidate), "rev-parse", "--show-toplevel"), cwd=candidate)
    if result.exit_code != 0 or not result.stdout.strip():
        raise ValueError("not inside a Git repository")
    return Path(result.stdout.strip()).resolve()


def parse_porcelain(text: str) -> tuple[Worktree, ...]:
    """Parse `git worktree list --porcelain` without locale-dependent text."""

    records: list[Worktree] = []
    current: dict[str, object] = {}
    for line in [*text.splitlines(), ""]:
        if not line:
            if current:
                records.append(Worktree(**current))
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = Path(value).resolve()
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key in {"detached", "locked", "prunable"}:
            current[key] = True
    return tuple(records)


def list_worktrees(root: Path) -> tuple[Worktree, ...]:
    project = git_root(root)
    result = run_command(("git", "-C", str(project), "worktree", "list", "--porcelain"), cwd=project)
    if result.exit_code != 0:
        raise OSError(result.stderr.strip() or "git worktree list failed")
    return parse_porcelain(result.stdout)


def slugify_topic(topic: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", topic.casefold()).strip("-")
    if not slug:
        raise ValueError("topic must contain a letter or digit")
    return slug


def validate_branch(branch: str) -> str:
    if not SAFE_BRANCH.fullmatch(branch) or branch.endswith((".", "/")) or "/." in branch:
        raise ValueError("branch is not a safe Git reference name")
    for component in branch.split("/"):
        parsed = PureWindowsPath(component)
        if parsed.drive or component.endswith((" ", ".")) or any(char in '<>:"\\|?*' for char in component):
            raise ValueError("branch contains a Windows-unsafe component")
    return branch


def contained_worktree_path(main: Path, value: Path) -> Path:
    """Require explicit worktree paths to be sibling children of the main checkout parent."""

    candidate = value.resolve(strict=False)
    parent = main.resolve().parent
    if candidate.parent != parent or candidate == main.resolve():
        raise ValueError("worktree path must be a distinct sibling of the main checkout")
    if candidate.name.endswith((" ", ".")) or any(char in '<>:"|?*' for char in candidate.name):
        raise ValueError("worktree path has a Windows-unsafe name")
    return candidate


def default_branch(root: Path) -> str:
    marker = root / "codeops" / ".codeops.yml"
    if marker.is_file():
        match = re.search(r"(?m)^\s*integrationBranch:\s*([^#\s]+)", marker.read_text(encoding="utf-8"))
        if match is not None:
            return validate_branch(match.group(1))
    result = run_command(
        ("git", "-C", str(root), "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"),
        cwd=root,
    )
    if result.exit_code == 0 and result.stdout.strip():
        return validate_branch(result.stdout.strip().removeprefix("refs/remotes/origin/"))
    for name in ("main", "master"):
        result = run_command(("git", "-C", str(root), "show-ref", "--verify", "--quiet", f"refs/heads/{name}"), cwd=root)
        if result.exit_code == 0:
            return name
    result = run_command(("git", "-C", str(root), "branch", "--show-current"), cwd=root)
    if result.exit_code != 0 or not result.stdout.strip():
        raise ValueError("cannot resolve the default branch")
    return validate_branch(result.stdout.strip())
