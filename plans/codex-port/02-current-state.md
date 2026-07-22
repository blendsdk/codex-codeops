# Current-State Analysis

## Claude baseline

The source at `../codeops` is CodeOps 3.12.0 and currently contains:

| Surface | Count | Current responsibility |
|---|---:|---|
| Skills | 11 | Requirements, planning, execution, reviews, docs, roadmap, routing, and setup |
| Slash commands | 21 | Substantive utilities plus thin aliases into skills |
| Custom agents | 9 | Executors, scouts, reviewers, auditors, challenger, and spec-test author |
| Top-level scripts | 12 | Validation, migration, roadmap engines, telemetry, agent sync, and fixture suites |
| Hook file | 1 | Standards injection, marker warning, and telemetry |
| Shipped workflow/tooling lines | ~16,400 | Markdown protocols, shell utilities, hooks, and standards |

The source already implements several high-value properties that must remain behavioral oracles:

- progressive skill disclosure;
- hard Zero-Ambiguity Gates;
- codebase-grounded plans;
- specification-first task ordering;
- update-before-verify execution state;
- layout-aware flat and nested artifacts;
- per-feature and portfolio roadmaps;
- independent reviewers and domain auditors;
- output-captured verification;
- deterministic migration and roadmap utilities;
- guarded commit modes; and
- metadata-only local telemetry.

## Codex platform facts

Current Codex documentation establishes these relevant capabilities:

- plugins use `.codex-plugin/plugin.json` and may bundle `skills/`, `hooks/`, scripts/references, MCP configuration, apps, and assets;
- skills use progressive disclosure and are available in Codex CLI, IDE, and desktop surfaces;
- persistent repository guidance uses `AGENTS.md`;
- project configuration and hooks may live under `.codex/`;
- custom agents are TOML files under `.codex/agents/` or `~/.codex/agents/`;
- subagents support explicit role prompts, model and reasoning configuration, and sandbox overrides;
- plugin-bundled hooks support the Claude-compatible `CLAUDE_PLUGIN_ROOT`, while `PLUGIN_ROOT` and `PLUGIN_DATA` are the native variables;
- `Edit` and `Write` hook aliases can match `apply_patch`;
- custom slash prompts use `~/.codex/prompts/` and `/prompts:<name>`; plugin packaging does not document Claude-style bundled `commands/` as a component; and
- plugin hooks require explicit user trust unless managed by policy.

## Direct compatibility

### High compatibility

- Most skill bodies and reference documents
- Deterministic roadmap and migration logic
- Git/GitHub command behavior
- SessionStart standards injection
- PreToolUse marker protection
- Progressive disclosure model
- Read-heavy parallel review design
- Verification-output capture

### Requires adaptation

- `.claude-plugin` manifest and marketplace metadata
- `CLAUDE.md` references and generated content
- Claude command frontmatter and shell interpolation
- agent Markdown/YAML to Codex TOML or dynamic dispatch packets
- model names and effort policy
- install/update documentation
- telemetry event parsing and storage paths
- worktree launcher

### Not portable as written

- Claude plugin `commands/` as a bundled slash-command surface
- `.claude/agents/*.md` generation
- `Skill|Task|Agent` telemetry assumptions
- Claude-specific task-list tools
- Opus/Sonnet/Fable routing semantics
- assertions that disabling a plugin is the only hook toggle

## Architectural debt worth removing

These are integration or maintenance costs, not core rigor:

- duplicated thin command aliases;
- version stamps repeated throughout many workflow documents;
- tool-name-specific instructions where outcome constraints suffice;
- configuration-like routing blocks embedded in project prose;
- hard-coded token/bootstrap measurements used as durable policy;
- invocation telemetry that does not measure engineering outcomes;
- separate executor prompts whose primary difference is model name;
- duplicated statements where a single owning document can be cited.

## Main risks

1. **False parity:** copied prompts may appear complete while Codex invocation, hooks, or agents behave differently.
2. **Gate erosion:** simplifying the UX could accidentally allow material assumptions.
3. **State divergence:** roadmap, plan, traceability, and Git state may disagree after interruption.
4. **Agent packaging:** Codex custom agents are not documented as a normal plugin-root component.
5. **Surface variance:** CLI, IDE, and desktop may expose different installation and prompt behavior.
6. **Compatibility burden:** supporting both legacy layouts and a stronger schema can multiply every test path.
7. **Prompt-only enforcement:** critical invariants can drift unless backed by deterministic checks.

## Target repository state

The Codex edition has an independent public GitHub repository at `git@github.com:blendsdk/codex-codeops.git`. The local `codex/` workspace is initialized on `main` with that repository as `origin`. At planning time the remote is empty; no release or installation claim exists yet.
