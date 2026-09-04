"""Shared repository fixtures for release-evidence conformance tests."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


VERSION = "1.2.0"


def initialize_repository(root: Path, install_evidence: str) -> None:
    """Create a minimal repository containing every release-evidence input."""
    (root / ".codex-plugin").mkdir(parents=True)
    (root / "tests" / "scenarios").mkdir(parents=True)
    (root / "tests" / "evidence").mkdir(parents=True)
    (root / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"version": VERSION}),
        encoding="utf-8",
    )
    (root / "tests" / "scenarios" / "evidence.json").write_text(
        json.dumps(
            {
                "codex": {"pluginVersion": "0.2.0"},
                "claude": {"pluginVersion": "3.12.0"},
                "scope": "requirements-stage ambiguity discovery and gate behavior",
            }
        ),
        encoding="utf-8",
    )
    (root / "tests" / "evidence" / "release-review-final.json").write_text(
        json.dumps({"verdict": "PASS", "findings": []}),
        encoding="utf-8",
    )
    (root / "tests" / "evidence" / "install-cli.md").write_text(
        install_evidence,
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(f"## {VERSION}\n", encoding="utf-8")
    git(root, "init", "-b", "main")
    git(root, "config", "user.name", "Release Test")
    git(root, "config", "user.email", "release-test@example.invalid")
    git(root, "add", ".")
    git(root, "commit", "-m", "prepare release")


def prepublication_evidence() -> str:
    """Return evidence captured before the release tag can be installed."""
    return (
        "# Codex plugin release evidence\n\n"
        f"- Plugin: `codeops@codeops-marketplace`, version `{VERSION}`\n"
        "- Evidence state: pre-publication package validation\n"
        f"- Source state: working tree for planned `v{VERSION}`\n"
    )


def published_evidence() -> str:
    """Return evidence captured from the published marketplace version."""
    return (
        "# Codex plugin release evidence\n\n"
        f"- Plugin: `codeops@codeops-marketplace`, version `{VERSION}`\n"
        f"- Repository source: release tag `v{VERSION}`\n"
        f"- Plugin was installed and enabled at `{VERSION}`.\n"
    )


def git(root: Path, *arguments: str) -> None:
    """Run a checked Git command against the temporary repository."""
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
