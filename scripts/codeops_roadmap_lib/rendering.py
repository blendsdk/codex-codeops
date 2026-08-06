"""Mutation-gated roadmap synchronization and compaction writes."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Iterator

from scripts.codeops_platform.subprocesses import run_mutation_preflight
from scripts.codeops_state_lib.filesystem import NativeAtomicWriteOps, atomic_write_bytes

from .model import SyncResult, detect_layout


@dataclass(frozen=True, slots=True)
class CompactResult:
    layout: str
    notes: tuple[str, ...]
    flags: tuple[str, ...]
    rendered: dict[Path, bytes]

    def to_json(self, root: Path) -> dict[str, object]:
        return {
            "result": "drift" if self.notes or self.flags else "in-sync",
            "layout": self.layout,
            "notes": list(self.notes),
            "flags": list(self.flags),
            "changed": sorted(path.relative_to(root).as_posix() for path in self.rendered),
        }


def _roadmaps(root: Path, layout: str) -> tuple[Path, ...]:
    if layout == "flat":
        candidates = [root / "plans" / "00-roadmap.md"]
        candidates.extend(sorted((root / "plans" / "_archive").glob("*/00-roadmap.md")))
    else:
        candidates = [root / "codeops" / "00-roadmap.md"]
        candidates.extend(sorted((root / "codeops" / "features").glob("*/00-roadmap.md")))
        candidates.extend(sorted((root / "codeops" / "_archive").glob("*/00-roadmap.md")))
    return tuple(path for path in candidates if path.is_file())


def _strip_notes(text: str) -> tuple[str, bool]:
    match = re.search(r"(?m)^## Notes\s*$", text)
    if match is None:
        return text, False
    following = re.search(r"(?m)^## (?!Notes\s*$).+$", text[match.end():])
    end = match.end() + following.start() if following is not None else len(text)
    newline = "\r\n" if "\r\n" in text else "\n"
    prefix = text[:match.start()].rstrip()
    suffix = text[end:].lstrip("\r\n")
    rendered = prefix + (newline * 2 + suffix if suffix else newline)
    return rendered, True


def _fat_cells(text: str, relative: str) -> list[str]:
    flags: list[str] = []
    headers: list[str] | None = None
    for line in text.splitlines():
        if not line.startswith("|"):
            headers = None
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if not cells or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        identity = cells[0] if cells else "?"
        for index, cell in enumerate(cells):
            if len(cell) > 200:
                column = headers[index] if index < len(headers) else str(index + 1)
                flags.append(f"{relative}:{identity}:{column} ({len(cell)} chars)")
    return flags


def compact(root: Path) -> CompactResult:
    """Compute heading-anchored Notes removal and fat-cell diagnostics."""

    root = root.resolve()
    layout = detect_layout(root)
    notes: list[str] = []
    flags: list[str] = []
    rendered: dict[Path, bytes] = {}
    for path in _roadmaps(root, layout):
        relative = path.relative_to(root).as_posix()
        original = path.read_bytes().decode("utf-8")
        value, removed = _strip_notes(original)
        if removed:
            notes.append(relative)
            rendered[path] = value.encode("utf-8")
        flags.extend(_fat_cells(value, relative))
    return CompactResult(layout, tuple(notes), tuple(flags), rendered)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@contextmanager
def _exclusive_transaction_lock(root: Path) -> Iterator[bool]:
    """Use a host-native advisory lock whose ownership dies with the process."""

    lock_dir = Path(tempfile.gettempdir()) / "codeops-roadmap-locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(root).encode("utf-8")).hexdigest()
    handle = (lock_dir / f"{key}.lock").open("a+b")
    acquired = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            acquired = False
        yield acquired
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _clear_transaction(state: Path, journal: Path) -> bool:
    """Remove the journal commit point first, then best-effort orphan evidence."""

    try:
        journal.unlink(missing_ok=True)
    except OSError:
        return False
    try:
        if state.is_dir():
            for path in sorted(state.iterdir()):
                path.unlink(missing_ok=True)
            state.rmdir()
    except OSError:
        pass
    return True


def _recover_transaction(
    root: Path,
    state: Path,
    journal: Path,
    writer: NativeAtomicWriteOps,
) -> tuple[bool, bool]:
    """Validate and roll back one crashed transaction while holding the OS lock."""

    if not state.exists():
        return True, False
    if not journal.is_file():
        return _clear_transaction(state, journal), False
    try:
        payload = json.loads(journal.read_text(encoding="utf-8"))
        if set(payload) != {"schema", "targets", "beforeHashes", "afterHashes"}:
            raise ValueError("roadmap transaction journal is open-ended")
        targets = payload["targets"]
        before_hashes = payload["beforeHashes"]
        after_hashes = payload["afterHashes"]
        if payload["schema"] != 1 or not all(isinstance(item, list) for item in (targets, before_hashes, after_hashes)):
            raise ValueError("roadmap transaction journal schema is invalid")
        if not targets or len(targets) != len(set(targets)) or not (len(targets) == len(before_hashes) == len(after_hashes)):
            raise ValueError("roadmap transaction target cardinality is invalid")
        canonical = {path.resolve() for path in _roadmaps(root, detect_layout(root))}
        destinations: list[Path] = []
        images: list[bytes] = []
        expected_files = {journal.name}
        for index, value in enumerate(targets):
            if not isinstance(value, str) or not isinstance(before_hashes[index], str) or not isinstance(after_hashes[index], str):
                raise ValueError("roadmap transaction entry is malformed")
            destination = (root / value).resolve(strict=False)
            destination.relative_to(root)
            if destination not in canonical:
                raise ValueError("roadmap transaction target is not a canonical roadmap")
            before_path = state / f"{index}.before"
            after_path = state / f"{index}.after"
            before = before_path.read_bytes()
            after = after_path.read_bytes()
            if _digest(before) != before_hashes[index] or _digest(after) != after_hashes[index]:
                raise ValueError("roadmap transaction image hash mismatch")
            if _digest(destination.read_bytes()) not in {before_hashes[index], after_hashes[index]}:
                raise ValueError("roadmap transaction destination has an unknown state")
            destinations.append(destination)
            images.append(before)
            expected_files.update({before_path.name, after_path.name})
        if {path.name for path in state.iterdir()} != expected_files:
            raise ValueError("roadmap transaction namespace contains unexpected files")
        for destination, before in zip(destinations, images, strict=True):
            atomic_write_bytes(destination, before, ops=writer)
        return _clear_transaction(state, journal), True
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return False, False


def write_rendered(root: Path, rendered: dict[Path, bytes]) -> int:
    """Gate and transactionally publish a complete roadmap render set.

    Exit 4 means a crashed write was rolled back and the caller must recompute before retrying.
    """

    root = root.resolve()
    data_by_target = {path.resolve(): data for path, data in rendered.items()}
    targets = tuple(sorted(data_by_target, key=lambda path: path.as_posix()))
    state = root / ".codeops-roadmap-transaction"
    journal = state / "active.json"
    declared = tuple(dict.fromkeys((*targets, *_roadmaps(root, detect_layout(root)), state, journal)))
    if (targets or state.exists()) and run_mutation_preflight(
        root,
        declared,
        entrypoint_code="roadmap-write",
    ) != 0:
        return 2
    if not targets and not state.exists():
        return 0
    writer = NativeAtomicWriteOps(root)
    with _exclusive_transaction_lock(root) as acquired:
        if not acquired:
            return 3
        recovered_ok, recovered = _recover_transaction(root, state, journal, writer)
        if not recovered_ok:
            return 3
        if recovered:
            return 4
        if not targets:
            return 0
        state.mkdir()
        relative_targets = [path.relative_to(root).as_posix() for path in targets]
        before_images = [path.read_bytes() for path in targets]
        after_images = [data_by_target[path] for path in targets]
        try:
            for index, (before, after) in enumerate(zip(before_images, after_images, strict=True)):
                atomic_write_bytes(state / f"{index}.before", before, ops=writer)
                atomic_write_bytes(state / f"{index}.after", after, ops=writer)
            atomic_write_bytes(
                journal,
                (json.dumps({
                    "schema": 1,
                    "targets": relative_targets,
                    "beforeHashes": [_digest(data) for data in before_images],
                    "afterHashes": [_digest(data) for data in after_images],
                }, indent=2, sort_keys=True) + "\n").encode("utf-8"),
                ops=writer,
            )
            for index, path in enumerate(targets):
                atomic_write_bytes(path, (state / f"{index}.after").read_bytes(), ops=writer)
        except BaseException as exc:
            restored, _ = _recover_transaction(root, state, journal, writer)
            if not isinstance(exc, Exception):
                raise
            return 1 if restored else 3
        return 0 if _clear_transaction(state, journal) else 3


def sync_payload(result: SyncResult, root: Path) -> dict[str, object]:
    return result.to_json(root)
