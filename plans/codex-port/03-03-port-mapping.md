# Port Mapping

## Skills

| Claude surface | Codex decision | Notes |
|---|---|---|
| `make_requirements` | Keep and enhance | Add artifact graph, domain lenses, and deterministic coverage validation. |
| `retro_requirements` | Keep | Integrate as an evidence-source mode of requirements discovery; preserve confidence and bug/feature triage. |
| `grill_me` | Keep behavior; possibly internalize later | Recursive interrogation is foundational. Do not consolidate until triggering and control parity are proven. |
| `make_plan` | Keep and enhance | Add readiness proof and bidirectional traceability. |
| `preflight` | Keep and enhance | Split semantic review from deterministic conformance; dynamically select domain auditors. |
| `exec_plan` | Keep and rewrite orchestration | Preserve update-before-verify, spec-first execution, commit modes, recovery, and review gates. |
| `roadmap` | Keep and enhance | Make lifecycle/readiness derived and recoverable; retain archive/review/show/update behavior. |
| `techdocs` | Keep | Make docs traceable to authoritative architecture and shipped behavior. |
| `upgrade_plan` | Keep initially | Expand to artifact-schema migrations; reassess after stable schema tooling exists. |
| `setup_codeops` | Keep and rewrite | Scaffold Codex layout/config/guidance and safely migrate existing CodeOps projects. |
| `setup_routing` | Replace | Use capability/risk-based agent selection and Codex configuration; remove Claude model semantics. |

## Commands

| Category | Decision |
|---|---|
| Thin aliases into skills | Remove from correctness surface; natural language and explicit skills replace them. |
| `gitcm` / `gitcmp` | Convert to optional skills or prompts; retain guarded behavior. |
| GitHub issue commands | Convert to one Codex skill with read/write modes and explicit authorization gates. |
| `analyze_project` | Replace with CodeOps augmentation of `AGENTS.md` and detected project config; do not duplicate Codex `/init`. |
| `migrate_clinerules` | Exclude from core; offer only as a separate legacy migration utility if demanded. |
| `clean_jsdoc` | Retain as an optional skill. |
| stats/retro commands | Replace invocation analytics with opt-in outcome-quality reporting. |

## Agents

| Claude agent | Codex role |
|---|---|
| `codebase-scout` | Explorer with read-only sandbox |
| `plan-task-executor*` | One executor role with capability-based model/effort selection |
| `phase-reviewer` | Correctness/maintainability reviewer |
| `preflight-auditor` | Dynamically scoped semantic auditor |
| `security-auditor` | Security auditor with selected domain checklists |
| `perf-auditor` | Performance auditor |
| `spec-test-author` | Implementation-blind specification-test author |
| `design-challenger` | Independent decision challenger |

The port must prototype whether these are generated project TOML agents or dynamic dispatch packets. Correctness cannot depend on either mechanism being present.

## Hooks

| Existing hook | Decision |
|---|---|
| Session standards injection | Retain, minimize, use `PLUGIN_ROOT`, and document trust. |
| `.codeops.yml` edit warning | Retain and test against `apply_patch` aliases. |
| Skill/agent telemetry | Replace with Codex payload fixtures and outcome-oriented events, or omit if AR-007 chooses removal. |
| Readiness enforcement | Add a narrow pre-execution check where Codex hook semantics can safely enforce it; never overclaim complete enforcement. |

## Scripts

- Port roadmap synchronization and migration engines first; they already have deterministic fixtures.
- Replace agent sync with a Codex agent-template generator only if AR-010 validates it.
- Rewrite validation around Codex manifests, skill metadata, artifact schemas, traceability, and scenario fixtures.
- Change writable telemetry/state from `~/.claude` to `PLUGIN_DATA` or an explicit CodeOps data root.
- Generalize `codeops-worktree` to launch Codex and optionally support multiple agent CLIs.

## Documentation

Rewrite installation, verification, updates, hooks trust, project setup, skills, agents, and troubleshooting for Codex. Preserve conceptual tutorials but validate every command and screenshot claim on each supported surface.

