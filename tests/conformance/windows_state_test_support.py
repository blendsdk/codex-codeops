"""Self-contained native plugin authority for state subprocess tests."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


_INSTALLED = False


def install_native_plugin_environment(root: Path) -> None:
    """Install isolated writable plugin data when a Windows test shell has none."""

    global _INSTALLED
    if os.name != "nt" or _INSTALLED:
        return
    _INSTALLED = True
    original_root = os.environ.get("PLUGIN_ROOT")
    original_data = os.environ.get("PLUGIN_DATA")
    plugin_data = Path(tempfile.mkdtemp(prefix="codeops-state-plugin-data-"))
    os.environ["PLUGIN_ROOT"] = str(root)
    os.environ["PLUGIN_DATA"] = str(plugin_data)

    def restore() -> None:
        shutil.rmtree(plugin_data, ignore_errors=True)
        for name, value in (
            ("PLUGIN_ROOT", original_root),
            ("PLUGIN_DATA", original_data),
        ):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    atexit.register(restore)
