"""Repository-specific validation contracts retained by the portable verifier."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
from typing import Callable


def _text(root: Path, relative: str) -> str:
    return (root / relative).read_text(encoding="utf-8")


def _contains(text: str, *tokens: str) -> None:
    for token in tokens:
        if token not in text:
            raise AssertionError(f"required contract token is missing: {token}")


def _marketplace(root: Path) -> None:
    data = json.loads(_text(root, ".agents/plugins/marketplace.json"))
    assert isinstance(data.get("name"), str) and data["name"]
    assert isinstance(data.get("plugins"), list) and data["plugins"]
    entry = next(item for item in data["plugins"] if item.get("name") == "codeops")
    assert entry["source"]["source"] in {"url", "git-subdir", "local"}
    assert entry["policy"]["installation"] in {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
    assert entry["policy"]["authentication"] in {"ON_INSTALL", "ON_USE"}
    assert isinstance(entry.get("category"), str) and entry["category"]


def _native_terms(root: Path) -> None:
    pattern = re.compile(
        r"CLAUDE_PLUGIN_ROOT|~/\.claude|\.claude/agents|"
        r"model: (?:opus|sonnet|fable)|Follow the project.s CLAUDE.md"
    )
    matches: list[str] = []
    for relative in ("skills", "_shared", "standards", "agent-templates", "hooks"):
        base = root / relative
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if pattern.search(line):
                    matches.append(f"{path.relative_to(root).as_posix()}:{number}:{line}")
    if matches:
        raise AssertionError("Codex-native terminology violations:\n" + "\n".join(matches))


def _scope_expansion(root: Path) -> None:
    policy = _text(root, "_shared/scope-expansion-control.md")
    layout = _text(root, "_shared/layout-convention.md")
    supported = (
        "skills/make-plan/SKILL.md",
        "skills/preflight/SKILL.md",
        "skills/exec-plan/SKILL.md",
    )
    _contains(
        policy,
        "Strict scope is the default",
        "exactly one standalone",
        "Necessary correction",
        "blocking uncertainty",
        "Only `Keep`",
        "Finding resolution and expansion authorization are separate",
        "`--auto-design` cannot choose `Keep`",
    )
    for relative in supported:
        value = _text(root, relative)
        _contains(
            value,
            "## Scope exploration option",
            "exact standalone `--explore-scope` token",
            "zero occurrences means strict scope",
            "../../_shared/scope-expansion-control.md",
            "Strict scope is the default",
        )
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if path.relative_to(root).as_posix() not in supported:
            assert "../../_shared/scope-expansion-control.md" not in path.read_text(encoding="utf-8")
    _contains(
        layout,
        "00-scope-expansion-register-<document-name>.md",
        "scope-expansion-register-<artifact-name>.md",
        "| Ad-hoc directory | `scope-expansion-register.md` inside the governed directory |",
    )
    _contains(
        policy,
        "| Event ID | SE ID | Timestamp | From state | Decision | Authority and evidence |",
        "| SE ID | Derived artifact or graph target | Relation or kind | Current state |",
    )
    _contains(_text(root, "_shared/auto-design.md"), "choose `Keep`")
    _contains(_text(root, "_shared/quality-profile.md"), "scope mode (`strict` or `explore`)")


def _preflight(root: Path) -> None:
    skill = _text(root, "skills/preflight/SKILL.md")
    report = _text(root, "skills/preflight/report-format.md")
    dimensions = _text(root, "skills/preflight/dimensions.md")
    auditor = _text(root, "agent-templates/preflight-auditor.md")
    _contains(
        skill,
        "## Audit scope contract",
        "contextual, not scope expansion",
        "require a fresh-session audit or an explicit user decision",
        "Preserve finding identity across iterations",
        "requirements/00-preflight-report-RD-NN.md",
    )
    _contains(report, "all remaining 🟡 explicitly accepted", "Finding identifiers name root causes")
    _contains(dimensions, "Freeze the scope")
    _contains(auditor, "Respect the audit boundary")
    roadmap = _text(root, "skills/roadmap/SKILL.md")
    _contains(roadmap, "A narrow report never advances sibling RDs", "proves only that document passed")


def _plan_execution(root: Path) -> None:
    make_plan = _text(root, "skills/make-plan/SKILL.md")
    exec_plan = _text(root, "skills/exec-plan/SKILL.md")
    protocol = _text(root, "skills/exec-plan/execution-protocol.md")
    template = _text(root, "skills/make-plan/templates.md")
    executor = _text(root, "agent-templates/plan-task-executor.md")
    demanding = _text(root, "agent-templates/plan-task-executor-opus.md")
    reviewer = _text(root, "agent-templates/phase-reviewer.md")
    _contains(
        make_plan,
        "## Planning scope contract",
        "exact expanded modification set",
        "explicitly approved `⏸ Deferred`",
        "after two post-gate ambiguity batches",
        "except the incrementally persisted Ambiguity",
    )
    assert "--gate plan --target <target>" in make_plan.replace(" \\\n  ", " ")
    assert "--gate execution --target <plan-target>" in exec_plan.replace(" \\\n  ", " ")
    assert "--request <transition-request.json>" in exec_plan.replace(" \\\n  ", " ")
    _contains(exec_plan, "`task-complete`")
    _contains(
        protocol,
        'codeops_worktree_snapshot.py" snapshot',
        'codeops_worktree_snapshot.py" diff',
        "three consecutive failures with the same failure signature",
        "expected modification set",
        "Documentation-standard self-check (NON-NEGOTIABLE, before every `[x]`)",
        "Missing required documentation blocks `[x]`",
    )
    for value in (executor, demanding):
        _contains(value, "Documentation gate (non-negotiable)", "Missing documentation blocks completion")
    _contains(reviewer, "Documentation compliance", "Missing required documentation is a standards finding")
    _contains(template, "Phase baseline tree")


def _auto_design(root: Path) -> None:
    policy = _text(root, "_shared/auto-design.md")
    supported = (
        "skills/make-requirements/SKILL.md",
        "skills/make-plan/SKILL.md",
        "skills/preflight/SKILL.md",
        "skills/exec-plan/SKILL.md",
    )
    _contains(
        policy,
        "Authority: AI — delegated by --auto-design",
        "## Reserved authority",
        "does not grant action permission",
        "root invocation ID",
        "never widen",
        "bounded escalation",
    )
    values: dict[str, str] = {}
    for relative in supported:
        value = _text(root, relative)
        values[relative] = value
        _contains(
            value,
            "## Auto-design option",
            "exact standalone `--auto-design` token",
            "before the first `--` sentinel",
            "zero occurrences means normal mode",
            "more than one is invalid",
            "tokens at or after the sentinel are target content",
            "../../_shared/auto-design.md",
            "unsupported child fails closed",
            "does not grant action permission",
            "Normal mode:",
        )
    for path in sorted((root / "skills").glob("*/SKILL.md")):
        if path.relative_to(root).as_posix() not in supported:
            assert "../../_shared/auto-design.md" not in path.read_text(encoding="utf-8")
    _contains(values[supported[-1]], "does not imply `--auto-commit`")
    _contains(values[supported[2]], "never auto-waive risk or dismiss a critical/major finding")
    requirements_add = _text(root, "skills/make-requirements/review-and-add.md")
    plan_checklist = _text(root, "skills/make-plan/quality-checklist.md")
    preflight_report = _text(root, "skills/preflight/report-format.md")
    execution_protocol = _text(root, "skills/exec-plan/execution-protocol.md")
    _contains(requirements_add, "With active auto-design, resolve eligible technical items")
    _contains(values[supported[0]], "complete auto-design delegated record", "active auto-design resolves eligible technical decisions")
    _contains(values[supported[1]], "complete delegated provenance for every eligible resolution")
    _contains(plan_checklist, "under the auto-design policy")
    _contains(preflight_report, "canonical delegated marker", "does not authorize applying the fix or waiving a finding")
    _contains(values[supported[-1]], "With active auto-design, resolve an eligible technical choice", "active auto-design resolves eligible technical decisions")
    _contains(execution_protocol, "active auto-design to an eligible technical choice")
    combined = "\n".join((preflight_report, values[supported[-1]], execution_protocol)).casefold()
    for forbidden in (
        "--auto-design authorizes",
        "--auto-design grants",
        "auto-design automatically applies",
        "auto-design automatically commits",
        "auto-design automatically pushes",
        "auto-design automatically deploys",
    ):
        assert forbidden not in combined
    _contains(values[supported[2]], "In normal mode, every finding", "With active auto-design, eligible technical resolutions")
    _contains(values[supported[-1]], "In normal mode, 🔴 CRITICAL and 🟠 MAJOR findings", "With active auto-design, select and record")


def _release_evidence(root: Path) -> None:
    manifest = json.loads(_text(root, ".codex-plugin/plugin.json"))
    scenario = json.loads(_text(root, "tests/scenarios/evidence.json"))
    review = json.loads(_text(root, "tests/evidence/release-review-final.json"))
    assert scenario["codex"]["pluginVersion"].startswith("0.2.0")
    assert scenario["claude"]["pluginVersion"] == "3.12.0"
    assert scenario["scope"] == "requirements-stage ambiguity discovery and gate behavior"
    assert review["verdict"] == "PASS"
    assert not any(item["severity"] in {"critical", "major"} for item in review["findings"])
    install = _text(root, "tests/evidence/install-cli.md")
    match = re.search(r"- Plugin: `[^`]+`, version `([^`]+)`", install)
    assert match is not None
    current = manifest["version"].split("+", 1)[0]
    assert match.group(1) == current
    if "- Evidence state: pre-publication package validation" in install:
        assert f"- Source state: working tree for planned `v{current}`" in install
        tag = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/v{current}"],
            cwd=root,
            check=False,
            capture_output=True,
            shell=False,
        )
        assert tag.returncode != 0
    else:
        assert f"- Repository source: release tag `v{current}`" in install
        assert re.search(rf"enabled at\s+`{re.escape(current)}`", install)
    assert current in _text(root, "CHANGELOG.md")


CONTRACTS: tuple[tuple[str, Callable[[Path], None]], ...] = (
    ("marketplace metadata", _marketplace),
    ("Codex-native shipped terminology", _native_terms),
    ("preflight scope and convergence contract", _preflight),
    ("plan and execution scope contracts", _plan_execution),
    ("auto-design authority contract", _auto_design),
    ("scope-expansion authority contract", _scope_expansion),
    ("release evidence provenance", _release_evidence),
)


def validate_contracts(root: Path) -> tuple[str, ...]:
    """Return deterministic named diagnostics for retained repository contracts."""

    failures: list[str] = []
    for name, check in CONTRACTS:
        try:
            check(root)
        except (AssertionError, KeyError, OSError, TypeError, ValueError) as exc:
            failures.append(f"{name}: {exc or 'contract assertion failed'}")
    return tuple(failures)
