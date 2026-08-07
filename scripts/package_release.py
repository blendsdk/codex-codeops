#!/usr/bin/env python3
"""Build a byte-reproducible release ZIP from one Git commit."""

from __future__ import annotations

import argparse
import binascii
from pathlib import Path
import struct
import subprocess
import tarfile
import tempfile
from typing import TypeAlias


ZIP_DOS_DATE = 0x21
ZIP_UTF8_FLAG = 0x800
ZIP_VERSION = 20
TreeEntry: TypeAlias = tuple[str, str]


def _git_tree(root: Path, commit: str) -> dict[str, TreeEntry]:
    """Return raw blob identities and modes for every path in one Git tree."""

    result = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", commit],
        check=True,
        capture_output=True,
    )
    entries: dict[str, TreeEntry] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.decode("ascii").split(" ")
        if object_type != "blob":
            raise ValueError(f"unsupported release tree entry: {raw_name.decode('utf-8')}")
        entries[raw_name.decode("utf-8")] = (mode, object_id)
    return entries


def _git_blob(root: Path, object_id: str) -> bytes:
    """Read one raw Git blob without checkout or archive text conversion."""

    return subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", object_id],
        check=True,
        capture_output=True,
    ).stdout


def _write_zip(
    source: tarfile.TarFile,
    output: Path,
    root: Path,
    tree: dict[str, TreeEntry],
) -> None:
    """Serialize regular TAR members with fixed, version-independent ZIP headers."""

    central: list[bytes] = []
    with output.open("wb") as target:
        for member in source.getmembers():
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f"unsupported release archive entry: {member.name}")
            entry = tree.get(member.name)
            if entry is None:
                raise ValueError(f"release archive entry is absent from the Git tree: {member.name}")
            mode, object_id = entry
            data = _git_blob(root, object_id)
            name = member.name.encode("utf-8")
            crc = binascii.crc32(data) & 0xFFFFFFFF
            offset = target.tell()
            target.write(struct.pack(
                "<IHHHHHIIIHH",
                0x04034B50, ZIP_VERSION, ZIP_UTF8_FLAG, 0, 0, ZIP_DOS_DATE,
                crc, len(data), len(data), len(name), 0,
            ))
            target.write(name)
            target.write(data)
            permissions = 0o755 if mode == "100755" else 0o644
            central.append(struct.pack(
                "<IHHHHHHIIIHHHHHII",
                0x02014B50, (3 << 8) | ZIP_VERSION, ZIP_VERSION, ZIP_UTF8_FLAG,
                0, 0, ZIP_DOS_DATE, crc, len(data), len(data), len(name), 0, 0,
                0, 0, (0o100000 | permissions) << 16, offset,
            ) + name)
        central_offset = target.tell()
        for record in central:
            target.write(record)
        central_size = target.tell() - central_offset
        target.write(struct.pack(
            "<IHHHHIIH",
            0x06054B50, 0, 0, len(central), len(central), central_size, central_offset, 0,
        ))


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
        with tarfile.open(archive, mode="r:") as source:
            _write_zip(source, output, root, _git_tree(root, commit))


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
