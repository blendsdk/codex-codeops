#!/usr/bin/env python3
"""Build a byte-reproducible release ZIP from one Git commit."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tarfile
import tempfile
import zipfile


ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)


def package(root: Path, commit: str, output: Path) -> None:
    """Write a canonical stored ZIP while honoring Git export attributes."""

    root = root.resolve()
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="codeops-release-") as raw:
        archive = Path(raw) / "source.tar"
        subprocess.run(
            ["git", "-C", str(root), "archive", "--format=tar", f"--output={archive}", commit],
            check=True,
        )
        with tarfile.open(archive, mode="r:") as source, zipfile.ZipFile(
            output, mode="w", compression=zipfile.ZIP_STORED, strict_timestamps=True
        ) as target:
            for member in source.getmembers():
                if member.isdir():
                    continue
                if not member.isfile():
                    raise ValueError(f"unsupported release archive entry: {member.name}")
                stream = source.extractfile(member)
                if stream is None:
                    raise ValueError(f"cannot read release archive entry: {member.name}")
                info = zipfile.ZipInfo(member.name, date_time=ZIP_EPOCH)
                info.create_system = 3
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = ((0o100000 | member.mode) & 0xFFFF) << 16
                target.writestr(info, stream.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.root, args.commit, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
