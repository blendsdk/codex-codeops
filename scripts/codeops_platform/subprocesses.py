"""Argument-array subprocess execution with optional sanitized evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
from typing import Mapping, Sequence

from scripts.codeops_state_lib.filesystem import atomic_write_bytes


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Observable result of one shell-free child process."""

    argv: tuple[str, ...]
    exit_code: int
    stdout: str
    stderr: str


def _display_token(value: str) -> str:
    """Remove control characters from evidence without changing execution input."""

    return "".join(character if ord(character) >= 32 else "?" for character in value)


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
    evidence_sink: Path | None = None,
) -> CommandResult:
    """Run a closed argument vector without a command shell."""

    if not argv or any(not isinstance(item, str) or "\x00" in item for item in argv):
        raise ValueError("command arguments must be nonempty strings without NUL")
    completed = subprocess.run(
        list(argv),
        cwd=cwd,
        env=dict(environment) if environment is not None else None,
        text=True,
        capture_output=True,
        check=False,
        shell=False,
    )
    result = CommandResult(
        tuple(argv),
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    if evidence_sink is not None:
        records: list[dict[str, object]] = []
        if evidence_sink.exists():
            records = json.loads(evidence_sink.read_text(encoding="utf-8"))
        records.append({
            "argv": [_display_token(item) for item in argv],
            "cwd": _display_token(str(cwd)),
            "exitCode": completed.returncode,
        })
        atomic_write_bytes(
            evidence_sink,
            (json.dumps(records, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    return result


def run_mutation_preflight(
    root: Path,
    targets: Sequence[Path],
    *,
    entrypoint_code: str,
) -> int:
    """Run the registered Windows mutation gate immediately before mutation."""

    import os

    if os.name != "nt":
        return 0
    plugin_root = os.environ.get("PLUGIN_ROOT")
    plugin_data = os.environ.get("PLUGIN_DATA")
    if not plugin_root or not plugin_data:
        return 1
    from scripts.codeops_windows_lib.models import Readiness
    from scripts.codeops_windows_lib.probes import NativeProbeDependencies
    from scripts.codeops_windows_preflight import run_preflight

    result = run_preflight(
        mode="mutation",
        entrypoint_code=entrypoint_code,
        hook_event=None,
        targets=tuple(targets),
        root=root,
        plugin_root=Path(plugin_root).resolve(strict=False),
        plugin_data=Path(plugin_data).resolve(strict=False),
        session_id=f"direct-{entrypoint_code}-{os.getpid()}",
        environment=dict(os.environ),
        dependencies=NativeProbeDependencies(),
    )
    return 0 if result.status is not Readiness.BLOCKED else result.exit_code
