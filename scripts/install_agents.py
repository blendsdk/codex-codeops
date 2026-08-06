#!/usr/bin/env python3
"""Safely materialize optional project-local Codex agents from CodeOps role templates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.codeops_platform.subprocesses import exclusive_path_lock, run_mutation_preflight
from scripts.codeops_state_lib.filesystem import NativeAtomicWriteOps, atomic_write_bytes
from scripts.codeops_state_lib.paths import NativePathProbe


MARKER = "# CODEOPS-GENERATED: install_agents.py schema=1"
ROLE_SOURCES = {
    "explorer": "codebase-scout.md",
    "design-challenger": "design-challenger.md",
    "performance-auditor": "perf-auditor.md",
    "correctness-reviewer": "phase-reviewer.md",
    "executor": "plan-task-executor.md",
    "demanding-executor": "plan-task-executor-opus.md",
    "preflight-auditor": "preflight-auditor.md",
    "security-auditor": "security-auditor.md",
    "spec-test-author": "spec-test-author.md",
    "financial-integrity-auditor": "financial-integrity-auditor.md",
    "concurrency-auditor": "concurrency-auditor.md",
    "semantics-reviewer": "semantics-reviewer.md",
}
WRITABLE = {"executor", "demanding-executor", "spec-test-author"}
TRANSACTION_DIRECTORY = ".codeops-install-transaction"


def parse_template(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(?P<header>.*?)\n---\n(?P<body>.*)$", text, re.DOTALL)
    if not match:
        raise ValueError(f"{path}: missing YAML-like frontmatter")
    header: dict[str, str] = {}
    for line in match.group("header").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        header[key.strip()] = value.strip()
    for key in ("description",):
        if not header.get(key):
            raise ValueError(f"{path}: missing {key}")
    return header, match.group("body").strip()


def render(role: str, source: Path) -> str:
    header, body = parse_template(source)
    model = header.get("model")
    effort = header.get("effort", "high")
    lines = [
        MARKER,
        f"name = {json.dumps(role)}",
        f"description = {json.dumps(header['description'])}",
    ]
    if model:
        lines.append(f"model = {json.dumps(model)}")
    lines.extend([
        f"model_reasoning_effort = {json.dumps(effort)}",
        f"sandbox_mode = {json.dumps('workspace-write' if role in WRITABLE else 'read-only')}",
        f"developer_instructions = {json.dumps(body)}",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=".", help="target project root")
    parser.add_argument("--roles", help="comma-separated roles; default: all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clear_transaction(state: Path, journal: Path) -> bool:
    """Remove the commit-point journal first, then discard inert images."""

    try:
        journal.unlink(missing_ok=True)
    except OSError:
        return False
    try:
        if state.is_dir():
            for path in state.iterdir():
                path.unlink(missing_ok=True)
            state.rmdir()
    except OSError:
        pass
    return True


def _recover_transaction(
    project: Path,
    target_dir: Path,
    state: Path,
    writer: NativeAtomicWriteOps,
) -> bool:
    """Validate and roll back a crashed hash-bound agent installation."""

    if not state.exists():
        return True
    journal = state / "active.json"
    if not journal.is_file():
        return _clear_transaction(state, journal)
    try:
        payload = json.loads(journal.read_text(encoding="utf-8"))
        if set(payload) != {"schema", "entries"} or payload["schema"] != 1:
            raise ValueError("agent transaction journal schema is invalid")
        entries = payload["entries"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("agent transaction entries are invalid")
        roles: set[str] = set()
        restored: list[tuple[Path, bytes | None]] = []
        expected_files = {journal.name}
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"role", "existed", "beforeHash", "afterHash"}:
                raise ValueError("agent transaction entry is malformed")
            role = entry["role"]
            if role not in ROLE_SOURCES or role in roles or not isinstance(entry["existed"], bool):
                raise ValueError("agent transaction role is invalid")
            roles.add(role)
            destination = (target_dir / f"{role}.toml").resolve(strict=False)
            destination.relative_to(project)
            before_path = state / f"{role}.before"
            after_path = state / f"{role}.after"
            after = after_path.read_bytes()
            expected_files.add(after_path.name)
            if _digest(after) != entry["afterHash"]:
                raise ValueError("agent transaction after-image hash mismatch")
            before: bytes | None = None
            allowed = {entry["afterHash"]}
            if entry["existed"]:
                before = before_path.read_bytes()
                expected_files.add(before_path.name)
                if _digest(before) != entry["beforeHash"]:
                    raise ValueError("agent transaction before-image hash mismatch")
                allowed.add(entry["beforeHash"])
            elif entry["beforeHash"] is not None:
                raise ValueError("absent agent has a before-image hash")
            if destination.exists() and _digest(destination.read_bytes()) not in allowed:
                raise ValueError("agent transaction destination has unknown content")
            if not destination.exists() and entry["existed"]:
                raise ValueError("existing agent disappeared during transaction")
            restored.append((destination, before))
        if {path.name for path in state.iterdir()} != expected_files:
            raise ValueError("agent transaction namespace contains unexpected files")
        for destination, before in restored:
            if before is None:
                destination.unlink(missing_ok=True)
            else:
                atomic_write_bytes(destination, before, ops=writer)
        return _clear_transaction(state, journal)
    except (json.JSONDecodeError, OSError, TypeError, ValueError):
        return False


def _write_transaction(
    project: Path,
    target_dir: Path,
    planned: list[tuple[Path, str]],
    writer: NativeAtomicWriteOps,
) -> bool:
    """Publish a complete agent set or restore every prior destination."""

    state = target_dir / TRANSACTION_DIRECTORY
    journal = state / "active.json"
    state.mkdir()
    entries: list[dict[str, object]] = []
    try:
        for destination, expected in planned:
            role = destination.stem
            before = destination.read_bytes() if destination.is_file() else None
            after = expected.encode("utf-8")
            if before is not None:
                atomic_write_bytes(state / f"{role}.before", before, ops=writer)
            atomic_write_bytes(state / f"{role}.after", after, ops=writer)
            entries.append({
                "role": role,
                "existed": before is not None,
                "beforeHash": _digest(before) if before is not None else None,
                "afterHash": _digest(after),
            })
        atomic_write_bytes(
            journal,
            (json.dumps({"schema": 1, "entries": entries}, sort_keys=True) + "\n").encode("utf-8"),
            ops=writer,
        )
        for destination, expected in planned:
            atomic_write_bytes(destination, expected.encode("utf-8"), ops=writer)
    except BaseException:
        if not _recover_transaction(project, target_dir, state, writer):
            print(f"RECOVERY REQUIRED {journal}", file=sys.stderr)
        raise
    return _clear_transaction(state, journal)


def main() -> int:
    args = parse_args()
    plugin_root = Path(__file__).resolve().parent.parent
    project = NativePathProbe().canonical(Path(args.project))
    target_dir = project / ".codex" / "agents"
    roles = list(ROLE_SOURCES)
    if args.roles:
        roles = list(dict.fromkeys(
            role.strip() for role in args.roles.split(",") if role.strip()
        ))
    unknown = sorted(set(roles) - set(ROLE_SOURCES))
    if unknown:
        print(f"Unknown roles: {', '.join(unknown)}", file=sys.stderr)
        return 2

    state = target_dir / TRANSACTION_DIRECTORY
    journal = state / "active.json"
    all_destinations = tuple(target_dir / f"{role}.toml" for role in ROLE_SOURCES)
    transaction_images = tuple(
        state / f"{role}.{suffix}"
        for role in ROLE_SOURCES
        for suffix in ("before", "after")
    )
    mutating = not args.check and not args.dry_run
    if mutating:
        targets = tuple(dict.fromkeys((target_dir, *all_destinations, state, journal, *transaction_images)))
        if run_mutation_preflight(project, targets, entrypoint_code="agent-install") != 0:
            print("Native mutation prerequisites are blocked.", file=sys.stderr)
            return 2

    def collect_plan() -> tuple[bool, list[tuple[Path, str]]]:
        failed = False
        planned: list[tuple[Path, str]] = []
        for role in roles:
            destination = target_dir / f"{role}.toml"
            expected = render(role, plugin_root / "agent-templates" / ROLE_SOURCES[role])
            if destination.exists():
                actual = destination.read_text(encoding="utf-8")
                if not actual.startswith(MARKER):
                    print(f"PRESERVE hand-authored {destination}")
                    continue
                if actual == expected:
                    print(f"OK {destination}")
                    continue
                if args.check:
                    print(f"DRIFT {destination}", file=sys.stderr)
                    failed = True
                    continue
            elif args.check:
                print(f"MISSING {destination}", file=sys.stderr)
                failed = True
                continue
            planned.append((destination, expected))
        return failed, planned

    if not mutating:
        failed, planned = collect_plan()
        if args.check:
            return 1 if failed else 0
        for destination, _ in planned:
            print(f"WOULD WRITE {destination}")
        return 0

    target_dir.mkdir(parents=True, exist_ok=True)
    writer = NativeAtomicWriteOps(project)
    with exclusive_path_lock(target_dir):
        if not _recover_transaction(project, target_dir, state, writer):
            print(f"RECOVERY REQUIRED {journal}", file=sys.stderr)
            return 1
        _, planned = collect_plan()
        if not planned:
            return 0
        for destination, _ in planned:
            print(f"WRITE {destination}")
        try:
            if not _write_transaction(project, target_dir, planned, writer):
                print(f"RECOVERY REQUIRED {journal}", file=sys.stderr)
                return 1
        except OSError as exc:
            print(f"Agent installation failed and was rolled back: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
