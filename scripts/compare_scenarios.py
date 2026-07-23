#!/usr/bin/env python3
"""Compare retained Codex and Claude scenario results on safety gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_scenarios import score


def blocking(path: Path) -> int:
    result = json.loads(path.read_text(encoding="utf-8"))
    return sum(item.get("must_block") is True for item in result.get("material_ambiguities", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", type=Path)
    args = parser.parse_args()
    scenario = args.scenario
    expected = scenario / "expected.json"
    codex = scenario / "result.json"
    claude = scenario / "claude-result.json"
    errors = [f"Codex: {item}" for item in score(expected, codex)]
    # Claude CodeOps 3.12.0 predates the Codex edition's canonical domain-pack
    # identifiers. Compare its semantic coverage and gate behavior, not names
    # that do not exist in that product.
    errors.extend(f"Claude: {item}" for item in score(expected, claude, require_lenses=False))
    codex_count = blocking(codex)
    claude_count = blocking(claude)
    if codex_count < claude_count:
        errors.append(f"Codex found {codex_count} blocking ambiguities; Claude found {claude_count}")
    if errors:
        print(f"Parity evaluation failed: {scenario.name}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Parity evaluation passed: {scenario.name} (Codex {codex_count}, Claude {claude_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
