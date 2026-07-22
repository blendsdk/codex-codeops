# Target Architecture

## Design principles

1. Preserve recursive specification rigor; remove only redundant ceremony and host-specific machinery.
2. Keep one authoritative owner for each fact.
3. Derive indexes, dashboards, and readiness reports from authoritative artifacts.
4. Use deterministic code for structure/state and model reasoning for semantics.
5. Make interruption recovery a primary design requirement.
6. Treat named agents and model routing as optimizations, never correctness dependencies.
7. Fail closed on material ambiguity and fail open to safe inline execution when optional orchestration is unavailable.

## Proposed repository structure

```text
codex/
├── .codex-plugin/
│   └── plugin.json
├── skills/
│   ├── requirements/
│   ├── plan/
│   ├── execute/
│   ├── preflight/
│   ├── roadmap/
│   ├── techdocs/
│   └── setup-codeops/
├── references/
│   ├── ambiguity/
│   ├── domains/
│   ├── artifacts/
│   ├── review/
│   └── migration/
├── scripts/
│   ├── codeops-state
│   ├── codeops-trace
│   ├── codeops-readiness
│   ├── codeops-roadmap
│   ├── codeops-migrate
│   └── validate
├── hooks/
│   └── hooks.json
├── standards/
├── agent-templates/
├── tests/
│   ├── fixtures/
│   ├── conformance/
│   ├── scenarios/
│   └── evals/
├── docs/
├── plans/
└── README.md
```

Final skill count remains an implementation decision. The first port should favor behavioral correspondence with the Claude skills; consolidation happens only after parity tests show no loss of discoverability or control.

## Runtime layers

### 1. Workflow layer

Skills own semantic protocols: discovery, ambiguity interviews, design, planning, execution, review, documentation, and tracking.

### 2. Artifact layer

Versioned schemas define requirements, decisions, specifications, acceptance criteria, tests, tasks, findings, evidence, and lifecycle state. Markdown remains human-readable; stable identifiers and constrained metadata make validation possible.

### 3. Deterministic control layer

Scripts validate links and state transitions, compute readiness, derive roadmap views, detect drift, and reconstruct resume state. Scripts do not decide semantics.

### 4. Agent layer

The primary Codex agent owns the coherent system model and user decisions. Bounded subagents perform reconnaissance, independent challenge, audit, specification-test authoring, or execution. The parent reconciles every result.

### 5. Integration layer

Codex manifests, hooks, optional prompts, custom-agent templates, configuration, and installation instructions remain isolated from workflow content.

## Authoritative state model

The artifact graph is:

```text
Requirement
  ↕
Decision / ambiguity resolution
  ↕
Specification and invariant
  ↕
Acceptance criterion
  ↕
Specification test
  ↕
Execution task
  ↕
Implementation evidence
  ↕
Verification and review evidence
```

Generated roadmap/status views may summarize this graph but never own its facts.

## Configuration boundaries

- `AGENTS.md`: concise project instructions, verification commands, conventions, and CodeOps entry guidance.
- `codeops/config.yml` or equivalent: CodeOps artifact layout, strictness, review policy, migration state, and optional metrics.
- `.codex/config.toml`: Codex-specific hooks, agent defaults, sandbox, MCP, and model settings where project-local configuration is appropriate.
- `.codex/agents/*.toml`: optional generated or hand-authored specialist agents, if the prototype validates this distribution model.

## Agent architecture

Roles are capability descriptions rather than model aliases:

- explorer
- requirements challenger
- design challenger
- traceability auditor
- specification-test author
- executor
- correctness reviewer
- security auditor
- financial-integrity auditor
- performance auditor
- concurrency auditor

Every dispatch packet declares scope, inputs, forbidden actions, expected evidence, and output schema. If the named role is unavailable, the parent may spawn a generic subagent with the same complete packet or execute inline without lowering gates.

## Project tracking architecture

Tracking exposes two orthogonal dimensions:

1. **Lifecycle:** discovery, requirements, specification, planning, ready, executing, reviewing, complete, archived.
2. **Readiness/evidence:** ambiguity closure, coverage, conflicts, task completion, verification, findings, blockers, and deferrals.

The roadmap engine calculates status from artifacts and Git state, preserves user-owned descriptive fields, and reports drift instead of silently rewriting ambiguous data.

