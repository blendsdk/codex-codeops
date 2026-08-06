#!/usr/bin/env python3
"""Portable flat-to-nested CodeOps layout command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_migrate_lib.model import build_preview
from scripts.codeops_migrate_lib.apply import apply_preview


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("preview", "apply"):
        child = subparsers.add_parser(command)
        child.add_argument("--root", type=Path, default=Path("."))
        child.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        preview = build_preview(args.root)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"codeops-migrate: {exc}", file=sys.stderr)
        return 1
    if args.command == "apply":
        code, payload = apply_preview(args.root, preview)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        elif code == 0:
            print(f"codeops-migrate: {payload['result']}")
        else:
            print(f"codeops-migrate: {payload['error']}", file=sys.stderr)
        return code
    payload = preview.to_json()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"SLUG: {preview.feature} (source: {preview.feature_source})")
        for move in preview.moves:
            print(f"MOVE {move.source} -> {move.target}")
        for warning in preview.warnings:
            print(f"WARN {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
