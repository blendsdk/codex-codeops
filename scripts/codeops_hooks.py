#!/usr/bin/env python3
"""Portable SessionStart and PreToolUse hook orchestration."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Protocol


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


_EVENTS = frozenset({"SessionStart", "PreToolUse"})
_PATCH_TARGET = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
_PATCH_MOVE = re.compile(r"^\*\*\* Move to: (.+)$", re.MULTILINE)


@dataclass(frozen=True, slots=True)
class HookResult:
    """Stable process result for one portable hook invocation."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""


class HookDependencies(Protocol):
    """Provide prerequisite, context, and marker behavior to the orchestrator."""

    def run_preflight(self, mode: str, payload: Mapping[str, object]) -> int:
        """Run the appropriate prerequisite gate and return its stable exit."""

    def render_session_context(self, payload: Mapping[str, object]) -> str:
        """Render the durable session context after successful preflight."""

    def run_marker_guard(self, payload: Mapping[str, object]) -> str:
        """Return a marker warning, or an empty string when no warning applies."""


def _validated_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Copy only documented hook fields after validating event-specific inputs."""
    if not isinstance(payload, Mapping):
        raise ValueError("hook payload must be an object")
    event = payload.get("hook_event_name")
    if event not in _EVENTS:
        raise ValueError("hook event is missing or unknown")
    common = ("session_id", "cwd", "hook_event_name", "model", "permission_mode")
    required = ("session_id", "cwd", "hook_event_name")
    if not all(isinstance(payload.get(name), str) for name in required):
        raise ValueError("hook identity fields are malformed")
    allowed = common + (
        ("source",)
        if event == "SessionStart"
        else ("turn_id", "tool_name", "tool_input")
    )
    validated = {name: payload[name] for name in allowed if name in payload}
    if event == "PreToolUse":
        if not isinstance(validated.get("tool_name"), str) or not isinstance(
            validated.get("tool_input"), Mapping
        ):
            raise ValueError("tool payload is malformed")
    return validated


def run_hook(
    payload: Mapping[str, object],
    dependencies: HookDependencies,
) -> HookResult:
    """Run preflight before the event's existing portable behavior."""
    try:
        validated = _validated_payload(payload)
        event = validated["hook_event_name"]
        mode = "session" if event == "SessionStart" else "mutation"
        preflight_exit = dependencies.run_preflight(mode, validated)
        if preflight_exit != 0:
            return HookResult(preflight_exit, stderr="CodeOps prerequisite check blocked the hook.\n")
        if event == "SessionStart":
            context = dependencies.render_session_context(validated)
            return HookResult(0, stdout=context.rstrip("\n") + "\n")
        warning = dependencies.run_marker_guard(validated)
        return HookResult(0, stderr=(warning.rstrip("\n") + "\n") if warning else "")
    except Exception:
        return HookResult(1, stderr="CodeOps hook input or runtime state is invalid.\n")


class NativeHookDependencies:
    """Production hook behavior with Windows-only prerequisite enforcement."""

    def run_preflight(self, mode: str, payload: Mapping[str, object]) -> int:
        """Run native Windows checks while retaining Unix compatibility behavior."""
        if os.name != "nt":
            return 0
        from scripts.codeops_windows_lib.probes import NativeProbeDependencies
        from scripts.codeops_windows_preflight import run_preflight

        root = Path(str(payload["cwd"])).resolve(strict=False)
        plugin_root = Path(os.environ["PLUGIN_ROOT"]).resolve(strict=False)
        plugin_data = Path(os.environ["PLUGIN_DATA"]).resolve(strict=False)
        event = str(payload["hook_event_name"])
        targets = () if mode == "session" else self._mutation_targets(root, payload)
        result = run_preflight(
            mode=mode,
            entrypoint_code=None if mode == "session" else "hook-pre-tool-use",
            hook_event=event,
            targets=targets,
            root=root,
            plugin_root=plugin_root,
            plugin_data=plugin_data,
            session_id=str(payload["session_id"]),
            environment=dict(os.environ),
            dependencies=NativeProbeDependencies(),
        )
        return result.exit_code

    def render_session_context(self, payload: Mapping[str, object]) -> str:
        """Render the two existing standards documents in their established order."""
        del payload
        plugin_root = Path(os.environ["PLUGIN_ROOT"])
        coding = (plugin_root / "standards" / "coding-standards.md").read_text(
            encoding="utf-8"
        )
        output = (plugin_root / "standards" / "output-style.md").read_text(
            encoding="utf-8"
        )
        return f"{coding.rstrip()}\n\n{output.rstrip()}\n"

    def run_marker_guard(self, payload: Mapping[str, object]) -> str:
        """Preserve the non-blocking layout-marker warning."""
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if "codeops/.codeops.yml" not in serialized:
            return ""
        return (
            "CodeOps warning: codeops/.codeops.yml is the layout marker and is owned by "
            "setup-codeops; edit it only through the setup/migration workflow."
        )

    def _mutation_targets(
        self,
        root: Path,
        payload: Mapping[str, object],
    ) -> tuple[Path, ...]:
        """Extract the complete declared target set for supported write-hook tools."""
        tool = payload.get("tool_name")
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, Mapping):
            raise ValueError("tool input is malformed")
        raw_targets: list[str]
        if tool in {"Edit", "Write"}:
            candidate = tool_input.get("file_path", tool_input.get("path"))
            if not isinstance(candidate, str):
                raise ValueError("write target is missing")
            raw_targets = [candidate]
        elif tool == "apply_patch":
            patch = tool_input.get("patch")
            if not isinstance(patch, str):
                raise ValueError("patch input is malformed")
            raw_targets = _PATCH_TARGET.findall(patch) + _PATCH_MOVE.findall(patch)
        else:
            raise ValueError("write-hook tool is unknown")
        if not raw_targets:
            raise ValueError("mutation target set is empty")
        return tuple(
            (Path(target) if Path(target).is_absolute() else root / target).resolve(strict=False)
            for target in raw_targets
        )


def _payload_from_stdin(event: str | None) -> Mapping[str, object]:
    """Read one JSON payload, allowing a SessionStart-only Unix compatibility fallback."""
    raw = sys.stdin.read().lstrip("\ufeff")
    if raw.strip():
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("hook payload must be an object")
        if event is not None and payload.get("hook_event_name") != event:
            raise ValueError("launcher event does not match hook payload")
        return payload
    if event != "SessionStart":
        raise ValueError("hook payload is missing")
    return {
        "session_id": "unix-compat",
        "cwd": str(Path.cwd()),
        "hook_event_name": "SessionStart",
    }


def main(argv: list[str] | None = None) -> int:
    """Run the production portable hook CLI."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--event", choices=sorted(_EVENTS))
    try:
        arguments = parser.parse_args(argv)
        payload = _payload_from_stdin(arguments.event)
        result = run_hook(payload, NativeHookDependencies())
    except (SystemExit, json.JSONDecodeError, OSError, TypeError, ValueError):
        result = HookResult(1, stderr="CodeOps hook input or runtime state is invalid.\n")
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["HookDependencies", "HookResult", "run_hook"]
