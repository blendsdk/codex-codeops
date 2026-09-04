#!/usr/bin/env python3
"""Specification tests for release-evidence validation across Git states."""

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
    published_evidence,
)


class ReleaseEvidenceSpecificationTests(unittest.TestCase):
    """Verify the evidence states allowed before and after release publication."""

    def test_immutable_release_tag_accepts_its_prepublication_evidence(self) -> None:
        """A tag snapshot can only contain evidence captured before that tag was published."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_repository(root, prepublication_evidence())
            git(root, "tag", "-a", f"v{VERSION}", "-m", f"Release {VERSION}")
            git(root, "checkout", "--detach", f"v{VERSION}")

            errors = validate_release_evidence(root)

        self.assertEqual(errors, [])

    def test_branch_rejects_prepublication_evidence_after_the_tag_exists(self) -> None:
        """A writable branch must replace temporary evidence after publication."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_repository(root, prepublication_evidence())
            git(root, "tag", "-a", f"v{VERSION}", "-m", f"Release {VERSION}")

            errors = validate_release_evidence(root)

        self.assertIn(
            f"pre-publication evidence for {VERSION} is stale outside the exact v{VERSION} checkout",
            errors,
        )

    def test_branch_accepts_observed_evidence_after_publication(self) -> None:
        """Published installation evidence satisfies the durable branch contract."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize_repository(root, published_evidence())
            git(root, "tag", "-a", f"v{VERSION}", "-m", f"Release {VERSION}")

            errors = validate_release_evidence(root)

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
