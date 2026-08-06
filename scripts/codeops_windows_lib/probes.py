"""Native Windows prerequisite probes behind the orchestration dependency protocol."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence

from scripts.codeops_platform.hosts import classify_process_host
from scripts.codeops_windows_lib.models import CheckResult, PreflightResult, Readiness


_DRIVE_FIXED = 3
_WINDOWS_11_MINIMUM_BUILD = 22000


def _result(
    code: str,
    status: Readiness,
    message: str,
    remediation: str | None = None,
) -> CheckResult:
    """Build one probe result with a stable code and sanitized text."""
    return CheckResult(code, status, message, remediation)


def _run(arguments: Sequence[str], *, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    """Run a fixed argument array without shell evaluation or inherited stdin."""
    return subprocess.run(
        list(arguments),
        stdin=subprocess.DEVNULL,
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def _windows_volume(path: Path) -> tuple[str, str, int]:
    """Return volume root, filesystem name, and drive type for an existing path."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    root_buffer = ctypes.create_unicode_buffer(261)
    if not kernel32.GetVolumePathNameW(str(path), root_buffer, len(root_buffer)):
        raise OSError(ctypes.get_last_error(), "cannot resolve the workspace volume")
    filesystem_buffer = ctypes.create_unicode_buffer(261)
    if not kernel32.GetVolumeInformationW(
        root_buffer.value,
        None,
        0,
        None,
        None,
        None,
        filesystem_buffer,
        len(filesystem_buffer),
    ):
        raise OSError(ctypes.get_last_error(), "cannot query the workspace filesystem")
    drive_type = int(kernel32.GetDriveTypeW(root_buffer.value))
    return root_buffer.value, filesystem_buffer.value, drive_type


def _has_reparse_component(path: Path) -> bool:
    """Return whether an existing component from the volume root is a reparse point."""
    resolved = path.absolute()
    current = Path(resolved.anchor)
    for component in resolved.parts[1:]:
        current /= component
        if not current.exists():
            break
        attributes = getattr(current.lstat(), "st_file_attributes", 0)
        if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            return True
    return False


def _is_administrator() -> bool:
    """Return whether the current Windows token is elevated enough for admin operations."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


class NativeProbeDependencies:
    """Production host and prerequisite probes for the native evaluator.

    Attestation persistence is deliberately inert until the dedicated persistence component is
    installed. The command entrypoint is added only after that component can store successful
    results atomically.
    """

    def classify_host(self, environment: Mapping[str, str]) -> str:
        """Return the passive process-host classification."""
        return classify_process_host(environment).value

    def evaluate_check(
        self,
        code: str,
        request: Mapping[str, object],
    ) -> CheckResult:
        """Evaluate one stable prerequisite code against validated request facts."""
        probes = {
            "windows-version": self._windows_version,
            "python-3": self._python,
            "git-for-windows": self._git,
            "workspace-local": self._workspace,
            "codex-native": self._codex,
            "sandbox": self._sandbox,
            "plugin-enabled": self._plugin,
            "hooks-available": self._hooks,
            "path-filesystem": self._path_filesystem,
        }
        probe = probes.get(code)
        if probe is None:
            return _result(code, Readiness.BLOCKED, "Unknown prerequisite check.")
        try:
            return probe(request)
        except (OSError, ValueError, subprocess.SubprocessError):
            return _result(
                code,
                Readiness.BLOCKED,
                "The prerequisite could not be established safely.",
                "Review the native Windows prerequisite and retry.",
            )

    def load_attestation(
        self,
        request: Mapping[str, object],
    ) -> Mapping[str, object] | None:
        """Return no cache until atomic attestation persistence is installed."""
        del request
        return None

    def store_attestation(
        self,
        request: Mapping[str, object],
        result: PreflightResult,
    ) -> None:
        """Refuse production persistence until the atomic attestation store is installed."""
        del request, result
        raise RuntimeError("attestation persistence is not installed")

    def cleanup_attestations(self) -> None:
        """Perform no cleanup until the atomic attestation store is installed."""

    def _windows_version(self, request: Mapping[str, object]) -> CheckResult:
        del request
        version = sys.getwindowsversion()
        if version.major == 10 and version.build >= _WINDOWS_11_MINIMUM_BUILD:
            return _result("windows-version", Readiness.READY, "Windows 11 is active.")
        return _result(
            "windows-version",
            Readiness.BLOCKED,
            "This Windows version is not supported.",
            "Run CodeOps on Windows 11.",
        )

    def _python(self, request: Mapping[str, object]) -> CheckResult:
        del request
        if sys.version_info >= (3, 10):
            return _result("python-3", Readiness.READY, "Python 3.10 or newer is active.")
        return _result(
            "python-3",
            Readiness.BLOCKED,
            "Python 3.10 or newer is required.",
            "Install or select a supported native Python interpreter.",
        )

    def _git(self, request: Mapping[str, object]) -> CheckResult:
        del request
        executable = shutil.which("git")
        if executable is None:
            return _result(
                "git-for-windows",
                Readiness.BLOCKED,
                "Native Git was not found.",
                "Install Git for Windows and add it to PATH.",
            )
        result = _run((executable, "--version"))
        if result.returncode == 0 and ".windows." in result.stdout.casefold():
            return _result("git-for-windows", Readiness.READY, "Git for Windows is active.")
        return _result(
            "git-for-windows",
            Readiness.BLOCKED,
            "The resolved Git command is not Git for Windows.",
            "Select the native Git for Windows executable.",
        )

    def _workspace(self, request: Mapping[str, object]) -> CheckResult:
        root = request["root"]
        if not isinstance(root, Path) or not root.is_dir() or not os.access(root, os.W_OK):
            return _result(
                "workspace-local",
                Readiness.BLOCKED,
                "The workspace is missing or not writable.",
            )
        _, filesystem, drive_type = _windows_volume(root)
        if drive_type == _DRIVE_FIXED and filesystem.casefold() == "ntfs":
            return _result(
                "workspace-local",
                Readiness.READY,
                "The workspace is on writable fixed local NTFS.",
            )
        return _result(
            "workspace-local",
            Readiness.BLOCKED,
            "The workspace is not on fixed local NTFS.",
            "Move the repository to a fixed local NTFS volume.",
        )

    def _codex(self, request: Mapping[str, object]) -> CheckResult:
        del request
        executable = shutil.which("codex")
        if executable is None or Path(executable).suffix.casefold() != ".exe":
            return _result(
                "codex-native",
                Readiness.BLOCKED,
                "The native Codex executable was not found.",
            )
        version = _run((executable, "--version"))
        help_result = _run((executable, "--help"))
        help_text = help_result.stdout.casefold()
        if (
            version.returncode == 0
            and help_result.returncode == 0
            and "sandbox" in help_text
            and "plugin" in help_text
        ):
            return _result("codex-native", Readiness.READY, "Native Codex capabilities are available.")
        return _result(
            "codex-native",
            Readiness.BLOCKED,
            "Required native Codex capabilities are unavailable.",
            "Update Codex and verify its plugin and sandbox commands.",
        )

    def _sandbox(self, request: Mapping[str, object]) -> CheckResult:
        del request
        executable = shutil.which("codex")
        if executable is None:
            return _result("sandbox", Readiness.BLOCKED, "Native Codex sandbox is unavailable.")
        interpreter = "py" if shutil.which("py") is not None else "python"
        interpreter_arguments = (
            ("-3", "-c", "pass") if interpreter == "py" else ("-c", "pass")
        )
        result = _run(
            (executable, "sandbox", "--", interpreter, *interpreter_arguments),
            timeout=30.0,
        )
        if result.returncode != 0:
            return _result(
                "sandbox",
                Readiness.BLOCKED,
                "The native Codex sandbox probe failed.",
                "Run Codex doctor and repair the native sandbox.",
            )
        if _is_administrator():
            return _result("sandbox", Readiness.READY, "The native sandbox is operational.")
        return _result(
            "sandbox",
            Readiness.WARNING,
            "The native sandbox is operational without elevation.",
            "Elevation is optional unless a later operation requires it.",
        )

    def _plugin(self, request: Mapping[str, object]) -> CheckResult:
        plugin_root = request["pluginRoot"]
        plugin_data = request["pluginData"]
        if not isinstance(plugin_root, Path) or not isinstance(plugin_data, Path):
            raise ValueError("validated plugin paths are missing")
        manifest = plugin_root / ".codex-plugin" / "plugin.json"
        if not manifest.is_file() or not plugin_data.is_dir() or not os.access(plugin_data, os.W_OK):
            return _result(
                "plugin-enabled",
                Readiness.BLOCKED,
                "Plugin root or writable plugin data is unavailable.",
            )
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(payload.get("name"), str) or not isinstance(payload.get("version"), str):
            return _result("plugin-enabled", Readiness.BLOCKED, "Plugin identity is malformed.")
        return _result("plugin-enabled", Readiness.READY, "Plugin identity and data path are coherent.")

    def _hooks(self, request: Mapping[str, object]) -> CheckResult:
        plugin_root = request["pluginRoot"]
        hook_event = request["hookEvent"]
        if not isinstance(plugin_root, Path):
            raise ValueError("validated plugin root is missing")
        manifest = plugin_root / "hooks" / "hooks.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        hooks = payload.get("hooks")
        if not isinstance(hooks, dict):
            return _result("hooks-available", Readiness.BLOCKED, "Hook manifest is malformed.")
        for event in ("SessionStart", "PreToolUse"):
            entries = hooks.get(event)
            try:
                command = entries[0]["hooks"][0]["commandWindows"]
            except (KeyError, IndexError, TypeError):
                return _result(
                    "hooks-available",
                    Readiness.BLOCKED,
                    "Native Windows hook registration is incomplete.",
                )
            if not isinstance(command, str) or "wsl" in command.casefold() or "bash" in command.casefold():
                return _result(
                    "hooks-available",
                    Readiness.BLOCKED,
                    "Native Windows hook registration is unsafe.",
                )
        if hook_event in {"SessionStart", "PreToolUse"}:
            return _result("hooks-available", Readiness.READY, "Trusted hook proof is present.")
        return _result(
            "hooks-available",
            Readiness.WARNING,
            "No hook proof is present; the registered command boundary remains authoritative.",
        )

    def _path_filesystem(self, request: Mapping[str, object]) -> CheckResult:
        root = request["root"]
        if not isinstance(root, Path):
            raise ValueError("validated workspace root is missing")
        if _has_reparse_component(root):
            return _result(
                "path-filesystem",
                Readiness.BLOCKED,
                "The workspace root contains a reparse component.",
                "Use a direct local NTFS path without junctions or symbolic links.",
            )
        return _result(
            "path-filesystem",
            Readiness.READY,
            "Workspace root components are reparse-free.",
        )
