#!/usr/bin/env python3
"""Validate repository-local Markdown links without accessing the network."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")


def markdown_files(raw_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in raw_paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(path.rglob("*.md"))
        elif path.suffix == ".md" and path.is_file():
            files.append(path)
    return sorted(set(files))


def main() -> int:
    errors: list[str] = []
    for source in markdown_files(sys.argv[1:]):
        if source.name in {"template.md", "templates.md"}:
            continue
        text = source.read_text(encoding="utf-8")
        for match in LINK_RE.finditer(text):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "/", "http://", "https://", "mailto:")):
                continue
            target_text = raw_target.split("#", 1)[0]
            if any(marker in target_text for marker in ("[", "]", "XX-", "<", ">")):
                continue
            if target_text.startswith("<") and target_text.endswith(">"):
                target_text = target_text[1:-1]
            target = (source.parent / unquote(target_text)).resolve()
            if not target.exists():
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{source}:{line}: missing local link target {raw_target!r}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Local Markdown links are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
