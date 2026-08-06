#!/usr/bin/env python3
"""Dispatch CodeOps state commands to the graph schema that owns their semantics."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from codeops_state_lib import legacy
from codeops_state_lib.v2 import has_schema_two, run as run_v2


_MUTATING_COMMANDS = frozenset({"transition", "transition-recover", "traceability-upgrade"})


def _root(argv: list[str]) -> Path:
    if "--root" not in argv:
        return Path(".").resolve()
    index = argv.index("--root")
    if index + 1 >= len(argv):
        return Path(".").resolve()
    return Path(argv[index + 1]).resolve()


def _argument(argv: list[str], name: str) -> str | None:
    try:
        index = argv.index(name)
    except ValueError:
        return None
    return argv[index + 1] if index + 1 < len(argv) else None


def _mutation_targets(argv: list[str], root: Path) -> tuple[Path, ...]:
    """Conservatively declare every durable target for one state mutation command."""

    command = argv[0]
    targets: set[Path] = set()
    if command in {"transition", "transition-recover"}:
        request_value = _argument(argv, "--request")
        if request_value is None:
            return ()
        request_path = Path(request_value)
        if not request_path.is_absolute():
            request_path = Path.cwd() / request_path
        try:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ()
        operation = request.get("operationId") if isinstance(request, dict) else None
        if not isinstance(operation, str):
            return ()
        state = root / "codeops" / ".state-transactions"
        targets.update(
            {
                state,
                state / "active.lock",
                state / f"{operation}.lock",
                state / f"{operation}.journal.json",
                state / f"{operation}.before",
                state / f"{operation}.after",
                state / f"{operation}.completed.json",
                state / f"{operation}.recovery.lock",
            }
        )
        targets.update(root.glob("codeops/features/*/traceability.json"))
        if command == "transition-recover" and isinstance(request, dict):
            for graph in request.get("graphs", []):
                if isinstance(graph, dict) and isinstance(graph.get("path"), str):
                    targets.add(root / graph["path"])
    else:
        preview = _argument(argv, "--preview")
        feature = _argument(argv, "--feature")
        if preview is not None:
            preview_path = Path(preview)
            targets.add(preview_path if preview_path.is_absolute() else Path.cwd() / preview_path)
        if "--apply" in argv and feature is not None:
            source = root / "codeops" / "features" / feature / "traceability.json"
            targets.update(
                {source, source.with_name("traceability.schema1.backup.json")}
            )
    return tuple(sorted((path.absolute() for path in targets), key=str))


def _run_mutation_preflight(argv: list[str], root: Path) -> int:
    """Run the registered native Windows gate before a direct state mutation."""

    if os.name != "nt" or not argv or argv[0] not in _MUTATING_COMMANDS:
        return 0
    targets = _mutation_targets(argv, root)
    plugin_root_value = os.environ.get("PLUGIN_ROOT")
    plugin_data_value = os.environ.get("PLUGIN_DATA")
    if not targets or not plugin_root_value or not plugin_data_value:
        print("CodeOps state mutation prerequisites are unavailable.", file=sys.stderr)
        return 1
    from codeops_windows_lib.models import Readiness
    from codeops_windows_lib.probes import NativeProbeDependencies
    from codeops_windows_preflight import run_preflight

    try:
        result = run_preflight(
            mode="mutation",
            entrypoint_code="state-transition",
            hook_event=None,
            targets=targets,
            root=root,
            plugin_root=Path(plugin_root_value).resolve(strict=False),
            plugin_data=Path(plugin_data_value).resolve(strict=False),
            session_id=f"direct-state-{os.getpid()}",
            environment=dict(os.environ),
            dependencies=NativeProbeDependencies(),
        )
    except Exception:
        print("CodeOps state mutation prerequisite evaluation failed.", file=sys.stderr)
        return 1
    if result.status is Readiness.BLOCKED:
        print("CodeOps state mutation prerequisites are blocked.", file=sys.stderr)
    return result.exit_code


def main() -> int:
    argv = sys.argv[1:]
    root = _root(argv)
    preflight_exit = _run_mutation_preflight(argv, root)
    if preflight_exit != 0:
        return preflight_exit
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
