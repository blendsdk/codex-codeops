"""Argument-array subprocess execution with optional sanitized evidence."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Iterator, Mapping, Sequence

from scripts.codeops_state_lib.filesystem import atomic_write_bytes


COMMAND_EVIDENCE_ENV = "CODEOPS_COMMAND_EVIDENCE"


@contextmanager
def exclusive_path_lock(path: Path) -> Iterator[None]:
    """Serialize writers by canonical destination using a process-owned OS lock."""

    lock_dir = Path(tempfile.gettempdir()) / "codeops-path-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(path.resolve(strict=False)).encode("utf-8")).hexdigest()
    handle = (lock_dir / f"{key}.lock").open("a+b")
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def _configured_evidence_sink(environment: Mapping[str, str] | None) -> Path | None:
    """Resolve an explicitly inherited absolute command-evidence destination."""

    source = environment if environment is not None else os.environ
    raw = source.get(COMMAND_EVIDENCE_ENV)
    if raw is None:
        return None
    sink = Path(raw)
    if not sink.is_absolute() or sink.name in {"", ".", ".."}:
        raise ValueError(f"{COMMAND_EVIDENCE_ENV} must be an absolute file path")
    return sink.resolve(strict=False)


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
        encoding="utf-8",
        errors="replace",
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
    selected_sink = evidence_sink or _configured_evidence_sink(environment)
    if selected_sink is not None:
        selected_sink = selected_sink.resolve(strict=False)
        selected_sink.parent.mkdir(parents=True, exist_ok=True)
        with exclusive_path_lock(selected_sink):
            records: list[dict[str, object]] = []
            if selected_sink.exists():
                value = json.loads(selected_sink.read_text(encoding="utf-8"))
                if not isinstance(value, list):
                    raise ValueError("command evidence must be a JSON array")
                records = value
            records.append({
                "argv": [_display_token(item) for item in argv],
                "cwd": _display_token(str(cwd)),
                "exitCode": completed.returncode,
            })
            atomic_write_bytes(
                selected_sink,
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
