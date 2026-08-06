#!/usr/bin/env python3
"""Evaluate the closed native Windows prerequisite contract."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Protocol

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.codeops_windows_lib.models import (
    CheckResult,
    PreflightInputError,
    PreflightInternalError,
    PreflightResult,
    Readiness,
)


_CHECK_CODES = (
    "native-windows",
    "windows-version",
    "python-3",
    "git-for-windows",
    "workspace-local",
    "codex-native",
    "sandbox",
    "plugin-enabled",
    "hooks-available",
    "path-filesystem",
)
_REGISTERED_ENTRYPOINTS = frozenset({
    "agent-install",
    "hook-pre-tool-use",
    "layout-migration",
    "outcome-write",
    "roadmap-write",
    "skill-mutation",
    "snapshot-write",
    "state-transition",
    "worktree-mutation",
})
_SESSION_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SEVERITY = {
    Readiness.READY: 0,
    Readiness.WARNING: 1,
    Readiness.BLOCKED: 2,
}


class PreflightDependencies(Protocol):
    """Supply native facts and persistence without exposing test modes to input."""

    def classify_host(self, environment: Mapping[str, str]) -> str:
        """Classify the current process as native Windows, WSL, or unsupported."""

    def evaluate_check(
        self,
        code: str,
        request: Mapping[str, object],
    ) -> CheckResult:
        """Evaluate one stable check code for a validated request."""

    def load_attestation(
        self,
        request: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        """Load a candidate session attestation without granting it authority."""

    def store_attestation(
        self,
        request: Mapping[str, object],
        result: PreflightResult,
    ) -> None:
        """Persist a successful result atomically."""

    def cleanup_attestations(self, request: Mapping[str, object]) -> None:
        """Remove retention-expired orphan attestations."""


def _inside(root: Path, target: Path) -> bool:
    """Return whether an absolute target is contained by the canonical root."""
    try:
        target.relative_to(root)
    except ValueError:
        return False
    return target != root


def _validate_request(
    *,
    mode: str,
    entrypoint_code: str | None,
    hook_event: str | None,
    targets: tuple[Path, ...],
    root: Path,
    plugin_root: Path,
    plugin_data: Path,
    session_id: str,
    environment: Mapping[str, str],
) -> dict[str, object]:
    """Validate and normalize the complete closed request object."""
    if not isinstance(mode, str):
        raise PreflightInputError("preflight mode is malformed")
    if entrypoint_code is not None and not isinstance(entrypoint_code, str):
        raise PreflightInputError("entrypoint code is malformed")
    if hook_event is not None and not isinstance(hook_event, str):
        raise PreflightInputError("hook event is malformed")
    if mode not in {"session", "read", "mutation"}:
        raise PreflightInputError("unknown preflight mode")
    if hook_event not in {None, "SessionStart", "PreToolUse"}:
        raise PreflightInputError("hook event is unknown")
    if not isinstance(session_id, str) or _SESSION_ID.fullmatch(session_id) is None:
        raise PreflightInputError("session ID is malformed")
    if not all(
        isinstance(path, Path) and path.is_absolute()
        for path in (root, plugin_root, plugin_data)
    ):
        raise PreflightInputError("root and plugin paths must be absolute Path values")
    if not isinstance(environment, Mapping) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in environment.items()
    ):
        raise PreflightInputError("environment must contain string keys and values")
    if not isinstance(targets, tuple) or not all(
        isinstance(target, Path) and target.is_absolute() for target in targets
    ):
        raise PreflightInputError("targets must be an absolute Path tuple")

    lexical_root = root.absolute()
    lexical_targets = tuple(target.absolute() for target in targets)
    canonical_root = lexical_root.resolve(strict=False)
    canonical_targets = tuple(target.resolve(strict=False) for target in lexical_targets)
    if mode in {"session", "read"}:
        if entrypoint_code is not None or canonical_targets:
            raise PreflightInputError("session and read modes do not accept mutation inputs")
        if mode == "session" and hook_event != "SessionStart":
            raise PreflightInputError("session mode requires SessionStart hook proof")
        if mode == "read" and hook_event is not None:
            raise PreflightInputError("read mode does not accept hook proof")
    else:
        if hook_event not in {None, "PreToolUse"}:
            raise PreflightInputError("mutation hook proof must be PreToolUse")
        if entrypoint_code not in _REGISTERED_ENTRYPOINTS:
            raise PreflightInputError("mutation entrypoint is missing or unknown")
        if not canonical_targets:
            raise PreflightInputError("mutation requires at least one target")
        if len(set(canonical_targets)) != len(canonical_targets):
            raise PreflightInputError("mutation targets must be unique")
        if not all(_inside(canonical_root, target) for target in canonical_targets):
            raise PreflightInputError("mutation target escapes the workspace root")

    return {
        "mode": mode,
        "entrypointCode": entrypoint_code,
        "hookEvent": hook_event,
        "targets": canonical_targets,
        "lexicalRoot": lexical_root,
        "lexicalTargets": lexical_targets,
        "root": canonical_root,
        "pluginRoot": plugin_root.resolve(strict=False),
        "pluginData": plugin_data.resolve(strict=False),
        "sessionId": session_id,
        "environment": dict(environment),
    }


def _aggregate(checks: tuple[CheckResult, ...]) -> Readiness:
    """Return the greatest readiness severity from an ordered check tuple."""
    return max((check.status for check in checks), key=_SEVERITY.__getitem__)


def _read_result(payload: Mapping[str, object], session_id: str) -> PreflightResult:
    """Restore a read-mode result while removing stale hook authority."""
    cached = PreflightResult.from_payload(payload.get("result"))
    if (
        cached.session_id != session_id
        or cached.status is Readiness.BLOCKED
        or tuple(check.code for check in cached.checks) != _CHECK_CODES
        or cached.status is not _aggregate(cached.checks)
    ):
        raise ValueError("attested result is not reusable")
    checks = tuple(
        (
            CheckResult(
                check.code,
                Readiness.WARNING,
                "Read mode has no current hook proof.",
                None,
            )
            if check.code == "hooks-available"
            else check
        )
        for check in cached.checks
    )
    return PreflightResult(1, _aggregate(checks), session_id, checks)


def run_preflight(
    *,
    mode: str,
    entrypoint_code: str | None,
    hook_event: str | None,
    targets: tuple[Path, ...],
    root: Path,
    plugin_root: Path,
    plugin_data: Path,
    session_id: str,
    environment: Mapping[str, str],
    dependencies: PreflightDependencies,
) -> PreflightResult:
    """Evaluate a validated request using explicit platform dependencies.

    The function performs no subprocess or filesystem probing itself. A caller constructs the
    production dependency object; deterministic tests can supply an in-memory implementation.
    """
    request = _validate_request(
        mode=mode,
        entrypoint_code=entrypoint_code,
        hook_event=hook_event,
        targets=targets,
        root=root,
        plugin_root=plugin_root,
        plugin_data=plugin_data,
        session_id=session_id,
        environment=environment,
    )
    try:
        host = dependencies.classify_host(environment)
        native = CheckResult(
            "native-windows",
            Readiness.READY if host == "native-windows" else Readiness.BLOCKED,
            (
                "CodeOps is running natively on Windows."
                if host == "native-windows"
                else "CodeOps mutation requires native Windows execution."
            ),
            None if host == "native-windows" else "Launch Codex natively on Windows.",
        )
        if host != "native-windows":
            return PreflightResult(1, Readiness.BLOCKED, session_id, (native,))

        attestation = dependencies.load_attestation(request)
        if mode == "read" and attestation is not None:
            try:
                return _read_result(attestation, session_id)
            except (TypeError, ValueError):
                pass
        checks = (native,) + tuple(
            dependencies.evaluate_check(code, request) for code in _CHECK_CODES[1:]
        )
        if tuple(check.code for check in checks) != _CHECK_CODES:
            raise PreflightInternalError("preflight dependency returned an invalid check order")
        result = PreflightResult(1, _aggregate(checks), session_id, checks)
        if result.status is not Readiness.BLOCKED:
            if mode == "session":
                dependencies.cleanup_attestations(request)
            dependencies.store_attestation(request, result)
        return result
    except PreflightInternalError:
        raise
    except Exception:
        raise PreflightInternalError("native prerequisite evaluation failed") from None


class _ClosedArgumentParser(argparse.ArgumentParser):
    """Reject parser failures without echoing caller-controlled values."""

    def error(self, message: str) -> None:
        del message
        raise PreflightInputError("preflight arguments are invalid")


def _parse_cli(argv: list[str]) -> dict[str, object]:
    """Parse the closed non-abbreviated preflight command surface."""
    singleton_flags = {
        "--mode",
        "--entrypoint-code",
        "--hook-event",
        "--root",
        "--plugin-root",
        "--plugin-data",
        "--session-id",
    }
    observed: set[str] = set()
    for token in argv:
        flag = token.split("=", 1)[0]
        if flag in singleton_flags:
            if flag in observed:
                raise PreflightInputError("preflight argument is duplicated")
            observed.add(flag)

    parser = _ClosedArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--entrypoint-code")
    parser.add_argument("--hook-event")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--root", required=True)
    parser.add_argument("--plugin-root", required=True)
    parser.add_argument("--plugin-data", required=True)
    parser.add_argument("--session-id", required=True)
    parsed = parser.parse_args(argv)
    return {
        "mode": parsed.mode,
        "entrypoint_code": parsed.entrypoint_code,
        "hook_event": parsed.hook_event,
        "targets": tuple(Path(target) for target in parsed.target),
        "root": Path(parsed.root),
        "plugin_root": Path(parsed.plugin_root),
        "plugin_data": Path(parsed.plugin_data),
        "session_id": parsed.session_id,
        "environment": dict(os.environ),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the production closed CLI and emit one result or sanitized diagnostic."""
    try:
        arguments = _parse_cli(list(sys.argv[1:] if argv is None else argv))
        from scripts.codeops_windows_lib.probes import NativeProbeDependencies

        result = run_preflight(
            **arguments,
            dependencies=NativeProbeDependencies(),
        )
    except PreflightInputError:
        sys.stderr.write("CodeOps preflight input is invalid.\n")
        return 1
    except PreflightInternalError:
        sys.stderr.write("CodeOps preflight evaluation failed.\n")
        return 1
    sys.stdout.write(result.to_json() + "\n")
    return result.exit_code


__all__ = [
    "PreflightDependencies",
    "PreflightInputError",
    "PreflightInternalError",
    "run_preflight",
]


if __name__ == "__main__":
    raise SystemExit(main())
