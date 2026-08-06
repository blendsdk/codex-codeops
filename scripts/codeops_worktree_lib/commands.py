"""Mutation-gated Git worktree creation and removal commands."""

from __future__ import annotations

from pathlib import Path
import subprocess

from scripts.codeops_platform.subprocesses import run_command, run_mutation_preflight

from .model import (
    contained_worktree_path,
    default_branch,
    git_root,
    list_worktrees,
    slugify_topic,
    validate_branch,
)


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    result = run_command(("git", "-C", str(root), *arguments), cwd=root)
    return result.exit_code, result.stdout, result.stderr


def _ref_exists(root: Path, ref: str) -> bool:
    return _git(root, "show-ref", "--verify", "--quiet", ref)[0] == 0


def _git_common_dir(root: Path) -> Path:
    code, stdout, stderr = _git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if code != 0 or not stdout.strip():
        raise ValueError(stderr.strip() or "cannot resolve Git common directory")
    return Path(stdout.strip()).resolve()


def _mutation_targets(project: Path, main: Path, worktree: Path) -> tuple[Path, tuple[Path, ...]]:
    boundary = main.resolve().parent
    common = _git_common_dir(project)
    targets = tuple(dict.fromkeys((
        common,
        (project / ".git").resolve(strict=False),
        worktree.resolve(strict=False),
    )))
    for target in targets:
        try:
            target.relative_to(boundary)
        except ValueError as exc:
            raise ValueError("Git/worktree mutation target escapes the common sibling boundary") from exc
    return boundary, targets


def create_worktree(
    root: Path,
    topic: str,
    *,
    base: str | None,
    branch: str | None,
    path: Path | None,
    dry_run: bool,
    launch: bool,
) -> tuple[int, dict[str, object]]:
    """Create or preview one sibling worktree using only Git argument vectors."""

    project = git_root(root)
    worktrees = list_worktrees(project)
    main = worktrees[0].path
    slug = slugify_topic(topic)
    selected_branch = validate_branch(branch or f"feat/{slug}")
    selected_path = contained_worktree_path(
        main,
        path if path is not None else main.parent / f"{main.name}-{slug}",
    )
    if selected_path.exists():
        return 1, {"result": "refused", "error": "target path already exists"}
    selected_base = validate_branch(base or default_branch(project))
    if _ref_exists(project, f"refs/heads/{selected_branch}"):
        arguments = ("worktree", "add", str(selected_path), selected_branch)
    elif _ref_exists(project, f"refs/remotes/origin/{selected_branch}"):
        arguments = (
            "worktree", "add", "--track", "-b", selected_branch,
            str(selected_path), f"origin/{selected_branch}",
        )
    else:
        arguments = (
            "worktree", "add", "-b", selected_branch, str(selected_path), selected_base,
        )
    payload: dict[str, object] = {
        "result": "preview" if dry_run else "created",
        "branch": selected_branch,
        "path": str(selected_path),
        "base": selected_base,
        "command": ["git", "-C", str(project), *arguments],
        "launched": False,
    }
    if dry_run:
        return 0, payload
    boundary, targets = _mutation_targets(project, main, selected_path)
    if run_mutation_preflight(
        boundary,
        targets,
        entrypoint_code="worktree-mutation",
    ) != 0:
        return 2, {"result": "blocked", "error": "native mutation prerequisites are blocked"}
    code, _, stderr = _git(project, *arguments)
    if code != 0:
        return 1, {"result": "refused", "error": stderr.strip() or "git worktree add failed"}
    if launch:
        try:
            subprocess.Popen(["codex"], cwd=selected_path, shell=False)
        except OSError as exc:
            return 1, {
                **payload,
                "result": "created-launch-failed",
                "error": str(exc),
            }
        payload["launched"] = True
    return 0, payload


def remove_worktree(
    root: Path,
    target: str,
    *,
    force: bool,
    delete_branch: bool,
    dry_run: bool,
) -> tuple[int, dict[str, object]]:
    """Remove or preview removal of one non-main registered worktree."""

    project = git_root(root)
    worktrees = list_worktrees(project)
    main = worktrees[0].path
    target_path = Path(target)
    if target_path.is_absolute() or any(separator in target for separator in ("/", "\\")):
        candidate = target_path.resolve(strict=False)
    else:
        slug = slugify_topic(target)
        candidate = main.parent / f"{main.name}-{slug}"
    candidate = contained_worktree_path(main, candidate)
    selected = next((item for item in worktrees[1:] if item.path == candidate), None)
    if selected is None:
        return 1, {"result": "refused", "error": "worktree is not registered"}
    arguments = ["worktree", "remove"]
    if force:
        arguments.append("--force")
    arguments.append(str(candidate))
    commands = [["git", "-C", str(project), *arguments]]
    if delete_branch and selected.branch:
        commands.append([
            "git", "-C", str(project), "branch", "-D", selected.branch,
        ])
    payload: dict[str, object] = {
        "result": "preview" if dry_run else "removed",
        "path": str(candidate),
        "branch": selected.branch,
        "commands": commands,
    }
    if dry_run:
        return 0, payload
    boundary, targets = _mutation_targets(project, main, candidate)
    if run_mutation_preflight(
        boundary,
        targets,
        entrypoint_code="worktree-mutation",
    ) != 0:
        return 2, {"result": "blocked", "error": "native mutation prerequisites are blocked"}
    completed = 0
    for command in commands:
        result = run_command(command, cwd=project)
        if result.exit_code != 0:
            error = result.stderr.strip() or "Git command failed"
            if completed and selected.branch:
                restored, _, restore_error = _git(
                    project,
                    "worktree",
                    "add",
                    str(candidate),
                    selected.branch,
                )
                if restored == 0:
                    return 1, {"result": "refused", "error": error, "rolledBack": True}
                return 2, {
                    "result": "recovery-required",
                    "error": error,
                    "recoveryError": restore_error.strip() or "worktree restoration failed",
                }
            return 1, {"result": "refused", "error": error}
        completed += 1
    return 0, payload
