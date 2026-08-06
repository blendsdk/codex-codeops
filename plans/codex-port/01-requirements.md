# Port Requirements

## Product requirements

### RD-001 — Codex-native distribution

The product shall install from `git@github.com:blendsdk/codex-codeops.git` as a valid Codex plugin with a `.codex-plugin/plugin.json`, Codex marketplace metadata, bundled skills, trusted lifecycle hooks, scripts, references, and optional assets. It shall not depend on Claude Code directories or commands at runtime. Installation, upgrade, disable, and uninstall flows shall be verified from a clean environment.

### RD-002 — Recursive ambiguity closure

The product shall recursively discover material ambiguities in requirements, system design, component specifications, testing strategy, and execution plans. A later-stage discovery shall be able to invalidate an earlier gate, reopen its owning artifact, and trigger downstream revalidation.

### RD-003 — Requirements engineering

The product shall support new-system discovery, existing-system reconstruction, addition of requirements, review of requirement sets, explicit scope/exclusions, domain terminology, actors, behavior, invariants, failure modes, measurable quality attributes, and approved deferrals.

### RD-004 — Complex-system specification

The product shall support multiple system classes without assuming a web application. It shall select domain lenses appropriate to compilers/languages, financial systems, web/API systems, distributed systems, security-sensitive systems, data systems, developer tools, and other detected domains.

### RD-005 — Architecture and component planning

The product shall produce codebase-grounded current-state analysis, system decomposition, interfaces, state transitions, algorithms where behaviorally relevant, data ownership, failure/recovery behavior, security boundaries, concurrency semantics, performance constraints, migration/compatibility behavior, and objective acceptance criteria.

### RD-006 — Bidirectional traceability

The product shall trace requirements through decisions, specifications, acceptance criteria, tests, execution tasks, implementation changes, and verification evidence. It shall detect orphaned or contradictory nodes in either direction.

### RD-007 — Readiness proof

Before execution, the product shall generate a deterministic readiness report covering open material ambiguities, cross-document conflicts, interface completeness, acceptance-test coverage, task/specification mapping, unresolved high-risk assumptions, and approved deferrals.

### RD-008 — Specification-first execution

The product shall preserve the ordering `specification → specification tests → confirmed red state → implementation → green state → implementation tests → full verification` where the selected quality profile requires specification tests. Specification-test expectations shall remain implementation-independent and immutable during execution unless the governing specification changes through the ambiguity protocol.

### RD-009 — Durable execution state

Task progress shall be durably recorded before verification and promoted to complete only after verification passes. Session loss, compaction, or agent failure shall not require conversation history to determine the next safe action.

### RD-010 — Independent quality review

The product shall dynamically select independent reviewers according to risk. At minimum it shall support correctness, maintainability, standards, security, performance, data integrity, concurrency, and specification-test-integrity lenses. Reviewers shall attempt to falsify claims and cite repository evidence.

### RD-011 — Project and portfolio tracking

The product shall track features, requirements, plans, tasks, dependencies, blockers, ambiguity status, lifecycle stage, readiness, execution progress, verification state, review findings, and archived work. Status shall be recoverable from durable artifacts and validated against disk state.

### RD-012 — Controlled autonomy

The product may decide non-material, reversible implementation details when the governing specification explicitly delegates discretion. It shall never silently decide a material ambiguity.

### RD-013 — Codex project guidance

The product shall use `AGENTS.md` for durable project guidance and `.codex/config.toml` or a CodeOps configuration file for operational configuration. It shall not embed mutable machine configuration into prose guidance when a structured owner exists.

### RD-014 — Hooks and enforcement

Lifecycle hooks shall inject only essential universal standards, warn or block unsafe workflow violations where Codex supports it, and avoid treating hooks as a complete security boundary. Hook trust requirements shall be explicit during installation.

### RD-015 — Agent portability

Agent roles shall be expressed independently of Claude model names and tools. Model selection shall be capability based, overridable, and degrade safely to inline execution when custom agents or subagent capacity are unavailable.

### RD-016 — Commands and discoverability

Core behavior shall be available through natural-language-triggered skills. Thin slash-command aliases shall not be required for correctness. Optional custom prompts may improve ergonomics but must not become a hidden runtime dependency.

### RD-017 — Deterministic validation

Schemas, traceability, progress transitions, roadmap derivation, migration, artifact links, version compatibility, and hook fixtures shall be validated by deterministic scripts where feasible. Model review shall focus on semantic completeness and consistency rather than mechanically checkable structure.

### RD-018 — Privacy and local data

No project content shall be uploaded by CodeOps telemetry. Any metrics shall be local, opt-in, documented, and oriented toward outcome quality rather than invocation counts.

### RD-019 — Migration and coexistence

The product shall define how existing CodeOps projects and artifacts are recognized, validated, migrated, or used without migration. It shall never destructively rewrite an existing project without preview, clean-state checks, and explicit authorization.

### RD-020 — Evidence-backed parity

No feature shall be described as ported solely because its prompt text was copied. Parity requires an executable Codex scenario test demonstrating equivalent or stronger behavior.

### RD-021 — Product README

The repository shall include a polished root `README.md` that explains the product promise, suitability for complex systems, recursive ambiguity-elimination workflow, project tracking, supported Codex surfaces, installation from this repository, verification, quick start, update/uninstall procedures, trust and permission implications, principal skills, example lifecycle, platform requirements, migration status, contribution/testing commands, and license. Every command shall be tested against the release artifact, and unreleased capabilities shall be labeled rather than presented as available.

### RD-022 — Native Windows runtime

CodeOps shall support every shipped core workflow on Windows 11 through native Codex, PowerShell,
Git for Windows, and Python 3.x. It shall not require Git Bash or WSL. WSL may be installed and
enabled without affecting readiness, but CodeOps shall never invoke `wsl.exe`, launch a WSL
distribution, translate paths through `/mnt`, or delegate any operation to WSL. If CodeOps is
actually executing inside WSL, it shall stop before project mutation and direct the user to launch
Codex natively on Windows. These boundaries are user-approved in AR-015, AR-016, and AR-021.

Before a Windows workflow proceeds, CodeOps shall run one authoritative prerequisite check once per
session and recheck mutation-sensitive conditions immediately before project writes. The check
shall execute a native interpreter probe and accept any functioning Python major version 3 without
pinning its minor or patch version. Missing, nonfunctional, or non-Python-3 interpreters shall
produce an actionable blocking result before project mutation and shall never trigger automatic
installation. The same check shall validate the supported Windows version, native Codex execution
and sandbox state, Git for Windows, the writable local workspace, plugin enablement, hook
availability/trust, and required path/filesystem capabilities. Results shall be deterministic and
classified as `READY`, `WARNING`, or `BLOCKED`; an operational unelevated Codex sandbox produces a
warning rather than a block. These behaviors are user-approved in AR-016, AR-017, and AR-019.

The deterministic control layer shall provide native Windows implementations for process-owner
identity, stale-lock detection, PID-reuse protection, atomic graph writes, recovery, migration,
roadmap synchronization and compaction, worktree snapshots, optional-agent installation, outcome
storage, hooks, and every other shipped utility. Process/API uncertainty shall continue to fail
closed. Durable paths shall use a host-independent canonical representation, and generated path
components shall reject Windows device names and other platform-invalid forms before any write.
Local writable filesystems are the initial supported boundary; UNC and network workspaces remain
unsupported until separately certified, per AR-018.

### RD-023 — Native Windows certification

CodeOps shall not claim Windows support until automated Windows CI and retained real-host evidence
prove the native runtime contract in RD-022. Windows CI shall exercise specification and
implementation tests for prerequisites, hooks, state transitions, concurrent ownership,
interrupted writes, stale-owner recovery, migration, roadmap derivation, path handling, hostile
identifiers, and Linux-regression parity. At least one real Windows 11 installation shall prove
plugin installation and enablement, hook review/trust, and representative requirements, planning,
preflight, execution-state transition/recovery, migration, roadmap, and verification workflows.
The Windows desktop app shall additionally pass installation and representative-workflow smoke
testing. Documentation and release metadata may claim Windows support only after that evidence is
retained and version-matched. This evidence boundary is user-approved in AR-015 and AR-020.

## Quality attributes

| Attribute | Requirement |
|---|---|
| Correctness | No material ambiguity may bypass the owning gate. |
| Recoverability | A new session can reconstruct exact workflow state using repository artifacts and Git evidence. |
| Auditability | Every gate decision and approved deferral has a durable basis. |
| Adaptability | Domain lenses and review teams adapt to the system and risk without weakening universal gates. |
| Maintainability | One authoritative owner per fact; generated views never become competing truth. |
| Portability | Claude-specific compatibility may be used only when explicitly tested and isolated. |
| Efficiency | Context is progressively disclosed; agents receive bounded packets; deterministic checks avoid repeated semantic scanning. |
| Safety | Destructive operations, external side effects, financial/security decisions, and irreversible changes require explicit authority. |

## Explicit non-goals for the first release

- Reproducing Claude command names solely for familiarity.
- Preserving obsolete Cline migration behavior in the core plugin.
- Matching invocation telemetry for its own sake.
- Guaranteeing a particular model name indefinitely.
- Treating document count reduction as a success metric.
- Starting implementation before the port's own requirements and architecture gates pass.
