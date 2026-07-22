---
name: upgrade-plan
description: >-
  Upgrades an outdated plan or requirements set to current CodeOps standards. Use when the user
  says "upgrade-plan", "upgrade_requirements", "upgrade my plan", "upgrade my requirements",
  "bring my plan up to date", "bring my requirements up to date", or asks for a "version upgrade"
  of a plan/requirements set. ONE skill covers both targets: "upgrade-plan [feature-name]"
  re-evaluates a named feature plan against current standards, and "upgrade_requirements"
  re-evaluates the set in requirements/. It detects the target from the phrasing/arguments and
  branches. The flow is: detect version, assess gaps, present an upgrade report BEFORE changing
  anything, pass a non-negotiable Content Quality Gate, apply upgrades preserving all
  user-authored content verbatim, then verify. Does NOT auto-advance the roadmap.
---

# upgrade-plan — Upgrade a Plan or Requirements Set

> **CodeOps Skills Version**: 3.12.0

Plans and requirements are living documents. As CodeOps standards evolve, older artifacts drift
out of date. This skill **detects** staleness, **assesses** gaps against current standards,
**upgrades** documents while preserving all user-authored content, and **verifies** the result.

This skill covers **upgrades only**. To create a new plan use the make-plan skill; to create a new
requirements set use the make-requirements skill.

> **Resolve paths layout-aware, and don't migrate layout here.** A plan/requirements set lives at a
> flat path (`plans/<feature>/`, `requirements/`) or, in a nested-layout repo, under
> `codeops/features/<f>/…` — resolve it via **[../../_shared/layout-convention.md](../../_shared/layout-convention.md)**.
> This skill upgrades **content/version** in place; it never moves a repo between layouts. Converting
> a flat repo to the nested `codeops/` layout is the **`setup-codeops`** skill's job — point the user
> there for that, and keep upgrades within the existing layout.

## Which target? (branch first)

Detect the target from the phrasing/arguments before doing anything else:

| Trigger | Target | Directory |
|---------|--------|-----------|
| `upgrade-plan [feature-name]`, "upgrade my plan", "bring the plan up to date" | **Plan** | `plans/[feature-name]/` |
| `upgrade_requirements`, "upgrade my requirements", "bring requirements up to date" | **Requirements** | `requirements/` |

If the target is genuinely ambiguous (e.g. bare "upgrade"), ask the user which one. The two
branches share the same 4-phase flow; the per-document checklists differ and live in
[upgrade-checklists.md](upgrade-checklists.md).

## Version detection & classification

1. Read the plan's `00-index.md` (or `99-execution-plan.md`), or for requirements the `README.md`
   and individual RD documents.
2. Look for a version stamp: `> **CodeOps Version**: X.Y.Z` or `> **CodeOps Skills Version**: X.Y.Z`.
3. Compare the stamp against the current standard version **3.3.2** (the bumps since `3.0.0` are behavioral — no document migration — so `3.0.0`–`3.3.1` artifacts remain compatible).

| Condition | Classification | Action |
|-----------|---------------|--------|
| No version stamp found | Pre-versioning / outdated | Full upgrade recommended — the artifact predates version stamping |
| Stamp = `3.0.0`, `3.1.0`, `3.2.0`, `3.3.0`, `3.3.1`, or `3.3.2` | Current | Report "No upgrade needed" — already compatible (behavioral, no-migration bumps since 3.0.0) |
| Stamp < `3.0.0` | Outdated | Upgrade recommended — re-evaluate against current standards |

After a successful upgrade, every stamped document carries `> **CodeOps Skills Version**: 3.12.0`.

## The 4 phases (overview)

The same flow applies to both branches. Per-document checklists are in
[upgrade-checklists.md](upgrade-checklists.md); the Phase 2B gate detail is in
[content-quality-gate.md](content-quality-gate.md).

### Phase 1 — Assessment

1. **Locate the directory** and read all `.md` documents in it.
2. **Detect version stamps** (see above).
3. **Load current standards** — for plans, the make-plan skill's current standards; for
   requirements, the make-requirements skill's current standards. Coding/testing standards come
   from your project's coding/testing standards (AGENTS.md).
4. **Generate a gap analysis** — compare each document against current templates and checklists.

**Error conditions (STOP):**

| Error | Action |
|-------|--------|
| Target directory doesn't exist | **STOP** — suggest the make-plan skill (plans) or the make-requirements skill (requirements) |
| Directory is empty / has no `.md` files | **STOP** — suggest make-plan / make-requirements |
| Artifact is already at version `3.0.0`, `3.1.0`, `3.2.0`, `3.3.0`, `3.3.1`, or `3.3.2` | Report "Already current, no upgrade needed" and stop |

### Phase 2 — Upgrade Report (BEFORE any changes)

> **Grounded Options & Recommendations (coding standards → Working style) apply here.** Before presenting options/findings/recommendations: filter out non-viable ones (no strawmen; ≥2 only when ≥2 are genuinely viable, else present the single viable path and name what was rejected), second-guess each, verify any code-modifying option against the actual current code (cite `file:line`), and lead with a recommendation backed by grounded reasoning. Match ceremony to stakes — the user decides. Apply the recommendation-hardening protocol (`_shared/recommendation-hardening.md`) to consequential recommendations; escalate to an independent challenger only when the decision is genuinely high-stakes.

Present findings to the user **before making any changes**:

```markdown
## Upgrade Report: [feature-name | requirements]

**Current Version:** [stamp or "none (pre-versioning)"]
**Target Version:** 3.3.2

### Will Be Added (missing sections/content)
- [ ] ...

### Will Be Updated (structural/format changes)
- [ ] ...

### Will Be Preserved (user content — no changes)
- [ ] ...

### Proceed with upgrade?
```

Then **ask the user** to choose:

1. **"Yes, apply all upgrades"** — proceed to Phase 2B.
2. **"Show me the details first"** — display a side-by-side comparison of changes, then re-ask.
3. **"No, keep as-is"** — abort the upgrade.

### Phase 2B — Content Quality Gate (🚨 non-negotiable hard gate)

**Phase 3 is BLOCKED until this gate passes.** A document with modern formatting but vague content
is still a bad document. Before any structural upgrade you MUST scan every existing document for
content gaps across **all 12 ambiguity categories**, flag every **vague-language pattern**, append
findings to the **Ambiguity Register** tagged `(upgrade)`, and resolve every entry with an explicit
user decision.

**🚫 While blocked:** do not proceed to Phase 3, do not update version stamps, do not modify any
document content, do not accept vague language as "good enough", do not rationalize ("the existing
approach seems reasonable").

**✅ The gate opens ONLY when all 5 conditions hold:**

1. Every content gap found is in the Ambiguity Register.
2. Every register entry has Status = "✅ Resolved" with the user's explicit decision.
3. The user has reviewed and confirmed the complete register (for >15 items, present in batches by
   category).
4. Zero vague-language patterns remain unresolved.
5. Zero deferred items — the user decides NOW (no-deferral, no-delegation policy).

Full detail — the 12 categories, the vague-language list, register handling/append/template, and
the gate-open conditions — is in [content-quality-gate.md](content-quality-gate.md). **Read it
before running Phase 2B.**

### Phase 3 — Apply Upgrades

Once the gate passes, re-evaluate each document against current templates AND write the resolved
content fixes into the documents with an `AR #` back-reference. Use the per-document re-evaluation
checklists in [upgrade-checklists.md](upgrade-checklists.md) (separate checklists for the plan docs
`00-index` / `00-ambiguity-register` / `01-requirements` / `02-current-state` / `03-tech-specs` /
`07-testing-strategy` / `99-execution-plan`, and for the requirements docs `README` / RD documents
/ register).

**🚨 Content Preservation Rules — the upgrade MUST NOT destroy user work:**

| Content type | Action |
|--------------|--------|
| Technical specifications (`03-XX` docs) | **Preserve verbatim** |
| Scope decisions | **Preserve verbatim** |
| Completed task checkboxes `[x]` | **Preserve** |
| Requirement descriptions, acceptance criteria, rationale | **Preserve verbatim** |
| Priority/status decisions, custom notes/comments | **Preserve** |
| Version stamps | **Update** to `3.3.2` |
| Template structural sections | **Update** if the format changed |
| Missing protocol sections (security, techdocs, session protocol, …) | **Add** |
| Cross-references | **Update** to current skill/command names |
| Content gaps resolved in Phase 2B | **Insert** with an `AR #` back-reference |

### Phase 4 — Verification

1. ✅ Confirm all documents updated.
2. ✅ No user content lost (compare document count, task/RD count, technical specs, acceptance criteria).
3. ✅ Version stamps now read `> **CodeOps Skills Version**: 3.12.0`.
4. ✅ Ambiguity Register complete — every entry resolved.
5. ✅ Zero vague language remaining in any document.
6. ✅ `AR #` back-references present for every content gap resolved during the upgrade.
7. ✅ Present the upgrade summary to the user.

```markdown
## Upgrade Complete: [feature-name | requirements]

**Version:** [old] → 3.3.2

### Structural Changes Applied
- ...

### Content Quality Gaps Resolved: [X] items
- See `00-ambiguity-register.md` for the full audit trail.

### Documents Updated: X of Y
### User Content Preserved: ✅ All technical specs, task states, and custom content intact
### Ambiguity Register: ✅ All entries resolved — zero vague language remaining
```

## Partial-upgrade resume handling

If a previous upgrade was interrupted (some documents stamped with the target version, others not):

1. **Detect the partial state** from the per-document stamps.
2. **Resume** — only upgrade documents that still need it; leave current ones untouched.
3. **Report** which documents were already current and which were upgraded.

## Notes & pointers

- **The upgrade does NOT auto-advance the roadmap.** Roadmap status is unchanged by an upgrade.
- Cross-references to update during the upgrade: make-plan → the make-plan skill; requirements →
  the make-requirements skill; techdocs → the techdocs skill; git-commands → the the `git-commit` skill and
  the `git-commit` skill in push mode commands; project conventions → the project's AGENTS.md (or detected project
  conventions); coding/testing → your project's coding/testing standards (AGENTS.md).
- Related skills/commands: make-plan, make-requirements, exec-plan, roadmap, techdocs,
  the `git-commit` skill, the `git-commit` skill in push mode.

**Key principles:** version-agnostic full re-evaluation (not incremental patches); content-first
(the gate catches gaps before structural upgrades); non-destructive (user content preserved
verbatim); transparent (changes approved before applied); resumable; zero-ambiguity (no vague
language, no deferred decisions, no AI guesswork survives the upgrade).
