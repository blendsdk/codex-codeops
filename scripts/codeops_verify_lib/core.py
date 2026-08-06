"""Deterministic portable validation and documentation gates."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Callable, Mapping

from scripts.codeops_platform.subprocesses import run_command
from scripts.codeops_verify_lib.contracts import validate_contracts


CHECK_NAMES = ("validate", "docs", "migration", "roadmap", "compact")
VERIFIER_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""

    def to_json(self) -> dict[str, object]:
        return {
            "name": self.name,
            "exitCode": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


def _python(root: Path, *arguments: str, environment: Mapping[str, str] | None = None) -> CheckResult:
    values = list(arguments)
    if values and values[0].startswith("scripts/"):
        values[0] = str(VERIFIER_ROOT / values[0])
    selected_environment = dict(os.environ if environment is None else environment)
    selected_environment["PYTHONUTF8"] = "1"
    selected_environment["PYTHONIOENCODING"] = "utf-8"
    result = run_command((sys.executable, *values), cwd=root, environment=selected_environment)
    return CheckResult("", result.exit_code, result.stdout, result.stderr)


def validate(root: Path) -> CheckResult:
    """Run plugin, skill, link, and conformance validation natively."""

    commands: list[tuple[str, ...]] = [
        ("scripts/validate_plugin.py", "."),
        *(
            ("scripts/validate_skill.py", str(path.relative_to(root)))
            for path in sorted((root / "skills").iterdir())
            if path.is_dir()
        ),
        (
            "scripts/validate_markdown_links.py",
            "skills", "_shared", "standards", "references", "docs", "plans", "README.md", "AGENTS.md",
        ),
        *(('scripts/compare_scenarios.py', f'tests/scenarios/{scenario}') for scenario in ('compiler', 'financial', 'web')),
    ]
    stdout: list[str] = []
    stderr: list[str] = []
    failures = 0
    for command in commands:
        result = _python(root, *command)
        stdout.append(result.stdout)
        stderr.append(result.stderr)
        failures += result.exit_code != 0
    contract_failures = validate_contracts(root)
    if contract_failures:
        stderr.append("\n".join(contract_failures) + "\n")
        failures += len(contract_failures)
    environment = dict(os.environ)
    environment["CODEOPS_VERIFY_CHILD"] = "1"
    environment.setdefault("PYTHONUTF8", "1")
    tests = _python(
        root,
        "-m", "unittest", "discover", "-s", "tests/conformance", "-p", "test_*.py",
        environment=environment,
    )
    stdout.append(tests.stdout)
    stderr.append(tests.stderr)
    failures += tests.exit_code != 0
    return CheckResult("validate", 1 if failures else 0, "".join(stdout), "".join(stderr))


def docs(root: Path) -> CheckResult:
    """Validate documentation links and reject unfinished release text."""

    result = _python(root, "scripts/validate_markdown_links.py", "README.md", "docs", "plans")
    stale: list[str] = []
    pattern = ("commands will be published", "TODO", "TBD", "claude-codeops/")
    for base in (root / "README.md", root / "docs"):
        paths = (base,) if base.is_file() else sorted(base.rglob("*.md"))
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for token in pattern:
                if token in text:
                    stale.append(f"{path.relative_to(root).as_posix()}: {token}")
    stderr = result.stderr + ("\n".join(stale) + "\n" if stale else "")
    return CheckResult("docs", 1 if result.exit_code or stale else 0, result.stdout, stderr)


def run_checks(root: Path, checks: Mapping[str, Callable[[Path], CheckResult]]) -> tuple[CheckResult, ...]:
    """Run all named checks in public order without stopping after a failure."""

    return tuple(checks[name](root) for name in CHECK_NAMES)
