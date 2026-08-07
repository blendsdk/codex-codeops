#!/usr/bin/env python3
"""Validate retained native Windows certification evidence."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence


REQUIRED_SCENARIOS = (
    "installation", "enablement", "session-preflight", "requirements", "planning",
    "preflight-audit", "execution-transition-recovery", "migration", "roadmap",
    "worktree", "agent-install-check", "outcomes", "verification",
)
DESKTOP_CHECKS = (
    "installation", "enablement", "hook-review", "preflight", "requirements-to-plan",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
PROHIBITED_RUNTIME_RE = re.compile(
    r"(?:^|[\\/\s])(?:wsl|bash|git-bash)(?:\.exe)?(?:$|[\\/\s])|(?:^|[\\/])/mnt(?:[\\/]|$)",
    re.IGNORECASE,
)
WINDOWS_SUPPORT_CLAIM_RE = re.compile(
    r"\b(?:CodeOps\s+)?supports?\s+(?:native\s+)?Windows 11\b|"
    r"\b(?:native\s+)?Windows 11\s+is\s+(?:a\s+)?supported\b|"
    r"\bsupported\s+on\s+(?:native\s+)?Windows 11\b",
    re.IGNORECASE,
)

COMMON_FIELDS = {
    "schemaVersion", "pluginVersion", "commit", "candidateSha256", "reviewer", "kind",
}
CLI_FIELDS = COMMON_FIELDS | {
    "host", "tools", "ci", "captureVersion", "assertions", "commandTrace", "scenarios",
}
DESKTOP_FIELDS = COMMON_FIELDS | {"tools", "assertions", "checklist"}
RECORD_FIELDS = {
    "schemaVersion", "scenarioId", "result", "commandClass", "timestamp", "summary",
}
TRACE_FIELDS = {"scenarioId", "executable", "arguments", "exitClass"}
SCENARIO_COMMAND_MARKERS = {
    "installation": ("plugin", "add"),
    "enablement": ("plugin", "list"),
    "session-preflight": ("codeops-windows-preflight.ps1",),
    "requirements": ("exec", "make-requirements"),
    "planning": ("exec", "make-plan"),
    "preflight-audit": ("exec", "preflight"),
    "execution-transition-recovery": ("transition", "transition-recover"),
    "migration": ("codeops_migrate.py", "apply"),
    "roadmap": ("codeops_roadmap.py", "sync"),
    "worktree": ("codeops_worktree.py",),
    "agent-install-check": ("install_agents.py", "--check"),
    "outcomes": ("codeops_outcomes.py", "emit", "report"),
    "verification": ("codeops_verify.py", "all"),
}


def _object(value: Any, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return None
    return value


def _closed(payload: Mapping[str, Any], allowed: set[str], label: str, errors: list[str]) -> None:
    for field in sorted(set(payload) - allowed):
        errors.append(f"{label} contains unknown field `{field}`")


def _read_object(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        errors.append(f"unable to read {label}: {error}")
        return None
    except json.JSONDecodeError as error:
        errors.append(f"{label} is not valid JSON: {error}")
        return None
    return _object(value, label, errors)


def _resolve_supporting(root: Path, raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        errors.append(f"{label} must be a non-empty portable relative path")
        return None
    candidate = Path(raw)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        errors.append(f"{label} must stay inside the evidence root")
        return None
    resolved = (root / candidate).resolve(strict=False)
    if not resolved.is_relative_to(root.resolve(strict=False)):
        errors.append(f"{label} must stay inside the evidence root")
        return None
    if not resolved.is_file():
        errors.append(f"{label} is missing")
        return None
    return resolved


def _hash_matches(path: Path, expected: Any, label: str, errors: list[str]) -> None:
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if not isinstance(expected, str) or SHA256_RE.fullmatch(expected) is None or expected != actual:
        errors.append(f"{label} hash does not match its supporting record")


def _reviewer(value: Any, label: str, errors: list[str]) -> None:
    reviewer = _object(value, f"{label} reviewer", errors)
    if reviewer is None:
        return
    _closed(reviewer, {"github", "timestamp"}, f"{label} reviewer", errors)
    github = reviewer.get("github")
    if not isinstance(github, str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", github):
        errors.append(f"{label} reviewer must include a valid GitHub identity")
    timestamp = reviewer.get("timestamp")
    if not isinstance(timestamp, str) or UTC_RE.fullmatch(timestamp) is None:
        errors.append(f"{label} reviewer timestamp must be UTC")
    else:
        try:
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append(f"{label} reviewer timestamp must be valid UTC")


def _common(
    payload: Mapping[str, Any], label: str, expected_version: str, expected_commit: str,
    errors: list[str],
) -> None:
    if payload.get("schemaVersion") != 1:
        errors.append(f"{label} schema version is unsupported")
    if payload.get("pluginVersion") != expected_version:
        errors.append(f"{label} plugin version does not match the candidate")
    if payload.get("commit") != expected_commit:
        errors.append(f"{label} commit does not match the candidate")
    candidate_hash = payload.get("candidateSha256")
    if not isinstance(candidate_hash, str) or SHA256_RE.fullmatch(candidate_hash) is None:
        errors.append(f"{label} candidate hash must be SHA-256")
    _reviewer(payload.get("reviewer"), label, errors)


def _false_assertions(value: Any, required: set[str], label: str, errors: list[str]) -> None:
    assertions = _object(value, f"{label} assertions", errors)
    if assertions is None:
        return
    _closed(assertions, required, f"{label} assertions", errors)
    for field in required:
        if assertions.get(field) is not False:
            errors.append(f"{label} assertion `{field}` must be false")


def _validate_trace(root: Path, reference: Any, errors: list[str]) -> tuple[set[str], dict[str, list[str]]]:
    command_trace = _object(reference, "CLI commandTrace", errors)
    if command_trace is None:
        return set(), {}
    _closed(command_trace, {"path", "sha256"}, "CLI commandTrace", errors)
    path = _resolve_supporting(root, command_trace.get("path"), "CLI command trace", errors)
    if path is None:
        return set(), {}
    _hash_matches(path, command_trace.get("sha256"), "CLI command trace", errors)
    try:
        commands = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        errors.append(f"CLI command trace is not valid JSON: {error}")
        return set(), {}
    if not isinstance(commands, list) or not commands:
        errors.append("CLI command trace must be a non-empty array")
        return set(), {}
    covered: set[str] = set()
    texts: dict[str, list[str]] = {}
    for index, value in enumerate(commands):
        command = _object(value, f"CLI command trace entry {index}", errors)
        if command is None:
            continue
        _closed(command, TRACE_FIELDS, f"CLI command trace entry {index}", errors)
        scenario = command.get("scenarioId")
        if isinstance(scenario, str):
            covered.add(scenario)
        executable = command.get("executable")
        arguments = command.get("arguments")
        if not isinstance(executable, str) or not executable:
            errors.append(f"CLI command trace entry {index} executable is invalid")
        if not isinstance(arguments, list) or not all(isinstance(item, str) for item in arguments):
            errors.append(f"CLI command trace entry {index} arguments are invalid")
            arguments = []
        runtime_text = " ".join([str(executable), *arguments])
        if isinstance(scenario, str):
            texts.setdefault(scenario, []).append(runtime_text.casefold())
        if PROHIBITED_RUNTIME_RE.search(runtime_text):
            errors.append(f"CLI command trace entry {index} uses a prohibited runtime")
        if command.get("exitClass") not in {"success", "expected-failure"}:
            errors.append(f"CLI command trace entry {index} exit class is invalid")
    return covered, texts


def _validate_cli(
    root: Path, payload: Mapping[str, Any], expected_version: str, expected_commit: str,
    errors: list[str], expected_ci_commit: str | None = None, semantic_required: bool = False,
) -> None:
    _closed(payload, CLI_FIELDS, "CLI evidence", errors)
    _common(payload, "CLI evidence", expected_version, expected_commit, errors)
    if payload.get("kind") != "cli":
        errors.append("CLI evidence kind must be `cli`")
    host = _object(payload.get("host"), "CLI host", errors)
    if host is not None:
        _closed(host, {"edition", "build", "architecture", "native"}, "CLI host", errors)
        if host.get("edition") != "Windows 11" or not isinstance(host.get("build"), int) or host["build"] < 22000:
            errors.append("CLI host must be Windows 11 build 22000 or newer")
        if host.get("architecture") not in {"AMD64", "ARM64"} or host.get("native") is not True:
            errors.append("CLI host must be a native supported Windows architecture")
    tools = _object(payload.get("tools"), "CLI tools", errors)
    if tools is not None:
        _closed(tools, {"python", "git", "codex"}, "CLI tools", errors)
        match = re.match(r"^(\d+)\.(\d+)(?:\.\d+)?$", str(tools.get("python", "")))
        if match is None or tuple(map(int, match.groups())) < (3, 10):
            errors.append("CLI Python must be version 3.10 or newer")
        if ".windows." not in str(tools.get("git", "")).casefold():
            errors.append("CLI Git must be Git for Windows")
        if not str(tools.get("codex", "")).strip():
            errors.append("CLI Codex version is required")
    ci = _object(payload.get("ci"), "CLI CI", errors)
    if ci is not None:
        _closed(ci, {"runId", "commit", "conclusion", "runner"}, "CLI CI", errors)
        if not str(ci.get("runId", "")).strip() or ci.get("conclusion") != "success" or ci.get("runner") != "windows-11-arm":
            errors.append("CLI CI evidence must identify a successful windows-11-arm run")
        if ci.get("commit") != (expected_ci_commit or expected_commit):
            errors.append("CLI CI commit does not match the candidate")
    if payload.get("captureVersion") != 1:
        errors.append("CLI capture version is unsupported")
    _false_assertions(payload.get("assertions"), {"wslInvoked", "gitBashInvoked"}, "CLI", errors)
    covered, command_texts = _validate_trace(root, payload.get("commandTrace"), errors)
    if semantic_required:
        for scenario, markers in SCENARIO_COMMAND_MARKERS.items():
            combined = " ".join(command_texts.get(scenario, []))
            if not all(marker.casefold() in combined for marker in markers):
                errors.append(f"CLI command trace lacks concrete `{scenario}` workflow coverage")
    scenarios = payload.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("CLI scenarios must be an array")
        return
    observed: set[str] = set()
    for index, value in enumerate(scenarios):
        scenario = _object(value, f"CLI scenario {index}", errors)
        if scenario is None:
            continue
        _closed(scenario, {"id", "status", "record", "sha256"}, f"CLI scenario {index}", errors)
        scenario_id = scenario.get("id")
        if not isinstance(scenario_id, str) or scenario_id not in REQUIRED_SCENARIOS or scenario_id in observed:
            errors.append(f"CLI scenario {index} has an unknown or duplicate id")
            continue
        observed.add(scenario_id)
        if scenario.get("status") != "pass":
            errors.append(f"CLI evidence has a failing scenario `{scenario_id}`")
        path = _resolve_supporting(root, scenario.get("record"), f"CLI scenario `{scenario_id}` record", errors)
        if path is None:
            continue
        _hash_matches(path, scenario.get("sha256"), f"CLI scenario `{scenario_id}`", errors)
        record = _read_object(path, f"CLI scenario `{scenario_id}` record", errors)
        if record is None:
            continue
        _closed(record, RECORD_FIELDS, f"CLI scenario `{scenario_id}` record", errors)
        if record.get("schemaVersion") != 1 or record.get("scenarioId") != scenario_id:
            errors.append(f"CLI scenario `{scenario_id}` record binding is invalid")
        if record.get("result") != scenario.get("status"):
            errors.append(f"CLI scenario `{scenario_id}` record result is inconsistent")
        if not isinstance(record.get("commandClass"), str) or not record["commandClass"]:
            errors.append(f"CLI scenario `{scenario_id}` command class is invalid")
        if not isinstance(record.get("timestamp"), str) or UTC_RE.fullmatch(record["timestamp"]) is None:
            errors.append(f"CLI scenario `{scenario_id}` timestamp must be UTC")
        if not isinstance(record.get("summary"), str) or not record["summary"]:
            errors.append(f"CLI scenario `{scenario_id}` summary is invalid")
    missing = set(REQUIRED_SCENARIOS) - observed
    if missing:
        errors.append(f"CLI evidence is missing required scenario(s): {', '.join(sorted(missing))}")
    uncovered = set(REQUIRED_SCENARIOS) - covered
    if uncovered:
        errors.append(f"CLI command trace is missing required scenario coverage: {', '.join(sorted(uncovered))}")


def _validate_desktop(
    payload: Mapping[str, Any], expected_version: str, expected_commit: str, errors: list[str],
) -> None:
    _closed(payload, DESKTOP_FIELDS, "desktop evidence", errors)
    _common(payload, "desktop evidence", expected_version, expected_commit, errors)
    if payload.get("kind") != "desktop":
        errors.append("desktop evidence kind must be `desktop`")
    tools = _object(payload.get("tools"), "desktop tools", errors)
    if tools is not None:
        _closed(tools, {"codex"}, "desktop tools", errors)
        if "desktop" not in str(tools.get("codex", "")).casefold():
            errors.append("desktop evidence must identify Codex desktop provenance")
    assertions = _object(payload.get("assertions"), "desktop assertions", errors)
    if assertions is not None:
        _closed(assertions, {"nativeWindows", "wslInvoked", "gitBashInvoked"}, "desktop assertions", errors)
        if assertions.get("nativeWindows") is not True:
            errors.append("desktop evidence must attest native Windows")
        for field in ("wslInvoked", "gitBashInvoked"):
            if assertions.get(field) is not False:
                errors.append(f"desktop assertion `{field}` must be false")
    checklist = payload.get("checklist")
    if not isinstance(checklist, list):
        errors.append("desktop checklist must be an array")
        return
    observed: set[str] = set()
    for index, value in enumerate(checklist):
        item = _object(value, f"desktop checklist item {index}", errors)
        if item is None:
            continue
        _closed(item, {"id", "status"}, f"desktop checklist item {index}", errors)
        item_id = item.get("id")
        if item_id not in DESKTOP_CHECKS or item_id in observed or item.get("status") != "pass":
            errors.append(f"desktop checklist item {index} is unknown, duplicate, or failing")
        elif isinstance(item_id, str):
            observed.add(item_id)
    missing = set(DESKTOP_CHECKS) - observed
    if missing:
        errors.append(f"desktop checklist is incomplete: {', '.join(sorted(missing))}")


def validate_evidence_set(
    root: Path,
    *,
    cli_path: Path | None,
    desktop_path: Path | None,
    expected_version: str,
    expected_commit: str,
    expected_candidate_sha256: str | None = None,
    expected_ci_commit: str | None = None,
    support_claimed: bool = False,
) -> list[str]:
    """Return deterministic validation errors for one exact candidate."""

    root = root.resolve(strict=False)
    errors: list[str] = []
    if VERSION_RE.fullmatch(expected_version) is None:
        errors.append("expected plugin version must be stable semantic versioning")
    if COMMIT_RE.fullmatch(expected_commit) is None:
        errors.append("expected commit must be a full lowercase Git commit")
    if expected_candidate_sha256 is not None and SHA256_RE.fullmatch(expected_candidate_sha256) is None:
        errors.append("expected candidate SHA-256 must be lowercase SHA-256")
    cli: dict[str, Any] | None = None
    desktop: dict[str, Any] | None = None
    if cli_path is None:
        if support_claimed:
            errors.append("CLI evidence is required for a Windows support claim")
    else:
        cli = _read_object(cli_path, "CLI evidence", errors)
        if cli is not None:
            _validate_cli(
                root, cli, expected_version, expected_commit, errors, expected_ci_commit,
                semantic_required=support_claimed,
            )
            if expected_candidate_sha256 is not None and cli.get("candidateSha256") != expected_candidate_sha256:
                errors.append("CLI evidence candidateSha256 does not match the release authority")
    if desktop_path is None:
        if support_claimed:
            errors.append("desktop evidence is required for a Windows support claim")
    else:
        desktop = _read_object(desktop_path, "desktop evidence", errors)
        if desktop is not None:
            _validate_desktop(desktop, expected_version, expected_commit, errors)
            if expected_candidate_sha256 is not None and desktop.get("candidateSha256") != expected_candidate_sha256:
                errors.append("desktop evidence candidateSha256 does not match the release authority")
    if cli is not None and desktop is not None:
        for field in ("pluginVersion", "commit", "candidateSha256"):
            if cli.get(field) != desktop.get(field):
                errors.append(f"CLI and desktop evidence {field} values do not match")
    return errors


def validate_documentation_policy(
    texts: Mapping[str, str], *, support_claimed: bool,
) -> list[str]:
    """Reject unsafe prerequisites and premature native Windows support wording."""

    errors: list[str] = []
    old_python_re = re.compile(r"\bPython\s+3\.(?:[0-9])\b", re.IGNORECASE)
    patch_pin_re = re.compile(r"\bPython\s+3\.\d+\.\d+\b", re.IGNORECASE)
    wsl_removal_re = re.compile(r"\b(?:uninstall|remove)\s+WSL\b", re.IGNORECASE)
    for name, text in sorted(texts.items()):
        if old_python_re.search(text):
            errors.append(f"{name}: Windows Python prerequisite must be 3.10 or newer")
        if patch_pin_re.search(text):
            errors.append(f"{name}: Windows Python prerequisite must not pin a patch release")
        if wsl_removal_re.search(text):
            errors.append(f"{name}: WSL may remain installed; only its execution is prohibited")
        if not support_claimed and WINDOWS_SUPPORT_CLAIM_RE.search(text):
            errors.append(f"{name}: native Windows support claim requires valid retained evidence")
    return errors


def documentation_claims_windows_support(texts: Mapping[str, str]) -> bool:
    """Return whether any public surface makes an affirmative Windows support claim."""

    return any(WINDOWS_SUPPORT_CLAIM_RE.search(text) is not None for text in texts.values())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--desktop", type=Path)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-candidate-sha256")
    parser.add_argument("--expected-ci-commit")
    parser.add_argument("--support-claimed", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    errors = validate_evidence_set(
        args.root,
        cli_path=args.cli,
        desktop_path=args.desktop,
        expected_version=args.expected_version,
        expected_commit=args.expected_commit,
        expected_candidate_sha256=args.expected_candidate_sha256,
        expected_ci_commit=args.expected_ci_commit,
        support_claimed=args.support_claimed,
    )
    if errors:
        print("Windows evidence validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Windows evidence validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
