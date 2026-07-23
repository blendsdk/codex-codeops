#!/usr/bin/env python3
"""Score structured CodeOps scenario results against adversarial expectations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def normalize(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))


def score(expected_path: Path, result_path: Path, *, require_lenses: bool = True) -> list[str]:
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    lenses = set(result.get("selected_lenses", []))
    if require_lenses:
        for lens in expected["required_lenses"]:
            if lens not in lenses:
                errors.append(f"missing required lens: {lens}")
    ambiguities = result.get("material_ambiguities", [])
    blocking = [item for item in ambiguities if item.get("must_block") is True]
    if len(blocking) < expected["minimum_material_ambiguities"]:
        errors.append(f"only {len(blocking)} blocking ambiguities; expected at least {expected['minimum_material_ambiguities']}")
    corpus = " ".join(
        str(item.get("question", "")) + " " + " ".join(item.get("impact", []))
        for item in ambiguities
    )
    corpus_tokens = normalize(corpus)
    for concept in expected["required_concepts"]:
        concept_tokens = normalize(concept)
        overlap = len(concept_tokens & corpus_tokens) / max(1, len(concept_tokens))
        if overlap < 0.5:
            errors.append(f"missing concept coverage: {concept}")
    if result.get("gate_verdict") != expected["verdict"]:
        errors.append(f"gate verdict {result.get('gate_verdict')!r}; expected {expected['verdict']!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expected", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    errors = score(args.expected, args.result)
    if errors:
        print("Scenario evaluation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Scenario evaluation passed: {args.expected.parent.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
