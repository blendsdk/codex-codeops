#!/usr/bin/env python3
"""Run an installed CodeOps edition against one structured scenario fixture."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


PROMPT = (
    "Read scenario.md. Use the {skill} workflow. Apply its domain-lens and "
    "zero-ambiguity gate rules, but do not create files and do not interview. "
    "Return only the required structured evaluation: select applicable canonical "
    "CodeOps lens IDs, enumerate every material unresolved question that blocks "
    "an executable plan, explain its concrete impacts, and set the gate verdict."
)


def run_codex(scenario: Path, schema_path: Path, output: Path) -> None:
    command = [
        "codex", "exec", "--ephemeral", "--dangerously-bypass-hook-trust",
        "-s", "danger-full-access", "-C", str(scenario),
        "--output-schema", str(schema_path), "-o", str(output),
        PROMPT.format(skill="the make-requirements skill"),
    ]
    subprocess.run(command, check=True)


def run_claude(scenario: Path, schema_path: Path, output: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema.pop("$schema", None)
    plugin = Path.home() / ".claude/plugins/marketplaces/codeops-marketplace"
    command = [
        "claude", "-p", "--no-session-persistence", "--permission-mode", "dontAsk",
        "--tools", "Read",
    ]
    if plugin.exists():
        command.extend(["--add-dir", str(plugin)])
    command.extend([
        "--effort", "high", "--output-format", "json",
        "--json-schema", json.dumps(schema, separators=(",", ":")),
    ])
    command.append(PROMPT.format(skill="/codeops:make_requirements"))
    completed = subprocess.run(command, cwd=scenario, capture_output=True, text=True)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    envelope = json.loads(completed.stdout)
    result = envelope.get("structured_output")
    if result is None:
        result = json.loads(envelope["result"])
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=("codex", "claude"))
    parser.add_argument("scenario", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    scenario = args.scenario.resolve()
    root = Path(__file__).resolve().parents[1]
    schema = root / "tests/scenarios/evaluation-result.schema.json"
    output = args.output.resolve()
    if args.engine == "codex":
        run_codex(scenario, schema, output)
    else:
        run_claude(scenario, schema, output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
