#!/usr/bin/env python3
"""Run the five portable CodeOps repository verification gates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_verify_lib.core import CHECK_NAMES, docs, run_checks, validate
from scripts.codeops_verify_lib.fixtures import compact_check, migration, roadmap


CHECKS = {
    "validate": validate,
    "docs": docs,
    "migration": migration,
    "roadmap": roadmap,
    "compact": compact_check,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("command", choices=("list", "all", *CHECK_NAMES))
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    if args.command == "list":
        payload = {"checks": list(CHECK_NAMES)}
        print(json.dumps(payload, indent=2, sort_keys=True) if args.json else "\n".join(CHECK_NAMES))
        return 0
    results = run_checks(root, CHECKS) if args.command == "all" else (CHECKS[args.command](root),)
    payload = {
        "result": "passed" if all(item.exit_code == 0 for item in results) else "failed",
        "results": [item.to_json() for item in results],
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for item in results:
            print(f"{'PASS' if item.exit_code == 0 else 'FAIL'}: {item.name}")
            if item.stdout:
                print(item.stdout, end="")
            if item.stderr:
                print(item.stderr, end="", file=sys.stderr)
    return 0 if payload["result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
