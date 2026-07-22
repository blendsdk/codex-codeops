# setup-routing — templates & write contracts

Read this before writing anything in Phase 4. It holds the exact artifacts the skill emits:
the two executor subagents, the sentinel routing block, and the merge rules. Fill the
`<PLACEHOLDERS>` from the chosen profile before presenting (Phase 2) and writing (Phase 4).

---

## 1. Executor subagents (plugin-shipped; per-project override is opt-in)

Since v3.2.0 both executors ship with the plugin in its `agents/` directory
(`agents/plan-task-executor.md`, `agents/plan-task-executor-opus.md`) — the routing block works
on every install with NO per-project agent writes.

**Do not hand-copy an agent file to change its model or effort.** Since v3.12.0 that is what
`agent_models` is for: a model override applies at dispatch time, and an effort override is
materialized by `"${PLUGIN_ROOT}/scripts/codeops-agents-sync.sh"`, which copies the plugin's body byte-for-byte and
rewrites only the frontmatter. A hand copy is a permanent silent fork — it freezes the prompt at
today's release and never receives another improvement. See `../../_shared/quality-profile.md`.

Write a hand-authored copy into the TARGET project's `.codex/agents/` ONLY when the user wants a
**customized prompt body** and opted in at Phase 3 (a project agent of the same name shadows the
plugin one). Start from the plugin file's current content, create each only if it does not already
exist, and never overwrite a user's file of the same name — report the collision and skip, or offer
a suffixed name. Such a file carries no `CODEOPS-GENERATED` marker, so the sync engine leaves it
alone permanently.

> **`model:` field syntax.** These templates use the `sonnet` / `opus` shorthand (also valid:
> `haiku`, `fable`, `inherit`, or a full model id). Confirm the shorthand is valid for the user's
> installed Codex version; if their version requires explicit model strings, substitute those
> and note it in the Phase 5 summary. When uncertain, emit the shorthand and ask the user to
> confirm — do not silently guess.
>
> **Both `model:` and `effort:` are pinned — by design.** A subagent's frontmatter `model:`
> overrides the session model, `settings.json` `"model"`, and `ANTHROPIC_MODEL`; its `effort:`
> overrides the session effort level *while that subagent is active*. So routing works **regardless
> of what model or effort the user has already configured** in their CC config. Pinning effort is
> what makes the Sonnet executor actually run cheap even if the user's session effort is high/xhigh.
> Effort levels: `low | medium | high | xhigh | max` (available levels depend on the model — Sonnet
> does not expose `xhigh`). The policy reserves `xhigh`/`max` for planning skills, so the **shipped**
> executors cap at `high`; a repo that genuinely needs more raises it per-repo through
> `agent_models`, which is a deployment choice rather than a change to what the plugin ships.
>
> **The one override that beats these pins:** the `CLAUDE_CODE_SUBAGENT_MODEL` env var sits *above*
> subagent frontmatter in the precedence order, so a user who sets it forces every subagent onto
> that model. That is a deliberate global cost-cap escape hatch, not a bug — mention it in the
> Phase 5 summary so the user knows their pins are honored unless they have set it.

### Override sources

The override starting-point content is NOT duplicated here (it would drift): read the plugin's
`agents/plan-task-executor.md` (Sonnet, effort medium) and `agents/plan-task-executor-opus.md`
(Opus, effort high) and copy their current content verbatim, then customize. Both carry the
phase-packet contract, the spec-test blocker rule, and the never-guess/never-edit-the-plan
rules — keep those in any customization.

---

## 2. The AGENTS.md routing block

Write it between the sentinels so re-running updates it in place. Keep it tight — it rides into
every session's context, so the sentinel span stays **≤10 lines** (each directive on one dense
line). Fill `<PROFILE NAME>`, `<DEFAULT TAG>`, and the profile-specific override line; drop the
override line if the profile has none.

```markdown
<!-- CODEOPS-ROUTING:START -->
## Model & effort routing (<PROFILE NAME>)
- Tag each task trivial|standard|complex|sensitive (default <DEFAULT TAG>) in make-plan.
- exec-plan runs phases inline on the tagged model; dispatch one pinned executor only when a cheaper model than the session's is warranted — trivial/standard→Sonnet (plan-task-executor), complex/sensitive→Opus (plan-task-executor-opus).
- <PROFILE-SPECIFIC OVERRIDE LINE>
- Reserve Opus + high/xhigh for make-plan, grill-me, preflight. /compact after each phase; /clear on project switch.
<!-- CODEOPS-ROUTING:END -->
```

### Profile-specific override line (pick the matching one)

- **A — Opus-dominant:** `Default complex; de-escalate only mechanical tasks (lexer tables, AST boilerplate, fixtures, mechanical refactors) to trivial. preflight always Opus.`
- **B — Mixed core/scaffold:** `All lowering/translation and target-language-semantics tasks are sensitive (Opus); CLI/error-formatting/scaffolding/fixtures are trivial/standard (Sonnet). preflight always Opus, focused on semantic correctness.`
- **C — Sonnet-default:** `Escalate to sensitive (Opus) only for security-, concurrency-, or performance-critical tasks.`
- **Balanced (fallback):** `Fallback classification — escalate complex/sensitive to Opus; confirm or correct the profile if this is wrong.`

---

## 3. Sentinel-merge rules (AGENTS.md)

The markers are exactly `<!-- CODEOPS-ROUTING:START -->` and `<!-- CODEOPS-ROUTING:END -->`.

- **Both markers present:** replace only the content between them; leave everything else byte-for-byte.
- **Neither marker present:** append the block at the end of `AGENTS.md` (create the file if the
  project has none), separated by a blank line.
- **Exactly one marker present (corrupted state):** do **not** guess. Report it and ask the user
  how to proceed.

Never disturb user-authored or `analyze_project`-authored sections. The managed blocks are the
only regions this skill owns.

---

## 4. The AGENTS.md quality-profile block

The canonical definition — fields, enums, defaults, activation, supersession — is
**`_shared/quality-profile.md`**; this template is only the write shape. Every key is optional
with meaningful defaults, so propose concrete values only where the repo evidence supports them.

```markdown
## Quality profile (CodeOps)
<!-- CODEOPS-QUALITY:START -->
lenses: [<ADD-ON LENSES>]
security_profile: [<SECURITY PROFILES>]
perf_critical: <true|false>
review_hook: on
telemetry: on
agent_models: <AGENT OVERRIDES, or {} >
<!-- CODEOPS-QUALITY:END -->
```

`agent_models` carries per-repo model **and** effort overrides — `{name: model}`,
`{name: {effort: E}}`, or `{name: {model: M, effort: E}}` (canonical forms and resolution order in
`_shared/quality-profile.md`). Default to `{}`: propose an entry only where the repo evidence
justifies it, and say which evidence. Any entry carrying `effort` is materialized as a generated
file by `"${PLUGIN_ROOT}/scripts/codeops-agents-sync.sh"` in Phase 4 — never write that file by hand.

Evidence → proposal hints: web request handlers → `owasp-web`; auth/session/token code →
`auth-protocol`; payment or ledger flows → `financial-integrity`; a multi-tenant schema →
`tenant-isolation`; MCP or agent integrations → `mcp-agent`; measured hot paths or latency
targets → `perf_critical: true`; concurrency-heavy code → the `concurrency` lens; a public
SDK surface → `api-surface`. `standards` is base-only — never propose it as an add-on.

**Merge rules:** identical to section 3, applied to the markers
`<!-- CODEOPS-QUALITY:START -->` / `<!-- CODEOPS-QUALITY:END -->` — replace between markers,
append when absent, refuse and ask on a corrupted single-marker state. The quality block and
the routing block are separate managed regions; each write touches only its own.
