---
name: exec-plan
description: >-
  Executes an implementation plan created by the make-plan skill. Use when the user says
  "exec-plan", "run the plan", "execute the plan", "implement the named feature plan",
  or "continue the plan for a feature". Accepts a feature name and an optional commit-mode
  flag: --ask-commit (default, ask after each verified task), --no-commit (never commit),
  or --auto-commit (commit + push after each verified task). Reads the feature's execution plan,
  finds the next incomplete task, and runs the per-task loop (implement, update the execution
  plan immediately, verify, then commit per mode) following specification-first task ordering.
  Under the repo's CodeOps quality policy, a risk-derived quality loop
  reviews each executed phase (reviewer + auditor agents); critical/major findings pause for a
  user ruling in every commit mode.
---

# exec-plan — Execute an Implementation Plan

> **CodeOps Artifact Schema**: 1

Execute the implementation plan at `plans/$ARGUMENTS/99-execution-plan.md`. The first
argument is the feature name; an optional flag selects the commit mode.

## Execution-entry gate

When CodeOps traceability exists, run the readiness check before modifying implementation files:

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness --root . --feature <feature>
```

Use the exact `feature` value from the selected feature's `traceability.json`; never guess from a
directory name. Do not execute while the selected feature reports a blocker. During execution,
keep task, implementation, and verification nodes synchronized with the Markdown plan's `[ ]` →
`[~]` → `[x]` transitions.

A runtime ambiguity invalidates the selected feature's readiness: record it and mark affected
links stale. If resolution requires changing an upstream artifact outside the selected plan's
documents, present the exact expanded modification set and obtain the user's approval before
editing. Resolve the ambiguity, rerun feature-scoped readiness, and only then resume.

This skill covers **execution only**. To create a plan, use the make-plan skill.

## Resolve the plan path first (layout-aware)

Determine the layout via **[../../_shared/layout-convention.md](../../_shared/layout-convention.md)**:

- **Flat layout** (no marker): the plan is at `plans/$ARGUMENTS/99-execution-plan.md` — as flat layout always has.
- **Nested layout** (marker present): the plan is under a feature —
  `codeops/features/<f>/plans/<plan>/99-execution-plan.md`. If the target feature/plan is ambiguous,
  **ask the user** (never guess). A non-trivial **task** mini-plan lives at the same nested path and
  executes identically (see "Lightweight tasks" above). Everywhere below that says
  `plans/$ARGUMENTS/` means this resolved plan path.

## Commit modes

| Flag | Behavior |
|------|----------|
| *(none)* / `--ask-commit` | **Default.** After each verified task, ask the user whether to commit. |
| `--no-commit` | Never commit, never ask. Pure implementation. |
| `--auto-commit` | Automatically commit + push (via the `git-commit` skill in push mode) after each verified task. |

Full prompt wording, end-of-plan reminders, and commit-message format live in
[commit-modes.md](commit-modes.md) — read it before the first commit decision.

## Lightweight tasks (both layouts)

A **non-trivial task** has a single mini-plan at the resolved task path (flat:
`plans/<task-slug>/99-execution-plan.md`; nested:
`codeops/features/<f>/plans/<task-slug>/99-execution-plan.md`). Execute it **exactly like a feature
plan** — same per-task loop, same real-time update mandate, same commit modes — it is just a
smaller `99-execution-plan.md` (objective + checklist + verify, no `00–07` set). Specification-first
ordering still applies *when the task warrants tests* (e.g. a bugfix's regression test).

A **trivial task** has **no plan document** to run: do the work directly, then record it as a
`T-NN` roadmap row + the commit (no execution-plan loop). The task model and routing rule live in
**[../../_shared/layout-convention.md](../../_shared/layout-convention.md)** — the lane exists in both
layouts (flat gained it in 3.2.0).

## Execution mode — inline first

Phases run **inline** on the session model by default; a phase is dispatched as ONE pinned-model
executor only when its routing tag maps to a cheaper model AND the phase amortizes the executor
bootstrap. Per-task or parallel dispatch happens only on the user's explicit request (it costs
more tokens, not fewer). Full rules in [execution-protocol.md](execution-protocol.md).

## Execution protocol (summary)

Read [execution-protocol.md](execution-protocol.md) for the full step-by-step protocol,
the specification-first ordering rules, the real-time update mandate, and the session
summary template. The essentials:

### Step 1 — Load the plan

1. Read `plans/$ARGUMENTS/99-execution-plan.md`.
2. Find incomplete tasks — both `[ ]` and implemented-but-unverified `[~]`; read supporting specs
   in `plans/$ARGUMENTS/`.
3. Determine the starting point: a `[~]` task is resumed first (re-verify, then promote or keep
   fixing); otherwise the first `[ ]` task.
4. If the plan is missing/empty/already complete, **STOP** — see the load table in
   [execution-protocol.md](execution-protocol.md). Generally suggest the make-plan skill.

**Schema check:** schema 1 plans require valid traceability and readiness. A legacy
`CodeOps Skills Version` stamp or missing schema triggers a read-only upgrade assessment; ask
before migration or execution with recorded compatibility risk. Never silently upgrade.

### Step 2 — Execute tasks (per-task loop)

For each task, in order:

1. **Implement** the task following the technical specs in `plans/$ARGUMENTS/`.
2. **🚨 Immediately update `99-execution-plan.md`** — completion marks are **two-stage**: mark the
   task `[~]` with an implemented-timestamp in its phase task list (or, in a pre-3.3.0 plan, in
   the Master Progress Checklist — see the protocol's dual-format detection) and bump the Progress
   counter / Last Updated stamp as soon as implementation finishes (crash-safe), promote it to
   `[x]` only after its verification passes. A task never shows `[x]` with a failing verify.
3. **Verify** — run your project's verify command (from the project's AGENTS.md, or detected
   project conventions), output captured per the protocol's **Verify-output capture rule**
   (PASS one-liner; on failure the last 50 log lines + log path). Pass → promote `[~]` → `[x]`;
   fail → fix and re-verify (mark stays `[~]`).
4. **Commit** per the active commit mode (see [commit-modes.md](commit-modes.md)) — the commit
   gate keys off `[x]`.
5. **Techdocs check (after each phase):** if the phase introduced architectural changes and
   techdocs exist, do an incremental update via the techdocs skill.
6. Continue until all tasks are complete. (Codex auto-compacts context — no manual
   threshold handling is needed.)

> **🚨 Specification-first task ordering — non-negotiable.** Within each feature:
> `spec tests → verify red → implement → verify green → impl tests → full verify`.
> Never write implementation code before its spec tests exist, and never edit a spec test to
> match the implementation (the implementation is wrong, not the test). Details and the
> compressed single-session form are in [execution-protocol.md](execution-protocol.md).

> **🚨 Zero-ambiguity during execution.** If you hit any detail not covered by the plan docs or
> `00-ambiguity-register.md`, STOP, present options to the user, wait for an explicit decision,
> record it in `00-ambiguity-register.md` (tag `(runtime)`), then resume. Never guess.

> **Grounded Options & Recommendations (coding standards → Working style) apply here.** Before presenting options/findings/recommendations: filter out non-viable ones (no strawmen; ≥2 only when ≥2 are genuinely viable, else present the single viable path and name what was rejected), second-guess each, verify any code-modifying option against the actual current code (cite `file:line`), and lead with a recommendation backed by grounded reasoning. Match ceremony to stakes — the user decides. Apply the recommendation-hardening protocol (`_shared/recommendation-hardening.md`) to consequential recommendations; escalate to an independent challenger only when the decision is genuinely high-stakes.

### Step 3 — Session wrap-up

1. Finish the current task before stopping.
2. **🚨 First, update `99-execution-plan.md`** with all completed tasks (before anything else).
3. Run the verify command.
4. Handle the commit per the active commit mode.
5. Report a session summary (must state `Execution Plan Updated: ✅`). Template in
   [execution-protocol.md](execution-protocol.md).

To resume in a later session, just run `/exec-plan $ARGUMENTS` again — the execution plan is the
source of truth and tells the skill where to pick up.

## Quality loop (profile-gated)

Every non-trivial executed phase (and task mini-plan) ends with a post-phase quality review under
strict defaults unless an allowed adaptive-mode policy explicitly disables it. Activation rules,
lenses, supersession, dispatch packets, and budget caps are defined
once in **[../../_shared/quality-profile.md](../../_shared/quality-profile.md)** — this skill
links to them, never restates them.

The flow: the protocol records a phase-start ref when the phase begins; after the phase's last
task verifies, the correctness reviewer and any active auditors are dispatched **in parallel** on
the phase diff, their findings are merged and presented in severity-grouped batches, and each
ruling is recorded in durable finding and traceability artifacts.

> **🚨 Finding gate (load-bearing).** 🔴 CRITICAL and 🟠 MAJOR findings PAUSE execution for the
> user's ruling in ALL commit modes — auto-commit never bypasses the pause. 🟡 MINOR findings are
> report-only. Accepted fixes are implemented, verified, follow-up-committed per the commit mode,
> and (after 🔴/🟠 fixes) re-reviewed ONCE on the fix diff — never a third time.

Step-by-step mechanics — the phase-start ref, spec-author dispatch, the post-phase quality step,
and emission points — live in [execution-protocol.md](execution-protocol.md).

## Roadmap sync

If a roadmap exists (`plans/00-roadmap.md` flat, or the feature's
`codeops/features/<f>/00-roadmap.md` nested), keep it in sync via the roadmap skill (update-first,
before verify/commit/next): set the RD/task row to `Executing` (🔄) on start, `Done` (✅) on
completion, and `Blocked` (⛔) with a nested `↳ DEF-n` sub-row when a blocking dependency is
discovered. **Nested layout:** after each per-feature transition, **cascade** to the portfolio
`codeops/00-roadmap.md` (re-roll that feature's row) before proceeding — per the roadmap skill's
cascade mandate. If no roadmap exists, these hooks are inert.

## Error handling

Brief rules for verification failure, plan deviation, and mid-task interruption are in
[execution-protocol.md](execution-protocol.md) — consult it when something goes wrong.

## Post-completion hooks (all tasks done)

1. Handle the end-of-plan commit per the active commit mode (see [commit-modes.md](commit-modes.md)).
2. **Techdocs:** if techdocs exist, do a comprehensive update via the techdocs skill; otherwise
   ask whether to create them.
3. **Re-analyze:** ask whether to re-analyze the project and update the project's AGENTS.md via
   the `analyze-project` skill.
4. **Roadmap:** set the RD row to `Done` via the roadmap skill if a roadmap exists.

## Conventions

- Follow your project's coding and testing standards (the project's AGENTS.md, or detected
  project conventions). If no AGENTS.md exists, detect build/test/verify commands from manifest
  files and use only facts you can read — do not invent settings.
- Commit using the `git-commit` skill (commit only) or the `git-commit` skill in push mode (commit + push), or a normal git commit.
- Related skills: make-plan (creation), upgrade-plan (outdated plans), preflight, roadmap, techdocs.
