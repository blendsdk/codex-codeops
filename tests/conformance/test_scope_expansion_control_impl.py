#!/usr/bin/env python3
"""Integration and hostile-input coverage for scope-expansion workflow controls."""

from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "_shared/scope-expansion-control.md"
SUPPORTED = {
    ROOT / "skills/make-plan/SKILL.md",
    ROOT / "skills/preflight/SKILL.md",
    ROOT / "skills/exec-plan/SKILL.md",
}


def markdown_table(section: str) -> dict[str, str]:
    """Return the two-column rows from one authoritative Markdown section."""

    return {
        left.strip(): right.strip()
        for left, right in re.findall(r"^\| (.+?) \| (.+?) \|$", section, re.MULTILINE)
        if not left.startswith("---") and left not in {"Arguments", "Governed target"}
    }


class ScopeExpansionControlImplementation(unittest.TestCase):
    """Verify exact activation, closed integration, and authority separation."""

    def test_exact_token_contract_names_hostile_lookalikes(self) -> None:
        """Prefix, assignment, and bare-word lookalikes must not activate exploration."""

        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("exactly one standalone", text)
        for lookalike in ("--explore-scopes", "--explore-scope=true", "explore-scope"):
            self.assertRegex(text, re.escape(lookalike))

    def test_activation_contract_covers_exact_and_hostile_argument_tables(self) -> None:
        """The shipped policy and every workflow must carry the exact activation contract."""

        policy = POLICY.read_text(encoding="utf-8")
        activation = policy.split("## Activation", maxsplit=1)[1].split(
            "## Prime directive", maxsplit=1
        )[0]
        self.assertEqual(
            markdown_table(activation),
            {
                "`target`": "`strict`",
                "`--explore-scope target`": "`explore`",
                "`--explore-scope --explore-scope target`": "`invalid`",
                "`-- --explore-scope`": "`strict`; the token is target content",
                "`--explore-scope -- --explore-scope`": (
                    "`explore`; the later token is target content"
                ),
                "`--explore-scopes`, `--explore-scope=true`, or `explore-scope`": (
                    "`strict`"
                ),
            },
        )

        required_clauses = (
            "exactly one exact standalone `--explore-scope` token",
            "before the first `--` sentinel",
            "zero occurrences means strict scope",
            "more than one is invalid",
            "tokens at or after the sentinel are target content",
            "remove it before resolving targets, paths, or modes",
        )
        for path in SUPPORTED:
            text = path.read_text(encoding="utf-8")
            section = text.split("## Scope exploration option", maxsplit=1)[1].split(
                "\n## ", maxsplit=1
            )[0]
            with self.subTest(skill=path):
                for clause in required_clauses:
                    self.assertIn(clause, section)

    def test_supported_workflow_allowlist_is_closed(self) -> None:
        """Only workflows with complete semantics may activate scope exploration."""

        linked = {
            path
            for path in (ROOT / "skills").glob("*/SKILL.md")
            if "../../_shared/scope-expansion-control.md"
            in path.read_text(encoding="utf-8")
        }
        self.assertEqual(linked, SUPPORTED)

    def test_supported_workflows_have_total_argument_rules(self) -> None:
        """Every supported entry point must parse the flag before resolving user targets."""

        for path in SUPPORTED:
            text = path.read_text(encoding="utf-8")
            with self.subTest(skill=path):
                for token in (
                    "exact standalone `--explore-scope` token",
                    "before the first `--` sentinel",
                    "zero occurrences means strict scope",
                    "more than one is invalid",
                    "tokens at or after the sentinel are target content",
                    "remove it before resolving targets, paths, or modes",
                ):
                    self.assertIn(token, text)

    def test_review_packets_and_agents_fail_closed_to_strict_scope(self) -> None:
        """Delegated reviewers must receive scope context and suppress optional suggestions."""

        profile = (ROOT / "_shared/quality-profile.md").read_text(encoding="utf-8")
        self.assertIn("scope mode (`strict` or `explore`)", profile)
        self.assertIn("confirmed scope baseline", profile)
        for relative in (
            "agent-templates/plan-task-executor.md",
            "agent-templates/plan-task-executor-opus.md",
            "agent-templates/preflight-auditor.md",
            "agent-templates/phase-reviewer.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(agent=relative):
                self.assertIn("fails closed to strict mode", text)
                self.assertIn("optional", text)
                self.assertIn("`SE-*`", text)

    def test_register_paths_distinguish_extensions_and_directory_targets(self) -> None:
        """The shipped path map must distinguish same-stem files and directory targets."""

        layout = (ROOT / "_shared/layout-convention.md").read_text(encoding="utf-8")
        section = layout.split("### Scope-expansion register paths", maxsplit=1)[1].split(
            "\n---", maxsplit=1
        )[0]
        paths = markdown_table(section)
        document_template = paths["Single requirement or single plan document"].split(
            " in the document directory", maxsplit=1
        )[0].strip("`")
        file_template = paths["Ad-hoc file"].split(
            " in the artifact directory", maxsplit=1
        )[0].strip("`")
        directory_template = paths["Ad-hoc directory"].split(
            " inside the governed directory", maxsplit=1
        )[0].strip("`")

        resolved = {
            document_template.replace("<document-name>", name)
            for name in ("foo.md", "foo.txt")
        }
        self.assertEqual(
            resolved,
            {
                "00-scope-expansion-register-foo.md.md",
                "00-scope-expansion-register-foo.txt.md",
            },
        )
        self.assertEqual(
            file_template.replace("<artifact-name>", "foo.md"),
            "scope-expansion-register-foo.md.md",
        )
        self.assertEqual(directory_template, "scope-expansion-register.md")
        self.assertIn("including its extension", layout)

    def test_lifecycle_table_defines_the_complete_transition_graph(self) -> None:
        """The normative transition table must match the accepted lifecycle exactly."""

        text = POLICY.read_text(encoding="utf-8")
        section = text.split("### State transitions", maxsplit=1)[1].split(
            "The stored decision vocabulary", maxsplit=1
        )[0]
        rows = re.findall(r"^\| `([^`]+)` \| (.+) \|$", section, re.MULTILINE)
        transitions = {
            source: tuple(re.findall(r"`([^`]+)`", destinations))
            for source, destinations in rows
        }
        self.assertEqual(
            transitions,
            {
                "Proposed": ("Keep", "Defer", "Discard"),
                "Keep": ("Superseded",),
                "Defer": ("Keep", "Discard", "Superseded"),
                "Discard": ("Keep", "Superseded"),
                "Superseded": (),
            },
        )

    def test_register_schema_separates_state_events_and_authority_links(self) -> None:
        """Current state, immutable rulings, and downstream evidence need separate tables."""

        text = POLICY.read_text(encoding="utf-8")
        for header in (
            "| ID | Proposed addition | Origin | Why it is outside scope | Impact | Recommendation | Current state |",
            "| Event ID | SE ID | Timestamp | From state | Decision | Authority and evidence | Owner | Revisit trigger | Replacement or reversal |",
            "| SE ID | Derived artifact or graph target | Relation or kind | Current state | Evidence source |",
        ):
            self.assertIn(header, text)
        self.assertIn("normalized project-relative path", text)
        self.assertIn("never in source comments", text)
        for token in (
            "`SEV-*` IDs are register-local, monotonic, never reused",
            "Append order is the ordering authority",
        ):
            self.assertIn(token, text)
        self.assertRegex(
            text,
            r"last\s+valid appended event determines current state",
        )

    def test_finding_and_fix_authority_stay_separate(self) -> None:
        """Finding acceptance and broad fix commands must not approve optional scope."""

        report = (ROOT / "skills/preflight/report-format.md").read_text(encoding="utf-8")
        execution = (
            ROOT / "skills/exec-plan/execution-protocol.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Finding resolution and expansion authorization are separate", report)
        self.assertIn("does not authorize undecided, deferred, or", report)
        self.assertIn("A finding ruling never chooses `Keep`", execution)

    def test_auto_design_and_exploration_authorities_are_orthogonal(self) -> None:
        """Technical delegation may coexist with exploration but cannot rule on scope."""

        auto_design = (ROOT / "_shared/auto-design.md").read_text(encoding="utf-8")
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("cannot activate optional", auto_design)
        self.assertIn("choose `Keep`", auto_design)
        self.assertIn("The two flags may coexist", policy)
        self.assertIn("only after `Keep` is recorded", policy)

    def test_user_documentation_explains_strict_and_exploration_modes(self) -> None:
        """Users must be able to predict default silence and opt-in proposal behavior."""

        for relative in ("README.md", "docs/concepts.md", "docs/tutorial.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(document=relative):
                self.assertIn("--explore-scope", text)
                self.assertIn("strict scope", text.lower())
                self.assertIn("Keep", text)


if __name__ == "__main__":
    unittest.main()
