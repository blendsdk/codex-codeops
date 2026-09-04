#!/usr/bin/env python3
"""Validate retained release evidence against the repository's Git state."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    """Parse the repository root supplied to the command-line validator."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repository_root",
        nargs="?",
        default=".",
        type=Path,
        help="repository root containing the plugin manifest and retained evidence",
    )
    return parser.parse_args()


def main() -> int:
    """Print every evidence error and return a shell-friendly status code."""
    root = parse_args().repository_root.expanduser().resolve()
    errors = validate_release_evidence(root)
    if errors:
        print("Release evidence validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Release evidence validation passed.")
    return 0


def validate_release_evidence(repository_root: Path) -> list[str]:
    """Return contract violations in the repository's retained release evidence.

    A writable branch must replace temporary evidence after its release tag exists. An immutable
    checkout of that exact tag may retain pre-publication evidence because installation from the
    tag cannot be observed before the tag is created.

    Args:
        repository_root: Root containing the manifest, changelog, evidence, and Git metadata.

    Returns:
        Human-readable validation errors. An empty list means the evidence is valid.

    @example
        ``validate_release_evidence(Path("."))`` validates the current repository.
    """
    root = repository_root.expanduser().resolve()
    try:
        manifest = _load_json_object(root / ".codex-plugin" / "plugin.json")
        scenario = _load_json_object(root / "tests" / "scenarios" / "evidence.json")
        review = _load_json_object(root / "tests" / "evidence" / "release-review-final.json")
        install = (root / "tests" / "evidence" / "install-cli.md").read_text(encoding="utf-8")
        changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        return [str(error)]

    errors: list[str] = []
    _validate_baseline_evidence(scenario, review, errors)

    version = manifest.get("version")
    if not isinstance(version, str) or not version:
        errors.append("plugin manifest version must be a non-empty string")
        return errors
    current = version.split("+", 1)[0]

    recorded_match = re.search(r"- Plugin: `[^`]+`, version `([^`]+)`", install)
    if recorded_match is None:
        errors.append("installation evidence must record the plugin version")
    elif recorded_match.group(1) != current:
        errors.append(f"installation evidence must record version {current}")

    if "- Evidence state: pre-publication package validation" in install:
        _validate_prepublication_evidence(root, current, install, errors)
    else:
        _validate_published_evidence(current, install, errors)

    if current not in changelog:
        errors.append(f"changelog must contain version {current}")
    return errors


def _load_json_object(path: Path) -> dict[str, Any]:
    """Load one required JSON object with a useful structural error."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _validate_baseline_evidence(
    scenario: dict[str, Any],
    review: dict[str, Any],
    errors: list[str],
) -> None:
    """Check the retained comparison and independent release-review evidence."""
    codex = scenario.get("codex")
    claude = scenario.get("claude")
    if not isinstance(codex, dict) or not str(codex.get("pluginVersion", "")).startswith("0.2.0"):
        errors.append("scenario evidence must retain the Codex 0.2.0 comparison baseline")
    if not isinstance(claude, dict) or claude.get("pluginVersion") != "3.12.0":
        errors.append("scenario evidence must retain the Claude 3.12.0 comparison baseline")
    if scenario.get("scope") != "requirements-stage ambiguity discovery and gate behavior":
        errors.append("scenario evidence must retain the requirements-stage comparison scope")
    if review.get("verdict") != "PASS":
        errors.append("final release review must have a PASS verdict")

    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("final release review findings must be a list")
        return
    for finding in findings:
        if isinstance(finding, dict) and finding.get("severity") in {"critical", "major"}:
            errors.append("final release review must not retain critical or major findings")
            return


def _validate_prepublication_evidence(
    repository_root: Path,
    current: str,
    install: str,
    errors: list[str],
) -> None:
    """Allow temporary evidence only before publication or inside the exact tag snapshot."""
    if f"- Source state: working tree for planned `v{current}`" not in install:
        errors.append(f"pre-publication evidence must identify planned tag v{current}")

    tag = f"v{current}"
    if _tag_exists(repository_root, tag) and not _is_detached_tag_checkout(repository_root, tag):
        errors.append(
            f"pre-publication evidence for {current} is stale outside the exact {tag} checkout"
        )


def _validate_published_evidence(current: str, install: str, errors: list[str]) -> None:
    """Require a published tag and observed enabled version in durable evidence."""
    if f"- Repository source: release tag `v{current}`" not in install:
        errors.append(f"published evidence must identify release tag v{current}")
    if re.search(rf"enabled at\s+`{re.escape(current)}`", install) is None:
        errors.append(f"published evidence must confirm enabled version {current}")


def _tag_exists(repository_root: Path, tag: str) -> bool:
    """Return whether the repository contains the exact tag reference."""
    result = _git(
        repository_root,
        "rev-parse",
        "--verify",
        "--quiet",
        f"refs/tags/{tag}",
    )
    return result.returncode == 0


def _is_detached_tag_checkout(repository_root: Path, tag: str) -> bool:
    """Return whether detached HEAD points at the commit named by an exact release tag."""
    branch = _git(repository_root, "symbolic-ref", "--quiet", "HEAD")
    if branch.returncode == 0:
        return False

    head = _git(repository_root, "rev-parse", "--verify", "HEAD^{commit}")
    tagged = _git(repository_root, "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    return (
        head.returncode == 0
        and tagged.returncode == 0
        and head.stdout.strip() == tagged.stdout.strip()
    )


def _git(repository_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a non-interactive, read-only Git query within the selected repository."""
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


if __name__ == "__main__":
    raise SystemExit(main())
