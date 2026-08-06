"""Pure roadmap parsing, derived status calculation, and rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


FEATURE_PROGRESS = re.compile(r"^(\d+ / \d+ \(\d+%\))(.*)$")
PORTFOLIO_PROGRESS = re.compile(r"^(\d+/\d+ RDs)(.*)$")
FEATURES_HEADER = re.compile(r"^(\d+ / \d+ done)(.*)$")


@dataclass(frozen=True, slots=True)
class RoadmapRows:
    done: int
    total: int
    rows: tuple[tuple[str, str, str], ...]
    open_followon: bool

    @property
    def percentage(self) -> int:
        return round(self.done / self.total * 100) if self.total else 0

    @property
    def status(self) -> str:
        if any("⛔" in status for _, _, status in self.rows):
            return "⛔"
        if self.total and self.done == self.total:
            return "🔄" if self.open_followon else "✅"
        if any("🔄" in status for _, _, status in self.rows):
            return "🔄"
        return "⬜"


@dataclass(frozen=True, slots=True)
class SyncResult:
    layout: str
    drift: tuple[str, ...]
    held: tuple[str, ...]
    rendered: dict[Path, bytes]

    def to_json(self, root: Path) -> dict[str, object]:
        return {
            "result": "drift" if self.drift else "in-sync",
            "layout": self.layout,
            "drift": list(self.drift),
            "held": list(self.held),
            "changed": sorted(path.relative_to(root).as_posix() for path in self.rendered),
        }


def detect_layout(root: Path) -> str:
    marker = root / "codeops" / ".codeops.yml"
    if marker.is_file() and re.search(
        r"(?m)^codeopsLayout:\s*nested\s*$",
        marker.read_text(encoding="utf-8"),
    ):
        return "nested"
    return "flat"


def _rows(text: str) -> tuple[tuple[str, str, str], ...]:
    rows: list[tuple[str, str, str]] = []
    in_table = False
    for line in text.splitlines():
        if re.match(r"\|\s*ID\s*\|", line):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or set(cells[0]) <= {"-", " "}:
            continue
        identity = cells[0]
        if identity.startswith("↳") or identity in {"—", "-", ""}:
            continue
        rows.append((
            identity,
            cells[4] if len(cells) > 4 else "",
            cells[5] if len(cells) > 5 else "",
        ))
    return tuple(rows)


def _open_followon(text: str) -> bool:
    in_section = False
    valid = False
    for line in text.splitlines():
        if re.match(r"^##\s+Open follow-ons\s*$", line):
            in_section = True
            valid = False
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or set(cells[-1]) <= {"-", " "}:
            continue
        if cells[-1] == "Status":
            valid = True
            continue
        if valid and cells[-1] and "✅" not in cells[-1]:
            return True
    return False


def analyze_roadmap(text: str) -> RoadmapRows:
    rows = _rows(text)
    requirements = [row for row in rows if re.match(r"RD-\d", row[0])]
    done = sum(1 for _, stage, status in requirements if "✅" in status or stage.startswith("Done"))
    return RoadmapRows(done, len(requirements), rows, _open_followon(text))


def _computed_header(
    text: str,
    key: str,
    token: str,
    shape: re.Pattern[str],
    path: str,
    drift: list[str],
    held: list[str],
) -> str:
    pattern = re.compile(rf"(?m)^> \*\*{re.escape(key)}\*\*: (.*)$")
    found = pattern.search(text)
    if found is None:
        drift.append(f"{path}: header '> **{key}**:' not found")
        return text
    match = shape.fullmatch(found.group(1))
    if match is None:
        held.append(f"{path}: {key}={found.group(1)}")
        return text
    replacement = token + match.group(2)
    if found.group(1) != replacement:
        drift.append(f"{path}: {key} {found.group(1)} -> {replacement}")
        return text[:found.start(1)] + replacement + text[found.end(1):]
    return text


def _feature_render(path: Path, root: Path, drift: list[str], held: list[str]) -> tuple[str, RoadmapRows, bool]:
    text = path.read_text(encoding="utf-8")
    analysis = analyze_roadmap(text)
    token = f"{analysis.done} / {analysis.total} ({analysis.percentage}%)"
    rendered = _computed_header(
        text,
        "Progress",
        token,
        FEATURE_PROGRESS,
        path.relative_to(root).as_posix(),
        drift,
        held,
    )
    return rendered, analysis, rendered == text and any(
        item.startswith(f"{path.relative_to(root).as_posix()}: Progress=") for item in held
    )


def synchronize(root: Path, today: str) -> SyncResult:
    """Compute all deterministic roadmap rewrites without touching disk."""

    del today  # Dates change only when an owned computed value changes; rendering owns that later.
    root = root.resolve()
    layout = detect_layout(root)
    drift: list[str] = []
    held: list[str] = []
    rendered: dict[Path, bytes] = {}
    if layout == "flat":
        path = root / "plans" / "00-roadmap.md"
        if not path.is_file():
            return SyncResult(layout, (), (), {})
        value, _, _ = _feature_render(path, root, drift, held)
        if value != path.read_text(encoding="utf-8"):
            rendered[path] = value.encode("utf-8")
        return SyncResult(layout, tuple(drift), tuple(held), rendered)

    features: dict[str, tuple[RoadmapRows, bool]] = {}
    for path in sorted((root / "codeops" / "features").glob("*/00-roadmap.md")):
        value, analysis, is_held = _feature_render(path, root, drift, held)
        features[path.parent.name] = (analysis, is_held)
        if value != path.read_text(encoding="utf-8"):
            rendered[path] = value.encode("utf-8")

    portfolio = root / "codeops" / "00-roadmap.md"
    if not portfolio.is_file():
        drift.append("codeops/00-roadmap.md: portfolio is missing")
        return SyncResult(layout, tuple(drift), tuple(held), rendered)
    original = portfolio.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    done_features = 0
    counted_features = 0
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] not in features:
            continue
        name = cells[0]
        analysis, is_held = features[name]
        if is_held or PORTFOLIO_PROGRESS.fullmatch(cells[3]) is None:
            held.append(f"codeops/00-roadmap.md: {name} Progress={cells[3]}")
            continue
        counted_features += 1
        expected_progress = f"{analysis.done}/{analysis.total} RDs"
        progress_match = PORTFOLIO_PROGRESS.fullmatch(cells[3])
        expected_progress += progress_match.group(2)
        expected_status = analysis.status
        if expected_status == "✅":
            done_features += 1
        if cells[3] != expected_progress or cells[4] != expected_status:
            drift.append(
                f"codeops/00-roadmap.md: {name} {cells[3]}/{cells[4]} -> {expected_progress}/{expected_status}"
            )
            cells[3] = expected_progress
            cells[4] = expected_status
            ending = "\n" if line.endswith("\n") else ""
            lines[index] = "| " + " | ".join(cells) + " |" + ending
    value = "".join(lines)
    value = _computed_header(
        value,
        "Features",
        f"{done_features} / {counted_features} done",
        FEATURES_HEADER,
        "codeops/00-roadmap.md",
        drift,
        held,
    )
    if value != original:
        rendered[portfolio] = value.encode("utf-8")
    return SyncResult(layout, tuple(drift), tuple(held), rendered)
