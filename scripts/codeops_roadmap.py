#!/usr/bin/env python3
"""Portable roadmap synchronization and compaction command."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Sequence

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_roadmap_lib.model import synchronize
from scripts.codeops_roadmap_lib.rendering import compact, write_rendered


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("sync", "compact"):
        child = subparsers.add_parser(command)
        child.add_argument("--root", type=Path, default=Path("."))
        mode = child.add_mutually_exclusive_group()
        mode.add_argument("--check", action="store_true")
        mode.add_argument("--write", action="store_true")
        mode.add_argument("--dry-run", action="store_true")
        child.add_argument("--date", default=date.today().isoformat())
        child.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        root = args.root.resolve()
        result = compact(root) if args.command == "compact" else synchronize(root, args.date)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"codeops-roadmap: {exc}", file=sys.stderr)
        return 1
    payload = result.to_json(root)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif args.command == "sync":
        for item in result.drift:
            print(f"DRIFT {item}")
        for item in result.held:
            print(f"HELD {item}")
    else:
        for item in result.notes:
            print(f"WOULD-STRIP {item}")
        for item in result.flags:
            print(f"FLAG {item}")
    if args.write:
        code = write_rendered(root, result.rendered)
        if code != 0:
            print("codeops-roadmap: native mutation prerequisites are blocked", file=sys.stderr)
            return code
    if args.check:
        if args.command == "sync":
            return 1 if result.drift else 0
        return 1 if result.notes or result.flags else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
