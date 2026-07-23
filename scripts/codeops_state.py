#!/usr/bin/env python3
"""Dispatch CodeOps state commands to the graph schema that owns their semantics."""

from __future__ import annotations

import sys
from pathlib import Path

from codeops_state_lib import legacy
from codeops_state_lib.v2 import has_schema_two, run as run_v2


def _root(argv: list[str]) -> Path:
    if "--root" not in argv:
        return Path(".").resolve()
    index = argv.index("--root")
    if index + 1 >= len(argv):
        return Path(".").resolve()
    return Path(argv[index + 1]).resolve()


def main() -> int:
    argv = sys.argv[1:]
    use_v2 = "--target" in argv or "--gate" in argv or has_schema_two(_root(argv))
    return run_v2(argv) if use_v2 else legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
