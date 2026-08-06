"""Self-contained native plugin authority for state subprocess tests."""

from __future__ import annotations

import atexit
import os
from pathlib import Path
import shutil
import tempfile


def install_native_plugin_environment(root: Path) -> None:
    """Install isolated writable plugin data when a Windows test shell has none."""

    if os.name != "nt":
        return
    os.environ.setdefault("PLUGIN_ROOT", str(root))
    if os.environ.get("PLUGIN_DATA"):
        return
    plugin_data = Path(tempfile.mkdtemp(prefix="codeops-state-plugin-data-"))
    os.environ["PLUGIN_DATA"] = str(plugin_data)
    atexit.register(shutil.rmtree, plugin_data, ignore_errors=True)
