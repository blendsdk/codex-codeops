"""Fixture-backed portable migration, roadmap, and compact logical gates."""

from __future__ import annotations

from pathlib import Path

from scripts.codeops_migrate_lib.model import build_preview
from scripts.codeops_roadmap_lib.model import synchronize
from scripts.codeops_roadmap_lib.rendering import compact

from .core import CheckResult


def migration(root: Path) -> CheckResult:
    fixture = root / "scripts" / "fixtures" / "flat-repo"
    try:
        preview = build_preview(fixture)
        sources = [move.source for move in preview.moves]
        assert preview.feature == "billing-platform"
        assert sources == [
            "requirements",
            "plans/invoicing",
            "plans/legacy",
            "plans/00-roadmap.md",
            "plans/_archive/billing-v1",
        ]
        assert any("plans/legacy" in warning for warning in preview.warnings)
    except (AssertionError, OSError, ValueError) as exc:
        return CheckResult("migration", 1, stderr=f"{exc}\n")
    return CheckResult("migration", 0, stdout="Migration checks passed.\n")


def roadmap(root: Path) -> CheckResult:
    fixture = root / "scripts" / "fixtures" / "roadmap-repo" / "nested"
    try:
        result = synchronize(fixture, "2025-06-01")
        assert result.layout == "nested"
        assert not result.drift
        assert result.held
    except (AssertionError, OSError, ValueError) as exc:
        return CheckResult("roadmap", 1, stderr=f"{exc}\n")
    return CheckResult("roadmap", 0, stdout="Roadmap checks passed.\n")


def compact_check(root: Path) -> CheckResult:
    fixture = root / "scripts" / "fixtures" / "bloated-repo" / "nested"
    try:
        result = compact(fixture)
        assert len(result.rendered) == 3
        for path, rendered in result.rendered.items():
            expected = path.with_name(path.name + ".expected").read_bytes()
            assert rendered == expected
        assert result.flags
    except (AssertionError, OSError, ValueError) as exc:
        return CheckResult("compact", 1, stderr=f"{exc}\n")
    return CheckResult("compact", 0, stdout="Compact checks passed.\n")
