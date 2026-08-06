"""Read-only discovery and planning for layout migration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True, slots=True)
class Move:
    """One canonical project-relative migration move."""

    source: str
    target: str

    def to_json(self) -> dict[str, str]:
        return {"source": self.source, "target": self.target}


@dataclass(frozen=True, slots=True)
class MigrationPreview:
    """Complete deterministic preview of a flat-layout migration."""

    feature: str
    feature_source: str
    moves: tuple[Move, ...]
    warnings: tuple[str, ...]
    already_migrated: bool = False

    def to_json(self) -> dict[str, object]:
        return {
            "result": "already-migrated" if self.already_migrated else "preview",
            "feature": self.feature,
            "featureSource": self.feature_source,
            "moves": [move.to_json() for move in self.moves],
            "warnings": list(self.warnings),
        }


def slugify(value: str) -> str:
    """Create one lowercase ASCII path component from display text."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not slug:
        raise ValueError("cannot derive a safe feature slug")
    return slug


def _feature(root: Path) -> tuple[str, str]:
    roadmap = root / "plans" / "00-roadmap.md"
    if roadmap.is_file():
        for line in roadmap.read_text(encoding="utf-8").splitlines():
            marker = "> **Feature-Set**:"
            if line.startswith(marker):
                value = line[len(marker):].strip()
                if value:
                    return slugify(value), "roadmap-header"
    return slugify(root.name), "dir-name"


def _source_link_warnings(root: Path) -> list[str]:
    warnings: list[str] = []
    plans = root / "plans"
    link_pattern = re.compile(r"\]\(([^)]+)\)")
    for path in sorted(plans.rglob("*.md")) if plans.is_dir() else ():
        relative = path.relative_to(root).as_posix()
        for target in link_pattern.findall(path.read_text(encoding="utf-8", errors="replace")):
            target = target.strip()
            if not target.startswith(".."):
                continue
            resolved = (path.parent / target).resolve(strict=False)
            try:
                local = resolved.relative_to(root).as_posix()
            except ValueError:
                local = ""
            if not (local == "plans" or local.startswith("plans/") or local == "requirements" or local.startswith("requirements/")):
                warnings.append(f"source-relative-link: {relative} -> {target}")
    return warnings


def build_preview(root: Path) -> MigrationPreview:
    """Discover a canonical move map without changing the project."""

    root = root.resolve()
    marker = root / "codeops" / ".codeops.yml"
    feature, source = _feature(root)
    if marker.is_file():
        return MigrationPreview(feature, source, (), (), True)
    moves: list[Move] = []
    warnings: list[str] = []
    requirements = root / "requirements"
    plans = root / "plans"
    roadmap = plans / "00-roadmap.md"
    if requirements.is_dir():
        moves.append(Move("requirements", f"codeops/features/{feature}/requirements"))
    plan_directories = sorted(
        path for path in plans.iterdir() if path.is_dir() and path.name != "_archive"
    ) if plans.is_dir() else []
    roadmap_text = roadmap.read_text(encoding="utf-8") if roadmap.is_file() else ""
    for path in plan_directories:
        moves.append(Move(f"plans/{path.name}", f"codeops/features/{feature}/plans/{path.name}"))
        if path.name not in roadmap_text:
            warnings.append(
                f"plan-not-in-roadmap: plans/{path.name} is on disk but not referenced in the roadmap"
            )
    if roadmap.is_file():
        moves.append(Move("plans/00-roadmap.md", f"codeops/features/{feature}/00-roadmap.md"))
    archive = plans / "_archive"
    if archive.is_dir():
        for path in sorted(archive.iterdir()):
            moves.append(Move(f"plans/_archive/{path.name}", f"codeops/_archive/{path.name}"))
            if path.is_file():
                warnings.append(
                    f"archive-loose-file: plans/_archive/{path.name} will move to codeops/_archive/{path.name}"
                )
    if plans.is_dir():
        for path in sorted(plans.iterdir()):
            if path.is_file() and path.name != "00-roadmap.md":
                warnings.append(
                    f"loose-file-not-migrated: plans/{path.name} is directly under plans and is left in place"
                )
    warnings.extend(_source_link_warnings(root))
    return MigrationPreview(feature, source, tuple(moves), tuple(warnings))
