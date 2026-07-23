---
name: make-requirements
description: >-
  Gather and document requirements, turn an idea into formal requirement
  documents (RDs). Use for "make-requirements" (full discovery: brain dump or
  bare idea into a structured requirements/ set), "add_requirement" (add one new
  RD to an existing set), and "review_requirements" (health check / gap analysis
  on an existing set). Trigger when the user wants to capture, expand, structure,
  or audit what a system must do before building it — e.g. "help me spec out my
  app", "document requirements", "what features am I missing", "add a feature to
  the requirements", "review my requirements for gaps". Acts as a proactive
  domain consultant: absorbs the seed idea, expands it with comparable-system
  features, challenges it with edge cases, then decomposes it into numbered RDs
  behind a hard Zero-Ambiguity Gate.
---

# Requirements Gathering & Documentation

> **CodeOps Artifact Schema**: 1

Transform a rough project idea into a structured, complete set of formal
**requirement documents (RDs)**. This skill is upstream of, and independent
from, the make-plan skill — neither requires the other.

## Codex traceability contract

For every accepted requirement and material ambiguity, maintain the feature's `traceability.json` according to [../../references/artifacts/traceability.md](../../references/artifacts/traceability.md). Requirements use stable `RD-*` identifiers; ambiguities and decisions use stable `AR-*` identifiers. Link each resolved ambiguity to every requirement or specification it affects. Before declaring requirements complete, run:

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness --root . \
  --gate requirements --target <target>
```

Resolve `<target>` from the graph (an RD, or an explicitly selected requirement-set/group);
never infer it from a directory or widen it to sibling RDs. Closure is read context, not an
authorized modification set. The requirements gate remains closed while a material ambiguity is
open, a requirement is not approved, a referenced artifact is missing, or the traceability graph
is broken. The script validates structure; this skill remains responsible for semantic completeness.
Advance a draft target only with the exact compare-and-swap request defined in the traceability
reference and `transition --request <request.json>` using gate `requirements`.

## Core Principle: Proactive Domain Consultant

Before discovery, read [../../references/domains/selection.md](../../references/domains/selection.md), select every applicable system lens, and read those lens files completely. Record selected lenses and evidence in the requirements index. Re-evaluate selection when discovery reveals another domain; a financial web service, for example, requires financial, web, distributed/concurrent, and data/migration lenses.

You are NOT a passive interviewer. You are a **domain-aware consultant** that:

1. **Absorbs** — takes whatever the user provides (brain dump, bullets, vague idea) as seed material
2. **Expands** — draws on knowledge of comparable systems to suggest features the user hasn't considered
3. **Challenges** — asks "what happens when..." to expose edge cases and hidden requirements
4. **Structures** — decomposes the expanded scope into formal, numbered RDs
5. **Validates** — cross-references all documents for gaps, inconsistencies, and missing concerns

The user's input is NEVER the final requirements. The value of this skill is in
**making incomplete ideas complete**.

> **Grounded Options & Recommendations (coding standards → Working style) apply here.** Before presenting options/findings/recommendations: filter out non-viable ones (no strawmen; ≥2 only when ≥2 are genuinely viable, else present the single viable path and name what was rejected), second-guess each, verify any code-modifying option against the actual current code (cite `file:line`), and lead with a recommendation backed by grounded reasoning. Match ceremony to stakes — the user decides. **Recommendation hardening:** apply `_shared/recommendation-hardening.md` — for **high-stakes** Phase 2B gate decisions (complex/sensitive-tagged) spawn one independent challenger and reconcile *before* presenting; for all consequential decisions run the in-context layers and close with the `Confidence:` / `Hardening:` disclosure.

---

## Resolve paths first (layout-aware)

Determine the layout via **[../../_shared/layout-convention.md](../../_shared/layout-convention.md)** before writing anything:

- **Flat layout** (no `codeops/.codeops.yml`): RDs live in `requirements/RD-NN-*.md` with a single
  repo-wide RD sequence — exactly as flat layout always has.
- **Nested layout** (marker present): RDs live in `codeops/features/<f>/requirements/RD-NN-*.md`.
  **Ask/confirm the target feature** before drafting (create the feature folder **lazily** if new
  — never guess the feature). **RD ids reset per feature** (`billing/RD-01` and `auth/RD-01` are
  both valid and independent), and any cross-feature reference is **feature-qualified**
  (`billing/RD-01`). Everywhere below that says `requirements/` means the feature's requirements dir.

## Route first: is this a feature or a task?

Requirements (RDs) are for **features** — new cohesive capabilities. Ad-hoc work (a bugfix,
chore, or small change) is **not** a feature: it is a lightweight **task**, tracked with a
roadmap row (trivial) or a single mini-plan (non-trivial) — **no RD, no discovery, no
Zero-Ambiguity Gate**. The lane exists in **both layouts** (flat gained it in 3.2.0). If the
user's request is really a small fix, route them to the task lane (a roadmap row + `make-plan`
for a non-trivial mini-plan) instead of drafting an RD. If it is genuinely unclear, ask — never
default to the heavy pipeline silently. The task model and routing rule live in
**[../../_shared/layout-convention.md](../../_shared/layout-convention.md)**.

## Step 0: Detect the Mode

Read the user's phrasing and arguments, then branch:

| Signal | Mode | Go to |
|--------|------|-------|
| "make-requirements", "spec out", "document requirements", a brain dump, a bare idea, or nothing but the trigger | **Full Discovery** | Phases 1–4 below |
| "add_requirement", "add a feature/RD", "I also need …" AND a `requirements/` set already exists | **Add One RD** | the `review-and-add.md` reference |
| "review_requirements", "check my requirements", "what's missing/inconsistent" AND a `requirements/` set exists | **Health Check** | the `review-and-add.md` reference |
| "make-requirements --continue" or "resume requirements" | **Resume** | Step 0a |

If a mode is ambiguous (e.g. a `requirements/` folder exists but the user gave a
fresh brain dump), ask the user which they want. Do not guess.

### Step 0a: Resume an interrupted session

If resuming: read `requirements/_draft/discovery-notes.md`, summarize where you
left off (confirmed scope, selected features, open questions, stakeholder map,
which phase/step is next), then continue from the next step.

### Add / Review modes

For **add_requirement** and **review_requirements**, read **`review-and-add.md`**
and follow the protocol there. Both reuse the gate and templates described below.

---

## Full Discovery Overview

A multi-turn conversation, never a one-shot. The flow:

```
discovery interview → comparable analysis → user journeys → edge cases →
  scope confirmation → glossary → decomposition → dependency graph →
  🚨 ZERO-AMBIGUITY GATE → RD authoring → validation → final output
```

| Phase | What happens | Reference file |
|-------|--------------|----------------|
| **1. Discovery & Domain Analysis** | Vision interview, stakeholder mapping, comparable-systems analysis, user journeys, edge cases, scope confirmation | **`discovery-phases.md`** |
| **2. Structuring** | Glossary, decompose into RDs, dependency graph, MVP-vs-full phasing, integration map | **`discovery-phases.md`** |
| **2B. Zero-Ambiguity Gate** | Hard, non-negotiable gate — compile the Ambiguity Register, resolve every item with the user | **`zero-ambiguity-gate.md`** |
| **3. Authoring** | Write README + RDs from templates; acceptance-criteria specificity; mandatory non-functional RD | **`templates.md`** |
| **4. Validation** | Cross-reference check, "Did You Consider…" checklist, final verification, roadmap sync, summary | this file (below) + `templates.md` |

### Trigger modes for input (Phase 1 entry)

- **Brain dump** (most common): user gives a rough description with the trigger. Take it as seed material, recognize it's incomplete, enter full discovery.
- **Bare trigger**: nothing but the trigger. Open with the broadest question: *"What do you want to build? Give me as much or as little as you have — a rough idea, some bullet points, a domain, or even just a problem you want to solve."*
- **Existing notes / reference**: user points at files (e.g. "I have notes in docs/project-ideas.md"). Read them, extract the seeds, enter discovery with richer starting material.

---

## The Zero-Ambiguity Rule (active from question one)

This rule applies to **every decision with semantic weight** — feature specs,
behavioral definitions, scope boundaries, edge-case handling, technical choices,
data models, naming, document organization. Behavior/scope/data/security
decisions ALWAYS gate; cosmetic choices with zero semantic impact are exempt
(per the shared gate's traceability exemptions), and low-stakes cosmetic items
may be batched. If you must choose between two or more semantically distinct
options, **the user decides**.

Every question MUST yield a concrete, specific, unambiguous answer. Do NOT accept
vague responses, fill gaps with your own assumptions, infer intent, or proceed
with "reasonable defaults" the user didn't explicitly choose. If an answer is
unclear, ask again with sharper options. If the user says "I'm not sure," lay out
the options with trade-offs and guide them — but the **decision must be theirs**.

Throughout discovery, compile the **Ambiguity Register**. It is formally enforced
at Phase 2B before any RD is written — see **`zero-ambiguity-gate.md`**. The
register is saved permanently at **`requirements/00-ambiguity-register.md`** and
every decision in every RD back-references its AR # entry.

When opt-in outcome metrics are enabled, record only the enumerated requirements result and
aggregate round/decision counts. Never store questions, decisions, names, paths, or content.

---

## Phase 4: Validation & Finalization

After all RDs are written:

### 4.1 Cross-Reference Validation

Check for:
- **Missing references** — RD-05 mentions "equipment booking" but RD-07 doesn't list the relationship
- **Orphaned features** — a feature is described but no RD owns it
- **Circular dependencies** — RD-03 → RD-05 → RD-03
- **Scope leaks** — a "Won't Have" in one RD contradicts a "Must Have" in another

### 4.2 "Did You Consider…" Checklist

Run through the commonly-forgotten-requirements checklist (audit logging, data
export, API versioning, rate limiting, empty states, accessibility, backup/DR,
i18n, GDPR/retention, soft vs hard delete, timezones, onboarding, and the
security items below). The full numbered table is in **`templates.md`**.

> **🚨 The security items are NON-NEGOTIABLE** and must be addressed in every
> project: server-side input validation & sanitization; injection prevention
> (SQL, XSS, command, path traversal); auth & authorization model; rate limiting
> on auth/public endpoints; secrets management; encryption at rest and in
> transit; infrastructure hardening; security testing. See your project's
> security coding standards (AGENTS.md) for the full standard.

### 4.2B Zero-Ambiguity Final Verification 🚨

- [ ] `00-ambiguity-register.md` exists and is saved to disk
- [ ] Every entry has Status = "✅ Resolved" with an explicit user decision
- [ ] Zero deferred items — every ambiguity has a concrete answer
- [ ] All RD decisions carry AR # back-references (only exceptions: universally obvious facts + zero-semantic-impact formatting)
- [ ] No RD contains AI-assumed defaults, inferred behaviors, or guessed specs
- [ ] The surface-during-authoring rule was followed (new ambiguities found while writing went through the register)
- [ ] The user reviewed and confirmed the complete register

### 4.3 Techdocs Update

- **If `docs/index.md` exists with `techdocs: true` frontmatter:** perform an incremental update — extract design decisions from the RDs, create ADRs for every technology/architecture choice affecting behavior, performance, or maintainability, and update architecture sections (see the techdocs skill).
- **If techdocs do NOT exist:** ask the user whether to create technical architecture documentation; if yes, run the techdocs skill using the fresh requirements as input.

### 4.4 Roadmap Sync (RD Drafted)

After each RD is authored (and again at the end of the set):
- **If `plans/00-roadmap.md` exists:** add or sync a row for each newly drafted RD at stage `RD Drafted` (✏️); update its `Stage`, `Status`, `Last Updated`, and the header `Progress` counter, following the update-first mandate.
- **If it does NOT exist:** ask the user whether to create a roadmap. Never auto-create it silently.

See the roadmap skill for the full Roadmap Keeper protocol and stage-transition map.

### 4.5 Final Output Summary

Present the complete set: location (`requirements/`), every document created with
a ✅, and a summary (total RDs, Must/Should/Out-of-scope counts, MVP vs full
product phases). Next step: *"To start implementing, pick an RD and run the
make-plan skill. Suggested order: RD-01 → RD-02 → …"*

---

## Session Management (long conversations)

Requirements gathering is long and multi-turn. RD documents and the Ambiguity
Register are **written to disk as they are completed** — never held only in
conversation memory, so they survive an interrupted session.

**Save progress and resume natively:**
- If the session is getting long or the user wants to pause, save all progress to `requirements/_draft/discovery-notes.md` (confirmed scope, selected features, open questions, stakeholder map, and which phase/step to resume from). Save any completed RDs to `requirements/` and any in-progress RD to `requirements/_draft/`.
- The user resumes later by saying "make-requirements --continue" (or "resume requirements"). On resume, read the draft notes and any existing RDs, summarize the state, and continue from the next step.

---

## Adapting to Project Type

Tailor discovery questions and comparable-systems analysis to the project type
(SaaS, internal tool, API/backend, library/SDK, CLI, mobile, e-commerce, CMS,
healthcare, education, fintech, …). The full mapping of project type →
comparable systems → key discovery focus is in **`discovery-phases.md`**.

## Related Skills

- the make-plan skill — how RDs feed into implementation plans (downstream)
- the grill-me skill — deep disambiguation before requirements gathering (grill-me → make-requirements)
- the techdocs skill — technical architecture documentation from design decisions
- the upgrade-plan skill — upgrading outdated requirements (upgrade_requirements)
- the roadmap skill — sync each newly drafted RD to stage `RD Drafted`
- Read the project's AGENTS.md (or detected project conventions) for project-specific constraints
