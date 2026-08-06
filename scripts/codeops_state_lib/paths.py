"""Canonical durable paths and closed Windows filesystem policy."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path, PureWindowsPath
import re
import stat
from typing import Protocol, Sequence, runtime_checkable


_DRIVE_FIXED = 3
_WINDOWS_INVALID = frozenset('<>:"/\\|?*')
_RESERVED_DEVICE = re.compile(
    r"^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class VolumeInfo:
    identity: str
    filesystem: str
    fixed_local: bool


@dataclass(frozen=True, slots=True)
class PathCollisionKey:
    volume_identity: str
    parent_long_name: str
    final_long_name: str
    file_identity: tuple[int, int] | None


@runtime_checkable
class PathProbe(Protocol):
    is_windows: bool

    def canonical(self, path: Path) -> Path: ...

    def volume_info(self, path: Path) -> VolumeInfo: ...

    def existing_components(self, root: Path, target: Path) -> tuple[Path, ...]: ...

    def is_reparse_point(self, path: Path) -> bool: ...

    def long_name(self, path: Path) -> str: ...

    def file_identity(self, path: Path) -> tuple[int, int] | None: ...


class NativePathProbe:
    """Read-only native filesystem observations used by durable path validation."""

    is_windows = os.name == "nt"

    def canonical(self, path: Path) -> Path:
        resolved = str(path.resolve(strict=False))
        if self.is_windows and resolved.startswith("\\\\?\\UNC\\"):
            resolved = "\\\\" + resolved[8:]
        elif self.is_windows and resolved.startswith("\\\\?\\"):
            resolved = resolved[4:]
        candidate = Path(resolved)
        if not self.is_windows:
            return candidate
        missing: list[str] = []
        existing = candidate
        while not existing.exists() and existing != existing.parent:
            missing.append(existing.name)
            existing = existing.parent
        expanded = Path(self.long_name(existing))
        return expanded.joinpath(*reversed(missing))

    def volume_info(self, path: Path) -> VolumeInfo:
        existing = path
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        if not self.is_windows:
            device = str(existing.stat().st_dev)
            return VolumeInfo(device, "", True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        root_buffer = ctypes.create_unicode_buffer(261)
        if not kernel32.GetVolumePathNameW(
            str(existing), root_buffer, len(root_buffer)
        ):
            raise OSError(ctypes.get_last_error(), "cannot resolve path volume")
        serial = ctypes.c_uint32()
        filesystem_buffer = ctypes.create_unicode_buffer(261)
        if not kernel32.GetVolumeInformationW(
            root_buffer.value,
            None,
            0,
            ctypes.byref(serial),
            None,
            None,
            filesystem_buffer,
            len(filesystem_buffer),
        ):
            raise OSError(ctypes.get_last_error(), "cannot query path filesystem")
        drive_type = int(kernel32.GetDriveTypeW(root_buffer.value))
        identity = f"{root_buffer.value.casefold()}:{int(serial.value):08x}"
        return VolumeInfo(
            identity,
            filesystem_buffer.value,
            drive_type == _DRIVE_FIXED,
        )

    def existing_components(self, root: Path, target: Path) -> tuple[Path, ...]:
        relative = target.relative_to(root)
        components = [root]
        current = root
        for component in relative.parts:
            current /= component
            if not current.exists():
                break
            components.append(current)
        return tuple(components)

    def is_reparse_point(self, path: Path) -> bool:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)

    def long_name(self, path: Path) -> str:
        if not self.is_windows or not path.exists():
            return str(path)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        required = int(kernel32.GetLongPathNameW(str(path), None, 0))
        if required == 0:
            raise OSError(ctypes.get_last_error(), "cannot resolve long path name")
        buffer = ctypes.create_unicode_buffer(required + 1)
        if not kernel32.GetLongPathNameW(str(path), buffer, len(buffer)):
            raise OSError(ctypes.get_last_error(), "cannot resolve long path name")
        return buffer.value

    def file_identity(self, path: Path) -> tuple[int, int] | None:
        if not path.exists():
            return None
        value = path.stat()
        return int(value.st_dev), int(value.st_ino)


def _validate_component(component: str, *, windows: bool) -> None:
    if not component or component in {".", ".."}:
        raise ValueError("durable path has an invalid component")
    if any(ord(character) < 32 for character in component):
        raise ValueError("durable path contains a control character")
    if windows:
        if any(character in _WINDOWS_INVALID for character in component):
            raise ValueError("durable path contains a Windows-invalid character")
        if component.endswith((" ", ".")):
            raise ValueError("durable path has a trailing space or dot")
        if _RESERVED_DEVICE.fullmatch(component):
            raise ValueError("durable path uses a reserved Windows device name")


def _relative_parts(value: str, *, windows: bool) -> tuple[str, ...]:
    if not isinstance(value, str) or not value:
        raise ValueError("durable path must be a nonempty string")
    parsed = PureWindowsPath(value)
    if parsed.is_absolute() or parsed.drive or parsed.root:
        raise ValueError("durable path must be project-relative")
    if windows:
        normalized = value.replace("\\", "/")
    else:
        if "\\" in value:
            raise ValueError("legacy backslash paths are Windows-only")
        normalized = value
    if normalized.startswith("/"):
        raise ValueError("durable path must be project-relative")
    parts = tuple(normalized.split("/"))
    for component in parts:
        _validate_component(component, windows=True)
    return parts


def _contained(root: Path, target: Path, probe: PathProbe) -> tuple[Path, Path]:
    canonical_root = probe.canonical(root)
    canonical_target = probe.canonical(target)
    try:
        canonical_target.relative_to(canonical_root)
    except ValueError as exc:
        raise ValueError("durable path escapes the project root") from exc
    return canonical_root, canonical_target


def canonical_relative_path(
    root: Path,
    path: Path,
    *,
    probe: PathProbe | None = None,
) -> str:
    """Return a validated project-relative path serialized with forward slashes."""

    selected = probe or NativePathProbe()
    canonical_root, canonical_target = _contained(root, path, selected)
    relative = canonical_target.relative_to(canonical_root)
    parts = relative.parts
    if not parts:
        raise ValueError("durable path cannot name the project root")
    for component in parts:
        _validate_component(component, windows=True)
    return "/".join(parts)


def resolve_durable_path(
    root: Path,
    value: str,
    *,
    probe: PathProbe | None = None,
) -> Path:
    """Resolve a canonical or safely compatible legacy path within root."""

    selected = probe or NativePathProbe()
    parts = _relative_parts(value, windows=selected.is_windows)
    canonical_root, canonical_target = _contained(
        root,
        Path(root).joinpath(*parts),
        selected,
    )
    canonical_target.relative_to(canonical_root)
    return canonical_target


def _collision_key(path: Path, volume: VolumeInfo, probe: PathProbe) -> PathCollisionKey:
    parent = probe.long_name(path.parent).casefold()
    final_value = probe.long_name(path)
    final = Path(final_value).name.casefold()
    return PathCollisionKey(
        volume.identity.casefold(),
        parent,
        final,
        probe.file_identity(path),
    )


def validate_transaction_paths(
    root: Path,
    paths: Sequence[Path],
    *,
    probe: PathProbe | None = None,
) -> tuple[Path, ...]:
    """Validate a complete path set before mutation and reject Windows aliases."""

    selected = probe or NativePathProbe()
    canonical_root = selected.canonical(root)
    ordered = tuple(paths)
    namespace_keys: set[tuple[str, str, str]] = set()
    identity_keys: set[tuple[str, tuple[int, int]]] = set()
    for path in ordered:
        # Validate the lexical path before canonical resolution can hide an alias.
        absolute = path if path.is_absolute() else root / path
        canonical_relative_path(root, absolute, probe=selected)
        _, canonical_target = _contained(root, absolute, selected)
        volume = selected.volume_info(canonical_target)
        if selected.is_windows and (
            not volume.fixed_local or volume.filesystem.casefold() != "ntfs"
        ):
            raise OSError("durable state requires a fixed local NTFS volume")
        for component in selected.existing_components(canonical_root, canonical_target):
            if selected.is_reparse_point(component):
                raise OSError("durable path contains a reparse point")
        key = _collision_key(canonical_target, volume, selected)
        namespace = (
            key.volume_identity,
            key.parent_long_name,
            key.final_long_name,
        )
        if namespace in namespace_keys:
            raise ValueError("durable transaction paths collide")
        namespace_keys.add(namespace)
        if key.file_identity is not None:
            identity = (key.volume_identity, key.file_identity)
            if identity in identity_keys:
                raise ValueError("durable transaction paths resolve to the same file")
            identity_keys.add(identity)
    return ordered
