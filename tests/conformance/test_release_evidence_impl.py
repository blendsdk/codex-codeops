#!/usr/bin/env python3
"""Implementation tests for release-evidence validation boundaries."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.release_evidence import validate_release_evidence
from tests.conformance.release_evidence_test_support import (
    VERSION,
    git,
    initialize_repository,
    prepublication_evidence,
)


class ReleaseEvidenceImplementationTests(unittest.TestCase):
    """Cover defensive cases outside the primary release workflow."""

    def test_detached_non_tag_commit_does_not_bypass_stale_evidence_check(self) -> None:
        """Only the commit named by the release tag receives the immutable-snapshot exception."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_repository(root, prepublication_evidence())
            git(root, "tag", "-a", f"v{VERSION}", "-m", f"Release {VERSION}")
            (root / "CHANGELOG.md").write_text(
                f"## {VERSION}\n\nPost-tag change.\n",
                encoding="utf-8",
            )
            git(root, "add", "CHANGELOG.md")
            git(root, "commit", "-m", "advance branch")
            git(root, "checkout", "--detach", "HEAD")

            errors = validate_release_evidence(root)

        self.assertIn(
            f"pre-publication evidence for {VERSION} is stale outside the exact v{VERSION} checkout",
            errors,
        )

    def test_published_evidence_requires_tag_and_enabled_version(self) -> None:
        """Incomplete published metadata reports both missing provenance fields."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = (
                "# Codex plugin release evidence\n\n"
                f"- Plugin: `codeops@codeops-marketplace`, version `{VERSION}`\n"
            )
            initialize_repository(root, incomplete)

            errors = validate_release_evidence(root)

        self.assertIn(f"published evidence must identify release tag v{VERSION}", errors)
        self.assertIn(f"published evidence must confirm enabled version {VERSION}", errors)

    def test_invalid_review_findings_shape_returns_a_clear_error(self) -> None:
        """Malformed retained review data fails without raising an unrelated exception."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_repository(root, prepublication_evidence())
            (root / "tests" / "evidence" / "release-review-final.json").write_text(
                '{"verdict": "PASS", "findings": null}',
                encoding="utf-8",
            )

            errors = validate_release_evidence(root)

        self.assertIn("final release review findings must be a list", errors)


if __name__ == "__main__":
    unittest.main()
