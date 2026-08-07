#!/usr/bin/env python3
"""Capture sanitized native Windows CLI certification evidence for a packed candidate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import tempfile
from typing import Sequence
import zipfile

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from scripts.codeops_platform.subprocesses import run_command
from scripts.validate_windows_evidence import PROHIBITED_RUNTIME_RE, REQUIRED_SCENARIOS, validate_evidence_set
from scripts.windows_release_authority import load_authority, verify_candidate


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--candidate", type=Path, required=True, help="Packed plugin ZIP")
    parser.add_argument("--authority", type=Path, required=True, help="Independent release authority JSON")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewer", required=True, help="Reviewer GitHub identity")
    parser.add_argument("--codex", default="codex", help="Trusted native Codex executable")
    return parser


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _prepare_output(output: Path, version: str) -> tuple[Path, Path]:
    """Create a version-owned record directory without disturbing retained evidence."""

    records_root = output / f"windows-native-{version}"
    manifest_path = output / f"windows-native-{version}.json"
    if records_root.exists() or manifest_path.exists():
        raise RuntimeError(f"evidence already exists for version {version}")
    output.mkdir(parents=True, exist_ok=True)
    records_root.mkdir()
    return records_root, manifest_path


def _discard_capture(records_root: Path, manifest_path: Path) -> None:
    """Remove only artifacts owned by the current failed capture."""

    manifest_path.unlink(missing_ok=True)
    if records_root.exists():
        shutil.rmtree(records_root)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *arguments: str) -> str:
    result = run_command(("git", *arguments), cwd=root)
    if result.exit_code:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(arguments)} failed")
    return result.stdout.strip()


def _candidate_root(extracted: Path) -> Path:
    direct = extracted / ".codex-plugin" / "plugin.json"
    if direct.is_file():
        return extracted
    matches = list(extracted.glob("*/.codex-plugin/plugin.json"))
    if len(matches) != 1:
        raise RuntimeError("candidate ZIP must contain exactly one plugin root")
    return matches[0].parents[1]


def _normalized(value: str, plugin_root: Path) -> str:
    return value.replace(str(plugin_root), "<PLUGIN_ROOT>").replace(str(plugin_root).replace("\\", "/"), "<PLUGIN_ROOT>")


def _initialize_git(path: Path, environment: dict[str, str]) -> None:
    """Create one isolated committed repository through native Git argument arrays."""

    path.mkdir(parents=True, exist_ok=True)
    commands = (
        ("git", "init", "-q", str(path)),
        ("git", "-C", str(path), "config", "user.email", "certification@example.invalid"),
        ("git", "-C", str(path), "config", "user.name", "CodeOps Certification"),
    )
    for command in commands:
        result = run_command(command, cwd=path, environment=environment)
        if result.exit_code != 0:
            raise RuntimeError(result.stderr.strip() or "unable to initialize certification repository")


def _commit_all(path: Path, message: str, environment: dict[str, str]) -> None:
    for command in (
        ("git", "-C", str(path), "add", "."),
        ("git", "-C", str(path), "commit", "-qm", message),
    ):
        result = run_command(command, cwd=path, environment=environment)
        if result.exit_code != 0:
            raise RuntimeError(result.stderr.strip() or "unable to commit certification fixture")


def _prepare_lifecycle_project(path: Path, environment: dict[str, str]) -> tuple[Path, str]:
    """Create a minimal valid graph used by installed state, roadmap, agent, and outcome commands."""

    _initialize_git(path, environment)
    feature = path / "codeops" / "features" / "sample"
    feature.mkdir(parents=True)
    artifact = path / "artifact.md"
    artifact.write_text("# Certification artifact\n", encoding="utf-8", newline="\n")
    revision = "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest()

    def node(identity: str, kind: str, status: str, **extra: object) -> dict[str, object]:
        value: dict[str, object] = {
            "id": identity,
            "type": kind,
            "title": identity,
            "status": status,
            "semanticSources": [{
                "path": "artifact.md",
                "selector": {"kind": "whole-file"},
                "normalization": "utf8-lf-trim-trailing-v1",
                "digest": "sha256",
            }],
            "revision": revision,
            "edges": [],
            "validations": [],
        }
        value.update(extra)
        return value

    plan_validations = [
        {
            "upstream": "sample/SPEC-001", "relation": "depends-on", "revision": revision,
            "gate": gate, "validatedAt": "2026-08-07T00:00:00Z",
        }
        for gate in ("plan", "execution")
    ] + [{
        "upstream": "sample/TASK-001", "relation": "implemented-by", "revision": revision,
        "gate": "execution", "validatedAt": "2026-08-07T00:00:00Z",
    }]
    specification_validations = [
        {
            "upstream": "sample/AC-001", "relation": "accepted-by", "revision": revision,
            "gate": gate, "validatedAt": "2026-08-07T00:00:00Z",
        }
        for gate in ("plan", "execution")
    ]
    graph = {
        "schema": 2,
        "feature": "sample",
        "nodes": [
            node("RD-001", "requirement", "approved"),
            node(
                "PLAN-001", "plan", "approved",
                edges=[
                    {"relation": "depends-on", "target": "sample/SPEC-001"},
                    {"relation": "implemented-by", "target": "sample/TASK-001"},
                ],
                evidence=["commit:certification"],
                validations=plan_validations,
            ),
            node("TASK-001", "task", "pending"),
            node(
                "SPEC-001", "specification", "approved",
                edges=[{"relation": "accepted-by", "target": "sample/AC-001"}],
                validations=specification_validations,
            ),
            node(
                "AC-001", "criterion", "approved",
                edges=[{"relation": "tested-by", "target": "sample/ST-001"}],
            ),
            node("ST-001", "test", "red-confirmed"),
        ],
    }
    _write_json(feature / "traceability.json", graph)
    (path / "codeops" / ".codeops.yml").write_text(
        "codeopsLayout: nested\nschema: 1\n", encoding="utf-8", newline="\n",
    )
    (path / "codeops" / "00-roadmap.md").write_text(
        "# Portfolio Roadmap\n\n> **Features**: 0 / 1 done\n> **Last Updated**: 1999-01-01\n\n"
        "| Feature | Roadmap | Stage Summary | Progress | Status | Last Updated |\n"
        "|---------|---------|---------------|----------|--------|--------------|\n"
        "| sample | [→](features/sample/00-roadmap.md) | execution | 0/1 RDs | ⬜ | 1999-01-01 |\n",
        encoding="utf-8", newline="\n",
    )
    (feature / "00-roadmap.md").write_text(
        "# Feature Roadmap\n\n> **Progress**: 0 / 1 (0%)\n> **Last Updated**: 1999-01-01\n\n"
        "| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |\n"
        "|----|-------|----|------|-------|--------|--------------|----------------------|\n"
        "| RD-001 | Requirement | — | — | Done | done | 1999-01-01 | — |\n",
        encoding="utf-8", newline="\n",
    )
    _commit_all(path, "certification baseline", environment)
    return feature / "traceability.json", revision


def _scenario_result(
    commands: Sequence[tuple[str, ...]], cwd: Path, environment: dict[str, str],
    *, accepted_exits: set[int] | None = None,
) -> tuple[bool, str]:
    """Run a concrete scenario and summarize only its command-level result."""

    accepted = accepted_exits or {0}
    results = [run_command(command, cwd=cwd, environment=environment) for command in commands]
    passed = all(result.exit_code in accepted for result in results)
    detail = "all concrete commands completed with expected exits" if passed else "one or more concrete commands failed"
    return passed, detail


def _codex_commands(stdout: str) -> list[str]:
    """Extract actual agent command strings from Codex JSONL events without retaining output."""

    observed: list[str] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"command", "cmd"} and isinstance(child, str) and child.strip():
                    observed.append(child)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for line in stdout.splitlines():
        try:
            visit(json.loads(line))
        except json.JSONDecodeError:
            continue
    return observed


def _append_codex_commands(path: Path, commands: Sequence[str]) -> None:
    """Append command-only Codex events to the inherited evidence sink."""

    if not commands:
        return
    records = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    if not isinstance(records, list):
        raise RuntimeError("Codex command evidence sink is malformed")
    records.extend({"argv": ["codex-agent-command", command], "cwd": "<CODEX_WORKSPACE>", "exitCode": 0} for command in commands)
    _write_json(path, records)


def _remove_certification_install(
    codex: str, marketplace_name: str, root: Path, environment: dict[str, str],
) -> list[str]:
    """Remove and verify absence of only the candidate-owned temporary installation."""

    errors: list[str] = []
    for command in (
        (codex, "plugin", "remove", f"codeops@{marketplace_name}"),
        (codex, "plugin", "marketplace", "remove", marketplace_name),
    ):
        run_command(command, cwd=root, environment=environment)
    for command, identity in (
        ((codex, "plugin", "list", "--json"), f"codeops@{marketplace_name}"),
        ((codex, "plugin", "marketplace", "list", "--json"), marketplace_name),
    ):
        result = run_command(command, cwd=root, environment=environment)
        if result.exit_code != 0:
            errors.append(f"cleanup verification command failed: {' '.join(command)}")
        elif identity in result.stdout:
            errors.append(f"cleanup left installed identity: {identity}")
    return errors


def _prepare_interrupted_recovery(path: Path, environment: dict[str, str]) -> tuple[Path, Path, Path]:
    """Create a valid abandoned transaction that native recovery must roll back."""

    graph_path, _ = _prepare_lifecycle_project(path, environment)
    before = graph_path.read_bytes()
    after_value = json.loads(before)
    after_value["nodes"][2]["status"] = "implemented"
    after = (json.dumps(after_value, indent=2, sort_keys=True) + "\n").encode("utf-8")
    graph_path.write_bytes(after)
    state = path / "codeops" / ".state-transactions"
    state.mkdir()
    operation = "windows-certification-recovery"
    nonce = "windows-certification-nonce"
    owner = {
        "schemaVersion": 1,
        "backend": "windows-filetime",
        "pid": 2147483647,
        "creationFileTime": "1",
    }
    before_image = f"{operation}.before"
    after_image = f"{operation}.after"
    (state / before_image).write_bytes(before)
    (state / after_image).write_bytes(after)
    (state / f"{operation}.lock").write_text(
        json.dumps({"operationId": operation, "owner": owner, "nonce": nonce}), encoding="utf-8",
    )
    record = {
        "path": graph_path.relative_to(path).as_posix(),
        "beforeHash": "sha256:" + hashlib.sha256(before).hexdigest(),
        "afterHash": "sha256:" + hashlib.sha256(after).hexdigest(),
    }
    _write_json(state / f"{operation}.journal.json", {
        "schema": 1,
        "operationId": operation,
        "lockNonce": nonce,
        "owner": owner,
        "direction": None,
        "graphs": [{
            **record,
            "beforeImage": before_image,
            "afterImage": after_image,
            "committed": True,
        }],
    })
    request = path / "recovery.json"
    _write_json(request, {
        "schema": 1,
        "operationId": operation,
        "direction": "rollback",
        "expectedLock": nonce,
        "expectedOwner": owner,
        "graphs": [record],
    })
    return request, graph_path, state


def _capture(args: argparse.Namespace, cleanup: list[tuple[str, str, Path, dict[str, str]]]) -> Path:
    root = args.root.resolve()
    candidate = args.candidate.resolve()
    output = args.output.resolve()
    if os.name != "nt" or platform.release() != "11" or sys.platform != "win32":
        raise RuntimeError("capture requires native Windows 11")
    if os.environ.get("WSL_DISTRO_NAME") or os.environ.get("WSL_INTEROP"):
        raise RuntimeError("capture refuses WSL execution")
    authority_path = args.authority.resolve()
    if _git(root, "status", "--porcelain"):
        raise RuntimeError("capture requires a clean repository")
    head = _git(root, "rev-parse", "HEAD")
    if not candidate.is_file() or not zipfile.is_zipfile(candidate):
        raise RuntimeError("candidate must be a readable plugin ZIP")

    with tempfile.TemporaryDirectory(prefix="codeops-windows-candidate-") as raw:
        extracted = Path(raw)
        archive_root = extracted / "plugin"
        archive_root.mkdir()
        with zipfile.ZipFile(candidate) as archive:
            archive.extractall(archive_root)
        plugin_root = _candidate_root(archive_root)
        manifest = json.loads((plugin_root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        version = manifest.get("version")
        source_manifest = json.loads((root / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        if not isinstance(version, str) or version != source_manifest.get("version"):
            raise RuntimeError("packed candidate version must match the source manifest")
        authority, authority_errors = load_authority(authority_path, version)
        if authority_errors or authority is None:
            raise RuntimeError("release authority failed validation: " + "; ".join(authority_errors))
        candidate_errors = verify_candidate(candidate, authority)
        if candidate_errors:
            raise RuntimeError("; ".join(candidate_errors))
        if not (plugin_root / "scripts" / "codeops_verify.py").is_file():
            raise RuntimeError("packed candidate is missing portable verification tooling")

        records_root, manifest_path = _prepare_output(output, version)
        timestamp = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        base_environment = dict(os.environ)
        base_environment.update({"PLUGIN_ROOT": str(plugin_root), "PLUGIN_DATA": str(records_root / "plugin-data"), "PYTHONUTF8": "1"})
        Path(base_environment["PLUGIN_DATA"]).mkdir(parents=True)
        marketplace_name = f"codeops-cert-{authority['candidateSha256'][:12]}"
        marketplace = extracted / ".agents" / "plugins" / "marketplace.json"
        relative_plugin = plugin_root.relative_to(extracted).as_posix()
        _write_json(marketplace, {
            "name": marketplace_name,
            "interface": {"displayName": "CodeOps Windows Certification"},
            "plugins": [{
                "name": "codeops",
                "source": {"source": "local", "path": f"./{relative_plugin}"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Developer Tools",
            }],
        })
        cleanup.append((args.codex, marketplace_name, root, base_environment))
        _remove_certification_install(args.codex, marketplace_name, root, base_environment)

        workspace = extracted / "workflow-project"
        _initialize_git(workspace, base_environment)
        (workspace / "README.md").write_text(
            "# Hello CLI certification\n\n"
            "Create requirements and a plan for a Python 3.10+ `hello.py` command. The command takes "
            "no arguments, writes exactly `hello` plus one newline to stdout, writes nothing to "
            "stderr, returns 0, uses only the Python standard library, and needs unit tests. Produce "
            "requirements, planning, and preflight artifacts only; do not implement source code.\n",
            encoding="utf-8", newline="\n",
        )
        _commit_all(workspace, "workflow seed", base_environment)

        lifecycle = extracted / "lifecycle-project"
        graph_path, revision = _prepare_lifecycle_project(lifecycle, base_environment)
        transition_request = lifecycle / "transition.json"
        _write_json(transition_request, {
            "schema": 1,
            "operationId": "windows-certification-transition",
            "target": "sample/TASK-001",
            "expected": {"status": "pending", "revision": revision},
            "requested": {"status": "implemented"},
            "gate": "plan",
            "sourceUpdates": [],
            "validationAdditions": [],
            "validationRemovals": [],
            "staleReason": None,
            "evidence": {"implementationEvidence": "native certification lifecycle"},
        })
        recovery_request, recovery_graph, recovery_state = _prepare_interrupted_recovery(
            extracted / "recovery-project", base_environment,
        )
        (lifecycle / "codeops" / "codeops.json").write_text(
            json.dumps({
                "schema": 1,
                "mode": "strict",
                "artifacts": {"layout": "nested", "root": "codeops"},
                "quality": {"independentReview": True, "minimumReviewers": 1, "stopOnMajorFinding": True},
                "metrics": {"enabled": True},
            }, indent=2, sort_keys=True) + "\n",
            encoding="utf-8", newline="\n",
        )
        _commit_all(lifecycle, "certification requests", base_environment)
        _commit_all(recovery_graph.parents[3], "interrupted recovery fixture", base_environment)

        migration = extracted / "migration-project"
        shutil.copytree(root / "scripts" / "fixtures" / "flat-repo", migration)
        _initialize_git(migration, base_environment)
        _commit_all(migration, "migration baseline", base_environment)

        state = plugin_root / "scripts" / "codeops_state.py"
        requirements_skill = plugin_root / "skills" / "make-requirements" / "SKILL.md"
        planning_skill = plugin_root / "skills" / "make-plan" / "SKILL.md"
        preflight_skill = plugin_root / "skills" / "preflight" / "SKILL.md"
        scenario_commands: dict[str, tuple[tuple[str, ...], ...]] = {
            "installation": (
                (args.codex, "plugin", "marketplace", "add", str(extracted), "--json"),
                (args.codex, "plugin", "add", f"codeops@{marketplace_name}", "--json"),
            ),
            "enablement": ((args.codex, "plugin", "list", "--marketplace", marketplace_name, "--json"),),
            "session-preflight": ((
                "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                str(plugin_root / "scripts" / "codeops-windows-preflight.ps1"), "-ResolvePython",
            ),),
            "requirements": ((
                args.codex, "exec", "--json", "--ephemeral", "--dangerously-bypass-hook-trust",
                "--sandbox", "danger-full-access", "--cd", str(workspace),
                f'Read and follow the exact installed candidate skill at "{requirements_skill}" with --auto-design; do not resolve a same-named skill from another marketplace. The README is the complete product scope. Create a decision-complete requirements set without implementation. Use only native Windows PowerShell and native executables.',
            ),),
            "planning": ((
                args.codex, "exec", "--json", "--ephemeral", "--dangerously-bypass-hook-trust",
                "--sandbox", "danger-full-access", "--cd", str(workspace),
                f'Read and follow the exact installed candidate skill at "{planning_skill}" with --auto-design; do not resolve a same-named skill from another marketplace. Plan the approved hello CLI requirements. Create a complete plan and traceability, but do not implement. Use only native Windows PowerShell and native executables.',
            ),),
            "preflight-audit": ((
                args.codex, "exec", "--json", "--ephemeral", "--dangerously-bypass-hook-trust",
                "--sandbox", "danger-full-access", "--cd", str(workspace),
                f'Read and follow the exact installed candidate skill at "{preflight_skill}" with --auto-design; do not resolve a same-named skill from another marketplace. Audit the hello CLI plan, resolve eligible technical findings, and leave a durable readiness verdict. Do not implement. Use only native Windows PowerShell and native executables.',
            ),),
            "execution-transition-recovery": (
                (sys.executable, str(state), "--root", str(lifecycle), "--request", str(transition_request), "--json", "transition"),
                (sys.executable, str(state), "--root", str(recovery_graph.parents[3]), "--request", str(recovery_request), "--json", "transition-recover"),
            ),
            "migration": ((sys.executable, str(plugin_root / "scripts" / "codeops_migrate.py"), "apply", "--root", str(migration), "--json"),),
            "roadmap": (
                (sys.executable, str(plugin_root / "scripts" / "codeops_roadmap.py"), "sync", "--root", str(lifecycle), "--write", "--date", "2026-08-07", "--json"),
                (sys.executable, str(plugin_root / "scripts" / "codeops_roadmap.py"), "sync", "--root", str(lifecycle), "--check", "--date", "2026-08-07", "--json"),
            ),
            "worktree": (
                (sys.executable, str(plugin_root / "scripts" / "codeops_worktree.py"), "list", "--root", str(lifecycle), "--json"),
                (sys.executable, str(plugin_root / "scripts" / "codeops_worktree.py"), "new", "certification", "--root", str(lifecycle), "--dry-run", "--json"),
            ),
            "agent-install-check": (
                (sys.executable, str(plugin_root / "scripts" / "install_agents.py"), "--project", str(lifecycle), "--roles", "explorer"),
                (sys.executable, str(plugin_root / "scripts" / "install_agents.py"), "--project", str(lifecycle), "--roles", "explorer", "--check"),
            ),
            "outcomes": (
                (sys.executable, str(plugin_root / "scripts" / "codeops_outcomes.py"), "emit", "--root", str(lifecycle), "--event", "verification-run", "--stage", "verification", "--result", "pass"),
                (sys.executable, str(plugin_root / "scripts" / "codeops_outcomes.py"), "report", "--root", str(lifecycle), "--json"),
            ),
            "verification": tuple(
                (sys.executable, str(plugin_root / "scripts" / "codeops_verify.py"), gate, "--root", str(plugin_root))
                for gate in ("docs", "migration", "roadmap", "compact")
            ),
        }
        scenarios: list[dict[str, str]] = []
        trace: list[dict[str, object]] = []
        scenario_failures: list[str] = []
        for scenario in REQUIRED_SCENARIOS:
            raw_trace = records_root / f".{scenario}-commands.json"
            environment = {**base_environment, "CODEOPS_COMMAND_EVIDENCE": str(raw_trace.resolve())}
            results = [
                run_command(command, cwd=workspace if scenario in {"requirements", "planning", "preflight-audit"} else plugin_root, environment=environment)
                for command in scenario_commands[scenario]
            ]
            if scenario in {"requirements", "planning", "preflight-audit"}:
                for result in results:
                    observed_commands = _codex_commands(result.stdout)
                    if not observed_commands:
                        raise RuntimeError(f"scenario {scenario} exposed no Codex command events")
                    _append_codex_commands(raw_trace, observed_commands)
            expected_exits = tuple(0 for _ in results)
            passed = all(result.exit_code == expected for result, expected in zip(results, expected_exits))
            if scenario == "enablement" and passed:
                listing = json.loads(results[0].stdout)
                installed = listing.get("installed", []) if isinstance(listing, dict) else []
                passed = any(
                    item.get("pluginId") == f"codeops@{marketplace_name}" and item.get("enabled") is True
                    for item in installed if isinstance(item, dict)
                )
            postconditions = {
                "requirements": bool(_git(workspace, "status", "--porcelain")),
                "planning": bool(_git(workspace, "status", "--porcelain")),
                "preflight-audit": bool(_git(workspace, "status", "--porcelain")),
                "execution-transition-recovery": (
                    json.loads(graph_path.read_text(encoding="utf-8"))["nodes"][2]["status"] == "implemented"
                    and json.loads(recovery_graph.read_text(encoding="utf-8"))["nodes"][2]["status"] == "pending"
                    and (recovery_state / "windows-certification-recovery.completed.json").is_file()
                    and not any(
                        path.name != "windows-certification-recovery.completed.json"
                        for path in recovery_state.iterdir()
                    )
                ),
                "migration": (migration / "codeops" / ".codeops.yml").is_file(),
                "agent-install-check": (lifecycle / ".codex" / "agents" / "explorer.toml").is_file(),
            }
            passed = passed and postconditions.get(scenario, True)
            if not passed:
                scenario_failures.append(
                    f"{scenario}: exits={[result.exit_code for result in results]}, "
                    f"postcondition={postconditions.get(scenario, True)}"
                )
            if passed and scenario in {"requirements", "planning", "preflight-audit"}:
                _commit_all(workspace, f"certification {scenario}", base_environment)
            if passed and scenario in {"execution-transition-recovery", "roadmap", "agent-install-check"}:
                _commit_all(lifecycle, f"certification {scenario}", base_environment)
            status = "pass" if passed else "fail"
            record = records_root / f"{scenario}.json"
            _write_json(record, {
                "schemaVersion": 1, "scenarioId": scenario, "result": status,
                "commandClass": "native-codex" if scenario in {"installation", "enablement", "requirements", "planning", "preflight-audit"} else "native-python",
                "timestamp": timestamp,
                "summary": f"installed-plugin {scenario} workflow completed with verified postconditions" if passed else f"installed-plugin {scenario} workflow failed",
            })
            scenarios.append({
                "id": scenario, "status": status,
                "record": record.relative_to(output).as_posix(), "sha256": _sha256(record),
            })
            if not raw_trace.is_file():
                raise RuntimeError(f"scenario {scenario} produced no inherited command evidence")
            raw_records = json.loads(raw_trace.read_text(encoding="utf-8"))
            if not isinstance(raw_records, list) or not raw_records:
                raise RuntimeError(f"scenario {scenario} command evidence is empty or malformed")
            for command in raw_records:
                command_argv = command.get("argv") if isinstance(command, dict) else None
                exit_code = command.get("exitCode") if isinstance(command, dict) else None
                if not isinstance(command_argv, list) or not command_argv or not isinstance(exit_code, int):
                    raise RuntimeError(f"scenario {scenario} command evidence is malformed")
                trace.append({
                    "scenarioId": scenario,
                    "executable": _normalized(str(command_argv[0]), plugin_root),
                    "arguments": [_normalized(str(item), plugin_root) for item in command_argv[1:]],
                    "exitClass": "success" if exit_code == 0 else "expected-failure",
                })
            raw_trace.unlink()
        if scenario_failures:
            _discard_capture(records_root, manifest_path)
            raise RuntimeError("installed scenarios failed: " + "; ".join(scenario_failures))
        trace_path = records_root / "commands.json"
        if any(PROHIBITED_RUNTIME_RE.search(" ".join([
            str(command["executable"]), *(str(item) for item in command["arguments"]),
        ])) for command in trace):
            raise RuntimeError("captured command evidence contains a prohibited runtime")
        _write_json(trace_path, trace)
        git_version = _git(root, "--version")
        codex_result = run_command((args.codex, "--version"), cwd=root, environment=base_environment)
        if codex_result.exit_code != 0 or not codex_result.stdout.strip():
            raise RuntimeError("unable to query native Codex version")
        build = int(platform.version().split(".")[-1])
        architecture = platform.machine().upper()
        _write_json(manifest_path, {
            "schemaVersion": 1, "pluginVersion": version, "commit": authority["sourceCommit"],
            "candidateSha256": _sha256(candidate),
            "reviewer": {"github": args.reviewer, "timestamp": timestamp}, "kind": "cli",
            "host": {"edition": "Windows 11", "build": build, "architecture": architecture, "native": True},
            "tools": {"python": platform.python_version(), "git": git_version, "codex": codex_result.stdout.strip()},
            "ci": {"runId": authority["ci"]["runId"], "commit": authority["ci"]["headCommit"], "conclusion": authority["ci"]["conclusion"], "runner": "windows-11-arm"},
            "captureVersion": 1,
            "assertions": {"wslInvoked": False, "gitBashInvoked": False},
            "commandTrace": {"path": trace_path.relative_to(output).as_posix(), "sha256": _sha256(trace_path)},
            "scenarios": scenarios,
        })
        errors = validate_evidence_set(
            output,
            cli_path=manifest_path,
            desktop_path=None,
            expected_version=version,
            expected_commit=authority["sourceCommit"],
            expected_candidate_sha256=authority["candidateSha256"],
            expected_ci_commit=authority["ci"]["headCommit"],
        )
        if errors:
            _discard_capture(records_root, manifest_path)
            raise RuntimeError("captured evidence failed validation: " + "; ".join(errors))
        return manifest_path


def capture(args: argparse.Namespace) -> Path:
    """Capture evidence and always remove the uniquely named global Codex installation."""

    cleanup: list[tuple[str, str, Path, dict[str, str]]] = []
    try:
        result = _capture(args, cleanup)
    except Exception as primary:
        cleanup_errors = [
            error
            for target in cleanup
            for error in _remove_certification_install(*target)
        ]
        if cleanup_errors:
            raise RuntimeError(f"{primary}; certification cleanup failed: {'; '.join(cleanup_errors)}") from primary
        raise
    cleanup_errors = [
        error
        for target in cleanup
        for error in _remove_certification_install(*target)
    ]
    if cleanup_errors:
        raise RuntimeError("certification cleanup failed: " + "; ".join(cleanup_errors))
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = capture(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        print(f"Windows evidence capture failed: {error}", file=sys.stderr)
        return 1
    print(f"Windows evidence captured: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
