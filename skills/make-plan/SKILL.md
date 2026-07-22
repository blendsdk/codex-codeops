---
name: make-plan
description: >-
  Creates a detailed, multi-document implementation plan for a software feature or task before any code is written. Use when the user wants to "make a plan", types "make-plan", or asks to "plan this feature", "create an implementation plan", "plan out this work", or "write a spec/plan" for something to be built. Drives a mandatory clarifying-questions interview, a hard Zero-Ambiguity Gate, and produces a feature plan document set ending in a task-by-task execution plan. For EXECUTING an existing plan, use the exec-plan skill instead.
---

# Implementation Plan Creation (`make-plan`)

Create a detailed, multi-document implementation plan for a software feature or task. This skill covers plan **creation** only. To **execute** a finished plan, use the **exec-plan skill**.

## Codex readiness proof

Maintain the feature's typed requirement → specification/invariant → acceptance criterion → specification test → task chain in `traceability.json`; follow [../../references/artifacts/traceability.md](../../references/artifacts/traceability.md). A plan is not ready merely because its documents exist. Before presenting it as executable, run:

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness --root .
```

Resolve every structural or readiness blocker, then perform the semantic Zero-Ambiguity Gate. If plan work exposes an upstream defect, reopen and correct the owning requirement or specification and revalidate downstream artifacts rather than patching the task text alone.

> **CodeOps Skills Version**: 3.12.0

## What you produce

A folder `plans/<feature-name>/` containing:

```
plans/<feature-name>/
├── 00-ambiguity-register.md   # Zero-Ambiguity Gate register (audit trail)
├── 00-index.md                # Overview and navigation
├── 01-requirements.md         # Requirements and scope
├── 02-current-state.md        # Current implementation analysis
├── 03-XX-<component>.md       # Technical spec per component (one or more)
├── 07-testing-strategy.md     # Spec test cases + verification
└── 99-execution-plan.md       # Phases, sessions, task checklist
```

The full templates for every document live in **[templates.md](templates.md)** — read it before writing any plan document in Phase 2.

## Resolve paths first (layout-aware)

Determine the layout via **[../../_shared/layout-convention.md](../../_shared/layout-convention.md)** before creating the plan folder:

- **Flat layout** (no marker): the plan folder is `plans/<feature-name>/`; `00-index.md` declares `> **Implements**: RD-NN` — exactly as flat layout always has.
- **Nested layout** (marker present): the plan folder is `codeops/features/<f>/plans/<plan>/`. **Ask/confirm the target feature** first (create the feature folder lazily if new — never guess). `00-index.md` declares a **feature-qualified** `> **Implements**: <feature>/RD-NN`, and any `> **Source**` link points at the feature's own `requirements/` dir. Everywhere below that says `plans/<feature-name>/` means this nested plan path.

## Lightweight tasks (mini-plan path — both layouts)

Not every change is a feature. Ad-hoc work (a bugfix, chore, small change) is a **task** (`T-NN`), and a *non-trivial* task gets a **single mini-plan**, not the full multi-document set. When the work is a task (see the routing rule in **[../../_shared/layout-convention.md](../../_shared/layout-convention.md)**):

- Write **only** the mini-plan at the resolved task path (flat: `plans/<task-slug>/99-execution-plan.md`; nested: `codeops/features/<f>/plans/<task-slug>/99-execution-plan.md`) — an execution doc with an **Objective**, a short **task checklist**, and a **Verify** line. **No** `00–07` docs, **no** RD, **no** Zero-Ambiguity Gate.
- Stamp it `> **Type**: Task (lightweight) · **Feature**: <f> · **CodeOps Skills Version**: 3.12.0` and a `> **Progress**:` line (in flat layout drop the `**Feature**:` part).
- Specification-first ordering still applies *when the task warrants tests* (e.g. a bugfix gets a regression test first); a trivial doc/config tweak may not.
- A **trivial** task needs no plan at all — it is just a roadmap row + the commit (point the user to the roadmap skill, then do the work).

Mini-plan shape:

```markdown
# Task T-05: Debounce the search input

> **Type**: Task (lightweight) · **Feature**: search · **CodeOps Skills Version**: 3.12.0
> **Progress**: 0/3 tasks (0%)

## Objective
Debounce the search box to 300ms to cut redundant queries.

## Tasks
- [ ] T-05.1 Write a spec test: rapid keystrokes ⇒ one query after 300ms
- [ ] T-05.2 Implement the debounce; verify the test passes
- [ ] T-05.3 Full verify

**Verify**: [project verify command]
```

Everything below is the **full feature** pipeline; skip it for tasks.

## Project configuration

These rules are universal. For build/test/verify commands, package manager, structure, language conventions, and commit scope, read **the project's AGENTS.md (or detected project conventions)**. If there is no AGENTS.md, detect settings from manifest files (`package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `Makefile`, `docker-compose.yml`, `pom.xml`, `build.gradle`, `CMakeLists.txt`, `*.sln`, `*.csproj`). Use only facts you can read from those files — never invent settings.

## Hard rules for every generated plan

- **No raw git commands in plan documents.** Plans must not contain `git add/commit/push` or bash blocks running git. When a plan needs to commit, it references the **/gitcm** (commit) or **/gitcmp** (commit + push) command. Execution commit behavior is owned by the exec-plan skill.
- **Specification-first testing ordering is non-negotiable** (see Phase 2 and [templates.md](templates.md)): spec tests → red phase → implement → green phase → impl tests → verify.
- **Zero-Ambiguity Gate (Phase 1C) must pass before ANY plan document is written.** No exceptions.

## Optional input: requirements documents

When a `requirements/` directory exists with `RD-XX-*.md` files (produced by the make-requirements skill), ask the user whether to base this plan on a specific RD. If they pick one, read it as primary input and shorten the Phase 1.1 interview (the RD answers most questions) — but still do Phase 1.2 current-state analysis and still run the Phase 1C gate. If they decline, run standard Phase 1. When a plan is based on an RD, `01-requirements.md` must include `> **Source**: [RD-XX](../../requirements/RD-XX-feature-name.md)` (in nested layout the relative link resolves within the same feature, e.g. `../../requirements/RD-XX-*.md` under `codeops/features/<f>/`) and `00-index.md` must declare `> **Implements**: RD-NN` — **feature-qualified** (`> **Implements**: <feature>/RD-NN`) in nested layout (used by the roadmap skill).

---

## Phase 1 — Information Gathering (MANDATORY)

### 1.1 Ask clarifying questions

> **ZERO-AMBIGUITY RULE — active from the first question.** Applies to every decision with semantic weight: design, architecture, behavior, scope, edge cases, error messages, naming, file structure. Behavior/scope/data/security decisions ALWAYS gate; cosmetic choices with zero semantic impact are exempt (per the shared gate's traceability exemptions), and low-stakes cosmetic items may be batched. If there is more than one semantically distinct option, the **user decides** — never you. Demand concrete, specific answers. Do not fill gaps with assumptions, infer intent, or apply "reasonable defaults" unless the user explicitly chose them. If an answer is vague, ask again with sharper options. If the user is unsure, lay out options with trade-offs and guide them — but the decision is theirs.

Cover at minimum: **Feature scope** (what it does / does NOT do, boundaries), **Technical context** (affected code, existing patterns, constraints), **Dependencies** (prerequisites, external deps), and **Success criteria** (definition of done, required tests, required docs).

### 1.2 Analyze current implementation

Read relevant source files; identify affected components; find similar/reference patterns; note technical debt; review project docs and AGENTS.md. If `docs/index.md` exists with `techdocs: true` frontmatter, read the relevant architecture sections first (see the techdocs skill).

### 1.3 Confirm scope

Present a scope confirmation (feature, IN scope, OUT of scope, key decisions needed) and ask the user to confirm or adjust. While doing this, start compiling the **Ambiguity Register** — finalized and enforced in Phase 1C.

---

## Phase 1B — Pre-Implementation Re-evaluation

Before writing documents (and again before each execution phase), re-check: Completeness (all requirements + edge cases), Context/Reasoning (can you justify each phase?), Task Granularity (2–4h tasks, independently testable), Dependencies (documented, no cycles), Testing (every task has validation), Architecture (anything >700 lines? plan a split), Scope Boundaries, No Dead Code, and Security (every user-input path identified; injection/auth/authz/rate-limiting/data protection addressed). Re-evaluate when requirements change or new constraints surface.

---

## Phase 1C — Zero-Ambiguity Gate (NON-NEGOTIABLE HARD GATE)

**This gate MUST pass before ANY plan document is created. No exceptions, no overrides, no "good enough."** Plans built on ambiguity produce code the user did not ask for. Every item in every plan document must trace to an explicit, user-confirmed decision.

The mechanism is the **Ambiguity Register** (`00-ambiguity-register.md`): a numbered inventory of every gap, ambiguity, unstated assumption, and open question, hunted systematically across all 12 categories. The full category checklist, register template, gate-enforcement rules, no-deferral policy, traceability requirement, surface-during-authoring rule, and interactions with the grill-me / upgrade-plan skills are in **[zero-ambiguity-gate.md](zero-ambiguity-gate.md)** — **read it now, before Phase 2.**

When opt-in outcome metrics are enabled, record only the enumerated planning result and aggregate
round/decision counts. Never store feature names, questions, decisions, or artifact content.

Gate opens ONLY when: every row Status = `✅ Resolved` with the user's explicit decision, the user has confirmed the complete register, zero items deferred, and the header reads `✅ GATE PASSED`. If zero ambiguities are found, still create the register file proving the review ran. You may recommend an option, but you may never decide for the user.

> **Grounded Options & Recommendations (coding standards → Working style) apply here.** Before presenting options/findings/recommendations: filter out non-viable ones (no strawmen; ≥2 only when ≥2 are genuinely viable, else present the single viable path and name what was rejected), second-guess each, verify any code-modifying option against the actual current code (cite `file:line`), and lead with a recommendation backed by grounded reasoning. Match ceremony to stakes — the user decides. **Recommendation hardening:** apply `_shared/recommendation-hardening.md` — for **high-stakes** Phase 1C gate decisions (complex/sensitive-tagged) spawn one independent challenger and reconcile *before* presenting; for all consequential decisions run the in-context layers and close with the `Confidence:` / `Hardening:` disclosure.

---

## Phase 2 — Create Plan Documents

1. Create the plan folder (`plans/<feature-name>/` flat, or `codeops/features/<f>/plans/<plan>/` nested — resolve via the convention doc).
2. Write each document using the templates in **[templates.md](templates.md)** — including its **Reference, don't restate** rule (one owning doc per fact; everything else cites ST-# / 03-doc § / AR-# with at most a one-line gloss). Stamp `00-index.md` and `99-execution-plan.md` with `> **CodeOps Skills Version**: 3.12.0`.
3. Every design decision, scope decision, and error-handling strategy must carry an `AR #` back-reference to the register (only exceptions: universally obvious facts and zero-semantic-impact formatting).
4. `07-testing-strategy.md` must contain concrete **Specification Test Cases (ST-*)** with input→expected-output pairs, each traced to a requirement / spec doc / AR entry. Expectations come from the SPEC, never from imagined implementation behavior.
4b. **Confirm the verify command once.** The command that fills every Verify line comes from the
   project's AGENTS.md or manifests — state what you detected and have the user confirm it (an AR
   entry like any decision). If nothing is detectable, ask — **never invent a command**.
5. `99-execution-plan.md` must structure every feature phase with the mandatory three-session ordering (Spec Tests → Implementation → Impl Tests & Hardening), carrying each phase's tasks as a **single checkbox list** — the plan's single source of truth for progress; a task line appears exactly once in the document. The full ordering rules are in [templates.md](templates.md).
6. If you discover a NEW ambiguity while writing, STOP immediately, add it to the register, get the user's decision, then resume (surface-during-authoring rule — see [zero-ambiguity-gate.md](zero-ambiguity-gate.md)).

Adapt component documents to the project type (Web App, API, Library, CLI, UI Components, Mobile, Compiler, Microservices, Infrastructure, Database, Bug Fix, Refactoring — the typical component breakdowns are listed in [templates.md](templates.md)).

---

## Phase 3 — Quality Checklist

Before finalizing, run the full quality checklist in **[quality-checklist.md](quality-checklist.md)** (Completeness, Granularity, Dependencies, Testing, Specification-First Testing, No Dead Code, Security-First, Zero-Ambiguity, Execution Plan Completeness, Format). The Specification-First, Security-First, Zero-Ambiguity, and Execution-Plan-Completeness blocks are NON-NEGOTIABLE.

---

## Phase 4 — Present Plan Summary

Report what was created:

```markdown
## Plan Created: [Feature Name]

**Location:** `plans/[feature-name]/`

**Documents Created:**
- 00-ambiguity-register.md ✅ (Zero-Ambiguity Gate — all items resolved)
- 00-index.md ✅
- 01-requirements.md ✅
- 02-current-state.md ✅
- [component docs] ✅
- 07-testing-strategy.md ✅
- 99-execution-plan.md ✅

**Summary:** Total Phases: X · Total Sessions: X · Estimated Time: X–X hours

**To begin implementation:** use the exec-plan skill on `[feature-name]`.
```

---

## Phase 5 — Roadmap Sync

After the plan is created, sync the roadmap if one is in play:

- **If `plans/00-roadmap.md` exists:** set the implemented RD's row to stage `Plan Created` (📋) and link the new plan. The link is deterministic — `00-index.md` declares `> **Implements**: RD-NN`, and the row is matched from that line. A plan with no declared RD is linked only when the user explicitly says which RD (or `DEF-n`) it belongs to. Update the roadmap BEFORE moving on.
- **If it does NOT exist:** ask the user whether to create a roadmap. Never auto-create it silently.

See the **roadmap skill** for the full Roadmap Keeper protocol.

---

## Related skills

- **exec-plan skill** — executes a finished plan (`99-execution-plan.md`), commit modes, real-time progress updates, post-completion re-analysis.
- **grill-me skill** — deep disambiguation before planning; its shared understanding feeds into the register as pre-resolved context but does NOT replace the Phase 1C gate.
- **make-requirements skill** — produces the `RD-XX-*.md` documents this skill can consume.
- **roadmap skill** — `make-plan` sets `Plan Created`; the roadmap tracks stages.
- **upgrade-plan skill** — upgrades outdated plans; the gate applies to new decisions only.
- **techdocs skill** — architecture docs read during Phase 1.2 and updated during execution.
- For coding, testing, and git standards, follow **your project's coding standards (AGENTS.md)** and use **/gitcm** / **/gitcmp** for commits.
