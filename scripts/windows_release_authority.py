#!/usr/bin/env python3
"""Load the independently owned native-Windows release-candidate identity."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FIELDS = {
    "schemaVersion", "pluginVersion", "sourceCommit", "candidateSha256", "artifactName", "ci",
}
CI_FIELDS = {"runId", "headCommit", "conclusion", "artifactName"}


def load_authority(path: Path, expected_version: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Return one closed candidate authority and deterministic validation errors."""

    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return None, [f"release authority is unavailable or invalid: {error}"]
    if not isinstance(value, dict):
        return None, ["release authority must contain a JSON object"]
    unknown = set(value) - FIELDS
    if unknown:
        errors.append(f"release authority has unknown fields: {', '.join(sorted(unknown))}")
    if value.get("schemaVersion") != 1:
        errors.append("release authority schemaVersion must be 1")
    if value.get("pluginVersion") != expected_version:
        errors.append("release authority pluginVersion does not match the plugin manifest")
    if COMMIT_RE.fullmatch(str(value.get("sourceCommit", ""))) is None:
        errors.append("release authority sourceCommit must be a full lowercase Git commit")
    if SHA256_RE.fullmatch(str(value.get("candidateSha256", ""))) is None:
        errors.append("release authority candidateSha256 must be lowercase SHA-256")
    if not isinstance(value.get("artifactName"), str) or not value.get("artifactName"):
        errors.append("release authority artifactName is required")
    ci = value.get("ci")
    if not isinstance(ci, dict):
        errors.append("release authority ci must be an object")
    else:
        unknown_ci = set(ci) - CI_FIELDS
        if unknown_ci:
            errors.append(f"release authority ci has unknown fields: {', '.join(sorted(unknown_ci))}")
        if not isinstance(ci.get("runId"), str) or not ci.get("runId"):
            errors.append("release authority ci.runId is required")
        if COMMIT_RE.fullmatch(str(ci.get("headCommit", ""))) is None:
            errors.append("release authority ci.headCommit must be a full lowercase Git commit")
        elif ci.get("headCommit") != value.get("sourceCommit"):
            errors.append("release authority ci.headCommit must match sourceCommit")
        if ci.get("conclusion") != "success":
            errors.append("release authority ci.conclusion must be success")
        if ci.get("artifactName") != value.get("artifactName"):
            errors.append("release authority artifact names do not match")
    return value, errors


def verify_candidate(path: Path, authority: dict[str, Any]) -> list[str]:
    """Rehash a candidate archive against the independently retained authority."""

    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        return [f"release candidate cannot be read: {error}"]
    return [] if digest == authority.get("candidateSha256") else [
        "release candidate SHA-256 does not match the independent authority"
    ]
