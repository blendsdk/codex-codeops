---
name: setup-routing
description: >-
  Configures per-project model and effort routing so Opus + high/xhigh thinking is spent only where it changes output quality and high-volume mechanical work runs on Sonnet. Use when the user says "setup-routing", "/setup-routing", "set up model routing", "configure model routing", "route tasks by model", or "make this project use Opus/Sonnet per task". Independently analyzes the repo, classifies it into a sensitivity profile (Opus-dominant, Mixed core/scaffold, Sonnet-default, or a Balanced fallback), proposes a tag-driven routing policy, waits for explicit confirmation, then writes a sentinel-delimited routing block into the project AGENTS.md. The pinned-model executor subagents the policy references ship with the plugin (agents/); customized per-project copies in .codex/agents/ are an opt-in override.
---

# Model & Effort Routing Setup (`setup-routing`)

> **CodeOps Skills Version**: 3.12.0

Configure **per-project model and effort routing** for the project the user is currently in, so
that expensive reasoning (Opus, high/xhigh thinking) is spent only where it changes output
quality, and high-volume mechanical work runs on Sonnet. Invoked as `/codeops:setup-routing` or
the typeable alias `/setup-routing`.

## The two-layer principle (preserve this throughout)

Routing has **two layers**, and they must stay coordinated:

1. **Policy layer (soft, behavioral).** A block in the project's `AGENTS.md` decides *which
   model* each phase runs on — inline-first — and which pinned executor backs a dispatch when
   one is warranted, expressed as a rule over task tags.
2. **Enforcement layer (hard, guaranteed).** Each executor subagent's frontmatter pins both
   `model:` (which model runs) and `effort:` (which reasoning effort runs) when that executor is
   invoked. Codex enforces both, overriding the user's session/`settings.json`/env config —
   so routing works *regardless of what the user has already configured*. The sole exception is the
   `CLAUDE_CODE_SUBAGENT_MODEL` env var, which sits above subagent frontmatter and forces every
   subagent onto one model (a deliberate global cost-cap escape hatch — surface it in Phase 5).

> The policy is only trustworthy because the pinned executors exist to back it. Since v3.2.0 the
> two executors (`plan-task-executor`, `plan-task-executor-opus`) **ship with the plugin** in its
> `agents/` directory — every install has them, so the policy block is valid on its own. **Never
> generate routing prose that references an executor that exists neither in the plugin nor in the
> project.** Per-project copies under `.codex/agents/` are an **opt-in override** for users who
> want customized executor prompts (a project agent of the same name shadows the plugin one).

> The policy layer is a *behavioral instruction to the orchestrator*, not a hard guarantee. The
> `exec-plan` skill's "Execution mode — inline first" protocol (execution-protocol.md) defines
> when a phase may be dispatched at all, the phase packet, the parent/executor division of
> labor, and a missing-executor guard (inline fallback with notice). Watching one real phase run
> under the policy is still the recommended validation (Phase 5).

## Project configuration

For build/test/verify commands, package manager, structure, and conventions, read **the project's
AGENTS.md** (or detect from manifests if none). This skill *adds to* that AGENTS.md; it never
rewrites the user's own sections. It reuses the non-destructive merge discipline of
`analyze_project`, tightened with explicit sentinels for idempotency.

## Hard rules

- **Independent analysis, not blind trust.** Classify the project from the *repository*, using the
  user's description only as a hint. State the evidence behind the classification.
- **Hard confirmation gate.** Never write anything until the user explicitly approves (Phase 3).
- **Non-destructive & idempotent.** Re-running must be safe: update the sentinel block in place,
  never duplicate it; write executor overrides only when the user opts in AND the file is absent;
  never overwrite a user's existing file.
- **Operate on the current project only.** Touch the project's `AGENTS.md` (and `.codex/agents/`
  only for opted-in overrides). **Never edit `~/.codex/AGENTS.md` or any global user file.**
- **Integration-branch write (parallel agents).** The routing block is a repo-wide `AGENTS.md`
  write, so it belongs on the **integration branch**. Resolve it the way `analyze_project` does —
  the `integrationBranch` marker key, else `origin/HEAD`, else `main`/`master`; if `git` is
  unavailable, treat the current branch as integration. On a **non-integration** (feature) branch,
  **warn and skip** the write and tell the user to run `setup-routing` on the integration branch —
  don't stage or fork the block. It's a once-per-repo idempotent write that only needs to happen
  there, so concurrent feature worktrees never collide on the routing block.
- **Concise generated output.** The routing block is injected into every session; keep it tight.
- **Grounded options & recommendations.** When you present the profile, the proposal, or any
  adjustment choice, follow the always-on Grounded Options directive in the coding standards:
  present only viable options, second-guess each, ground claims in the real repo, and lead with a
  recommendation and its reason. You recommend; the user decides. For consequential
  recommendations also apply the recommendation-hardening protocol
  (`_shared/recommendation-hardening.md`).

---

## Sensitivity profiles

Detect the project type and map it to a profile. The set is extensible — add profiles by giving
each a trigger set, detection hints, and a default-tag + escalation rule.

### Profile A — "Opus-dominant" (high reasoning sensitivity)
- **Triggers:** compiler, interpreter, programming-language implementation, type system, semantic
  analysis, code generation, optimizer, formal verification, or similar.
- **Detection hints:** `lexer`/`parser`/`ast`/`ir`/`codegen` directories or files; grammar files
  (`.g4`, `.pest`, custom); heavy use of a systems language; a description mentioning "compiler",
  "language", "type checker", "IR", "codegen".
- **Default tag:** untagged → `complex` (Opus). **De-escalate** only explicitly mechanical tasks
  (lexer tables, AST-node boilerplate, test fixtures, mechanical refactors) → `trivial` (Sonnet).
- `preflight` always Opus.

### Profile B — "Mixed core/scaffold" (split sensitivity)
- **Triggers:** a DSL or query language that lowers/compiles to another target (e.g. SQL); ORMs
  with non-trivial query generation; any *semantic translation core* surrounded by *mechanical
  scaffolding*.
- **Detection hints:** description mentioning "DSL", "lowering", "transpile", "query builder",
  "compiles to SQL"; a translation/lowering layer plus a parser/CLI surface.
- **Default tag:** untagged → `standard`, but **all lowering/translation tasks and anything
  touching target-language semantics → `sensitive` (Opus).** Frontend plumbing, error formatting,
  CLI wiring, scaffolding, fixtures → `trivial`/`standard` (Sonnet).
- `preflight` always Opus, with explicit emphasis on **semantic-correctness review** — silent
  wrong-output is the failure mode.

### Profile C — "Sonnet-default" (low reasoning sensitivity)
- **Triggers:** conventional web/app development — React, Vue, Node, REST/GraphQL APIs, CRUD,
  standard backend services.
- **Detection hints:** `package.json` with react/next/express/fastify/nest; component directories;
  typical web-app layout.
- **Default tag:** untagged → `standard` (Sonnet). **Escalate** only tasks tagged
  security-sensitive, concurrency-sensitive, or performance-critical → `sensitive` (Opus).

### Fallback — "Balanced"
If detection is ambiguous, use a balanced profile: untagged → `standard` (Sonnet), escalate
`complex`/`sensitive` → Opus. **Tell the user this was a fallback** and invite them to correct the
classification before confirming.

## Task-tag vocabulary

Routing is **tag-driven**, not a blanket per-project switch (Profiles A and B are internally
mixed). The vocabulary is fixed: `trivial`, `standard`, `complex`, `sensitive`. Each profile sets
only the **default tag** for untagged tasks and the **escalation/de-escalation** it applies. The
routing rule is constant — `trivial`/`standard` → Sonnet; `complex`/`sensitive` → Opus — applied
inline-first: run each phase inline on the model its tag calls for, and dispatch a phase to the
matching pinned executor only when a cheaper model than the session's is warranted (see the
exec-plan skill's inline-first mode).

The generated routing block also instructs `make-plan`/`exec-plan` (within this project) to **tag
each task** with one of these levels, so routing becomes a mechanical rule rather than a per-task
judgment call. This is written into the project AGENTS.md routing block — the skill does **not**
modify the global `make-plan` skill.

---

## The interaction flow

### Phase 1 — Analyze (read-only)
Read the repo: manifests (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `Makefile`,
build files), directory structure, key files, grammar/IR/codegen markers, framework signals, and
any existing `AGENTS.md`. Combine the evidence with the user's one-line description.

### Phase 2 — Classify & propose
Pick a profile and **state the evidence** ("I see `parser/`, `ir/`, and `codegen.rs` — classifying
as Opus-dominant"). Then present, in full and exactly as it will be written:
- the chosen profile and its default tag + escalation rule;
- the complete routing block (from [templates.md](templates.md), filled in);
- the complete **quality-profile block** (templates.md section 4; canonical semantics in
  `_shared/quality-profile.md`) — lens add-ons, `security_profile`, and `perf_critical` inferred
  from the same repo evidence under the same independent-analysis rule: propose from what the
  code shows, never from the user's description alone;
- a note that the referenced executors ship with the plugin, plus the OPTIONAL override: offer to
  copy them into `.codex/agents/` for per-project prompt customization.

### Phase 3 — Confirmation gate (HARD STOP)
Ask the user to **confirm**, **adjust** (override the profile, individual tag mappings, or any
quality-block value), or **cancel**. ONE gate covers both blocks — routing and quality. Do not
write anything until explicit approval. Honor adjustments before writing.

### Phase 4 — Write
Apply the writes from [templates.md](templates.md):
1. **Routing block.** Apply the sentinel merge to the project `AGENTS.md` (replace between
   markers / append / refuse-on-corruption — see templates.md). The executors it references
   ship with the plugin; nothing else to write.
2. **Quality-profile block.** Apply the identical sentinel merge for the
   `<!-- CODEOPS-QUALITY -->` markers (templates.md section 4) — a separate managed region;
   each write touches only its own block.
3. **Generated agent overrides.** Whenever a quality block exists, run
   `"${PLUGIN_ROOT}/scripts/codeops-agents-sync.sh"` from the project root — **always**,
   not only when `agent_models` carries an `effort`. It writes the `.codex/agents/` files the
   effort overrides need (plugin body verbatim, frontmatter rewritten, marker-stamped) **and
   prunes generated files a withdrawn override left behind** — so skipping the run when the map
   has no effort is exactly the case that would strand a dead pin in force. It is a no-op when
   there is nothing to do. **Never hand-write an agent file to change a model or an effort**;
   report the engine's output verbatim rather than paraphrasing what it did.
   If it reports `SKIPPED`, say so prominently: a hand-authored agent of that name shadows the
   plugin's, so the profile's override for it **is not in effect** until the user removes the
   file. Never delete it for them.
4. **Customized prompt bodies (ONLY if the user opted in at Phase 3).** Copy the plugin's agent
   files into `.codex/agents/` for prompt customization — each only if absent; on a name
   collision, **report and skip**, or offer a suffixed name — never overwrite a user's file.
Never touch content outside the managed blocks or pre-existing agent files.

### Phase 5 — Verify & report
Summarize exactly what was written and where. Tell the user how to confirm:
- run `/agents` to see the executors (plugin-shipped, plus any project overrides — a project
  agent of the same name shadows the plugin one);
- inspect the `<!-- CODEOPS-ROUTING -->` **and** `<!-- CODEOPS-QUALITY -->` blocks in `AGENTS.md`;
- re-run `"${PLUGIN_ROOT}/scripts/codeops-agents-sync.sh" --check` any time (exit 1 means a generated agent is
  missing or stale against the installed plugin) — the check to reach for after a plugin upgrade;
- (recommended) run one `exec-plan` task and confirm the Sonnet executor is actually selected.

**Quality-block consumer note:** the quality loop activates on the next `exec-plan` run
(activation rules in `_shared/quality-profile.md`), and a quality agent whose pinned model is
unavailable on the user's account (for example, absent from an org allowlist) **silently runs on
the session model** — mention it so surprising review quality is traceable.

**Flag the real-world validation explicitly:** whether their Codex version honors
delegation-by-name reliably, and that they should watch their **rework rate** for a week before
trusting Sonnet on borderline tasks. Also confirm the generated `model:`/`effort:` shorthand is
valid for their installed Codex version (see templates.md). If any generated agents were
written, say that they are regenerated — not hand-maintained — so a plugin upgrade reaches them via
`codeops-agents-sync.sh` rather than being silently missed. Note that the pinned `model:` and
`effort:` win over any model/effort they already set in `settings.json` or env — **except** if they
have set `CLAUDE_CODE_SUBAGENT_MODEL`, which overrides every subagent's pinned model.

---

## Related skills

- **exec-plan skill** — consumes the routing block via its "Delegated Execution" protocol
  (handoff packet, parent-owns-plan-file, blocker path, missing-executor inline fallback).
- **make-plan skill** — the routing block asks it to tag each generated task `trivial`/`standard`/
  `complex`/`sensitive` within this project.
- **preflight skill** — always Opus under every profile (and semantic-correctness-focused under B).
- **analyze_project command** — the non-destructive AGENTS.md merge discipline this skill reuses.
- For coding, testing, and git standards, follow **your project's AGENTS.md** and use **/gitcm** /
  **/gitcmp** for commits.
