"""Shared durable same-directory atomic replacement."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
from typing import Protocol, runtime_checkable

from .paths import validate_transaction_paths


WINDOWS_RETRY_DELAYS = (0.05, 0.10, 0.20, 0.40, 0.75)
_RETRYABLE_WINDOWS_ERRORS = frozenset({32, 33})


@runtime_checkable
class AtomicWriteOps(Protocol):
    def write_temporary_sibling(self, path: Path, data: bytes) -> Path: ...

    def revalidate(self, path: Path, temporary: Path) -> None: ...

    def replace(self, temporary: Path, path: Path) -> None: ...

    def sync_directory(self, parent: Path) -> None: ...

    def sleep(self, delay: float) -> None: ...

    def cleanup_temporary(self, temporary: Path) -> None: ...


class NativeAtomicWriteOps:
    """Native atomic primitives with a repeatable last-moment storage check."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root

    def write_temporary_sibling(self, path: Path, data: bytes) -> Path:
        if not path.parent.is_dir():
            raise FileNotFoundError("atomic-write parent directory does not exist")
        descriptor, raw = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(raw)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            temporary.unlink(missing_ok=True)
            raise
        return temporary

    def revalidate(self, path: Path, temporary: Path) -> None:
        validate_transaction_paths(self.root or path.parent, (path, temporary))

    def replace(self, temporary: Path, path: Path) -> None:
        os.replace(temporary, path)

    def sync_directory(self, parent: Path) -> None:
        try:
            descriptor = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            # Windows does not expose a directory fsync equivalent through os.open.
            pass

    def sleep(self, delay: float) -> None:
        time.sleep(delay)

    def cleanup_temporary(self, temporary: Path) -> None:
        temporary.unlink(missing_ok=True)


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    ops: AtomicWriteOps | None = None,
) -> None:
    """Durably replace a file with bounded Windows sharing/lock retries."""

    if not isinstance(path, Path):
        raise TypeError("atomic-write path must be a pathlib.Path")
    if not isinstance(data, bytes):
        raise TypeError("atomic-write data must be bytes")
    selected = ops or NativeAtomicWriteOps()
    temporary: Path | None = None
    try:
        temporary = selected.write_temporary_sibling(path, data)
        attempt = 0
        while True:
            selected.revalidate(path, temporary)
            try:
                selected.replace(temporary, path)
                break
            except OSError as exc:
                code = getattr(exc, "winerror", None)
                if (
                    code not in _RETRYABLE_WINDOWS_ERRORS
                    or attempt >= len(WINDOWS_RETRY_DELAYS)
                ):
                    raise
                selected.sleep(WINDOWS_RETRY_DELAYS[attempt])
                attempt += 1
        selected.sync_directory(path.parent)
    finally:
        if temporary is not None:
            try:
                selected.cleanup_temporary(temporary)
            except OSError:
                pass
