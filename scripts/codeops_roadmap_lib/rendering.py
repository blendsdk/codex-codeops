"""Mutation-gated roadmap synchronization and compaction writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

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


def write_rendered(root: Path, rendered: dict[Path, bytes]) -> int:
    """Gate and atomically publish a complete roadmap render set."""

    if not rendered:
        return 0
    root = root.resolve()
    targets = tuple(sorted(rendered, key=lambda path: path.as_posix()))
    if run_mutation_preflight(root, targets, entrypoint_code="roadmap-write") != 0:
        return 2
    writer = NativeAtomicWriteOps(root)
    for path in targets:
        atomic_write_bytes(path, rendered[path], ops=writer)
    return 0


def sync_payload(result: SyncResult, root: Path) -> dict[str, object]:
    return result.to_json(root)
