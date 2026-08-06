"""Session-bound native prerequisite attestations with atomic local persistence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from scripts.codeops_windows_lib.models import PreflightResult


_FUTURE_SKEW = timedelta(minutes=5)
_ORPHAN_RETENTION = timedelta(days=7)


def _utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def _parse_time(raw: object) -> datetime | None:
    """Parse one ISO timestamp as aware UTC, rejecting ambiguous local values."""
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC)


def _command_version(executable: str) -> str:
    """Return a sanitized single-line executable version or an empty value."""
    try:
        result = subprocess.run(
            (executable, "--version"),
            stdin=subprocess.DEVNULL,
            text=True,
            capture_output=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""


class AttestationStore:
    """Validate, retain, and atomically replace same-session attestation records."""

    def __init__(self, now: Callable[[], datetime] = _utc_now) -> None:
        """Create a store with an injectable aware UTC clock."""
        self._now = now

    def load(self, request: Mapping[str, object]) -> Mapping[str, object] | None:
        """Return a fully bound, non-future record or no cache candidate."""
        try:
            path = self._path(request)
            payload = json.loads(path.read_text(encoding="utf-8"))
            expected_binding = self._binding(request)
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            return None
        if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
            return None
        created = _parse_time(payload.get("createdAt"))
        now = self._aware_now()
        if created is None or created > now + _FUTURE_SKEW:
            return None
        if payload.get("binding") != expected_binding:
            return None
        result = payload.get("result")
        if not isinstance(result, dict):
            return None
        return payload

    def store(self, request: Mapping[str, object], result: PreflightResult) -> None:
        """Atomically persist a successful result in its contained session directory."""
        path = self._path(request)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schemaVersion": 1,
            "createdAt": self._aware_now().isoformat().replace("+00:00", "Z"),
            "binding": self._binding(request),
            "result": result.to_payload(),
        }
        descriptor, raw_temporary = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(raw_temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def cleanup(self, request: Mapping[str, object]) -> None:
        """Remove only orphan JSON records whose filesystem age exceeds retention."""
        sessions = self._sessions_directory(request)
        if not sessions.is_dir():
            return
        cutoff = self._aware_now() - _ORPHAN_RETENTION
        for candidate in sessions.glob("*.json"):
            try:
                modified = datetime.fromtimestamp(candidate.stat().st_mtime, UTC)
                if modified < cutoff:
                    candidate.unlink()
            except OSError:
                continue

    def _aware_now(self) -> datetime:
        """Return the injected time normalized to UTC and reject naive clocks."""
        value = self._now()
        if value.tzinfo is None:
            raise ValueError("attestation clock must be timezone-aware")
        return value.astimezone(UTC)

    def _sessions_directory(self, request: Mapping[str, object]) -> Path:
        """Resolve the contained sessions directory from a validated request."""
        plugin_data = request.get("pluginData")
        if not isinstance(plugin_data, Path) or not plugin_data.is_absolute():
            raise ValueError("validated plugin data path is missing")
        return plugin_data / "preflight" / "sessions"

    def _path(self, request: Mapping[str, object]) -> Path:
        """Resolve one allowlisted session filename beneath plugin data."""
        session_id = request.get("sessionId")
        if not isinstance(session_id, str):
            raise ValueError("validated session ID is missing")
        sessions = self._sessions_directory(request)
        path = sessions / f"{session_id}.json"
        if path.parent != sessions:
            raise ValueError("attestation path escapes its session directory")
        return path

    def _binding(self, request: Mapping[str, object]) -> dict[str, Any]:
        """Build the complete environment and plugin identity binding."""
        plugin_root = request.get("pluginRoot")
        root = request.get("root")
        session_id = request.get("sessionId")
        if not isinstance(plugin_root, Path) or not isinstance(root, Path):
            raise ValueError("validated root paths are missing")
        plugin_manifest = plugin_root / ".codex-plugin" / "plugin.json"
        hook_manifest = plugin_root / "hooks" / "hooks.json"
        plugin = json.loads(plugin_manifest.read_text(encoding="utf-8"))
        git = shutil.which("git") or ""
        return {
            "sessionId": session_id,
            "pluginVersion": plugin.get("version"),
            "pluginRoot": str(plugin_root.resolve(strict=False)),
            "workspaceRoot": str(root.resolve(strict=False)),
            "osIdentity": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
            "pythonExecutable": str(Path(sys.executable).resolve(strict=False)),
            "pythonVersion": platform.python_version(),
            "gitExecutable": str(Path(git).resolve(strict=False)) if git else "",
            "gitVersion": _command_version(git) if git else "",
            "hookDigest": hashlib.sha256(hook_manifest.read_bytes()).hexdigest(),
        }
