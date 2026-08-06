"""Passive process-host classification with no delegated environment probes."""

from __future__ import annotations

import os
import platform
from enum import Enum
from typing import Mapping


class HostKind(str, Enum):
    """Supported process-host classifications used before platform dispatch."""

    NATIVE_WINDOWS = "native-windows"
    WSL = "wsl"
    OTHER = "other"


def classify_process_host(
    environment: Mapping[str, str],
    *,
    os_name: str | None = None,
    system: str | None = None,
    release: str | None = None,
) -> HostKind:
    """Classify the current process from facts already available in-process.

    Installed optional subsystems do not affect native Windows. A POSIX process is classified as
    WSL only when its kernel release or inherited process environment identifies that runtime.
    No executable, distribution, or translated filesystem path is queried.
    """
    current_os = os.name if os_name is None else os_name
    current_system = platform.system() if system is None else system
    current_release = platform.release() if release is None else release
    if current_os == "nt" and current_system.casefold() == "windows":
        return HostKind.NATIVE_WINDOWS
    wsl_environment = "WSL_INTEROP" in environment or "WSL_DISTRO_NAME" in environment
    wsl_kernel = "microsoft" in current_release.casefold()
    if current_os == "posix" and (wsl_environment or wsl_kernel):
        return HostKind.WSL
    return HostKind.OTHER
