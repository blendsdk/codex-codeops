"""Authorized, rollback-safe application of a layout migration preview."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from scripts.codeops_platform.subprocesses import run_command, run_mutation_preflight
from scripts.codeops_state_lib.filesystem import NativeAtomicWriteOps, atomic_write_bytes

from .model import MigrationPreview


def _git(root: Path, *arguments: str) -> tuple[int, str, str]:
    result = run_command(("git", "-C", str(root), *arguments), cwd=root)
    return result.exit_code, result.stdout, result.stderr


def _integration_branch(root: Path) -> str:
    code, stdout, _ = _git(root, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if code == 0 and stdout.strip():
        return stdout.strip().removeprefix("origin/")
    code, stdout, _ = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    return stdout.strip() if code == 0 and stdout.strip() else "main"


def _portfolio(root: Path, preview: MigrationPreview) -> bytes:
    today = date.today().isoformat()
    return (
        f"# Portfolio Roadmap: {root.name}\n\n"
        f"> **Status**: Active\n"
        f"> **Last Updated**: {today}\n"
        f"> **Features**: 0 / 1 done\n"
        f"> **CodeOps Artifact Schema**: 1\n\n"
        "## Legend\n\n"
        "⬜ Backlog · 🔄 In progress · ✅ Done · ⛔ Blocked · ⏸️ Deferred · 📦 Archived\n\n"
        "## Features\n\n"
        "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
        "|---------|---------|---------------|----------|--------|--------------|\n"
        f"| {preview.feature} | [→](features/{preview.feature}/00-roadmap.md) | migrated from flat layout | — | 🔄 | {today} |\n\n"
        "## Archived\n\n"
        "| Feature | Roadmap | Completed | Last Updated |\n"
        "|---------|---------|-----------|--------------|\n"
        "| — | — | — | — |\n"
    ).encode("utf-8")


def apply_preview(root: Path, preview: MigrationPreview) -> tuple[int, dict[str, object]]:
    """Apply a preview with Git moves and publish the layout marker last."""

    root = root.resolve()
    marker = root / "codeops" / ".codeops.yml"
    if preview.already_migrated or marker.is_file():
        return 0, {"result": "already-migrated", "feature": preview.feature, "moves": []}
    code, stdout, stderr = _git(root, "rev-parse", "--show-toplevel")
    if code != 0 or Path(stdout.strip()).resolve() != root:
        return 1, {"result": "refused", "error": stderr.strip() or "root is not a Git repository"}
    code, stdout, stderr = _git(root, "status", "--porcelain=v1")
    if code != 0 or stdout:
        return 1, {"result": "refused", "error": stderr.strip() or "working tree is dirty"}
    codeops = root / "codeops"
    if codeops.exists() and not codeops.is_dir():
        return 1, {"result": "refused", "error": "codeops exists but is not a directory"}
    targets = [root / move.source for move in preview.moves]
    targets.extend(root / move.target for move in preview.moves)
    config = codeops / "codeops.json"
    portfolio = codeops / "00-roadmap.md"
    targets.extend((codeops, config, portfolio, marker))
    if run_mutation_preflight(root, targets, entrypoint_code="layout-migration") != 0:
        return 1, {"result": "blocked", "error": "native mutation prerequisites are blocked"}

    completed: list[tuple[Path, Path]] = []
    created_files: list[Path] = []
    try:
        for move in preview.moves:
            source = root / move.source
            target = root / move.target
            target.parent.mkdir(parents=True, exist_ok=True)
            code, _, stderr = _git(root, "mv", str(source), str(target))
            if code != 0:
                raise OSError(stderr.strip() or f"git mv failed: {move.source}")
            completed.append((source, target))
        codeops.mkdir(parents=True, exist_ok=True)
        writer = NativeAtomicWriteOps(root)
        atomic_write_bytes(
            config,
            (json.dumps({
                "schema": 1,
                "mode": "strict",
                "artifacts": {"layout": "nested", "root": "codeops"},
                "quality": {
                    "independentReview": True,
                    "minimumReviewers": 1,
                    "stopOnMajorFinding": True,
                },
                "metrics": {"enabled": False},
            }, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            ops=writer,
        )
        created_files.append(config)
        atomic_write_bytes(portfolio, _portfolio(root, preview), ops=writer)
        created_files.append(portfolio)
        marker_text = (
            "# CodeOps layout marker.\n"
            "codeopsLayout: nested\n"
            'layoutVersion: "3.0.0"\n'
            f"integrationBranch: {_integration_branch(root)}\n"
            "conventions:\n"
            "  rdIdScope: per-feature\n"
            '  taskIdPrefix: "T"\n'
            "  maintenanceFeature: _maintenance\n"
            "  archiveDir: codeops/_archive\n"
        ).encode("utf-8")
        atomic_write_bytes(marker, marker_text, ops=writer)
        created_files.append(marker)
    except (OSError, ValueError) as exc:
        for path in reversed(created_files):
            path.unlink(missing_ok=True)
        rollback_ok = True
        for source, target in reversed(completed):
            code, _, _ = _git(root, "mv", str(target), str(source))
            rollback_ok = rollback_ok and code == 0
        return (1 if rollback_ok else 2), {
            "result": "refused" if rollback_ok else "recovery-required",
            "error": str(exc),
        }
    return 0, {
        "result": "applied",
        "feature": preview.feature,
        "moves": [move.to_json() for move in preview.moves],
        "marker": "codeops/.codeops.yml",
    }
