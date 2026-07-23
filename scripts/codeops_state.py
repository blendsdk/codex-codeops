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
    root = _root(argv)
    use_v2 = (
        (argv and argv[0] in {"transition", "transition-recover", "traceability-upgrade"})
        or "--target" in argv
        or "--gate" in argv
        or has_schema_two(root)
        or (root / "codeops" / "codeops.json").is_file()
        or (root / "schemas" / "traceability-v2.schema.json").is_file()
    )
    return run_v2(argv) if use_v2 else legacy.main()


if __name__ == "__main__":
    raise SystemExit(main())
