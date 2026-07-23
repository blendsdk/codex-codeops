# Zero-Ambiguity Gate (shared protocol)

> **CodeOps Artifact Schema**: 1

This is the **single canonical definition** of the Zero-Ambiguity Gate. It lives at the plugin
root in `_shared/` (deliberately outside `skills/`, like `layout-convention.md`). The gate-running
skills link here instead of carrying their own copies:

| Caller | Phase | Blocked artifacts while the gate is closed |
|--------|-------|--------------------------------------------|
| make-plan | Phase 1C | every plan document (`00-index.md`, `01-requirements.md`, specs, execution plan) |
| make-requirements | Phase 2B | every requirement document (`RD-XX-*.md`, `requirements/README.md`) |
| upgrade-plan | Phase 2B (Content Quality Gate) | Phase-3 structural upgrades, version stamps, any document edit |

Each caller keeps a short preamble (phase name, blocked artifacts, caller-specific notes) and
links here for everything below. Change the gate in one place: here.

## Why this gate exists

Artifacts built on ambiguity produce implementations built on guesswork. When the AI guesses, the
user gets requirements they didn't specify, behaviors they didn't define, and architectures with
no accountable authority. Every item in every gated artifact must trace back to an **authorized
resolution**: an explicit user decision in normal mode, or a complete eligible delegated record
under active auto-design. If you cannot point to that authority, you have failed this gate.

> **Recommendation hardening (complex/sensitive decisions).** When you present options for an
> ambiguity tagged complex or sensitive, apply `_shared/recommendation-hardening.md` — spawn one
> independent challenger and reconcile before recommending, and close the presentation with the
> `Confidence:` / `Hardening:` disclosure where that protocol requires it.

## The Ambiguity Register

Before the gated phase may proceed, compile and present an **Ambiguity Register** — a formal,
numbered inventory of every identified gap, ambiguity, unstated assumption, undefined behavior,
and open question. Hunt systematically across ALL 12 categories (each row merges the widest scope
of the historical per-skill variants — use every clause that fits the artifact at hand):

| Category | What to look for |
|----------|-----------------|
| **Feature gaps** | Features mentioned but not fully specified, incomplete component specs, unclear interactions, undefined workflows |
| **Behavioral gaps** | Undefined "what happens when…" scenarios, missing error handling/states, unspecified state transitions |
| **Scope ambiguities** | Features that could go either way, unclear in/out-of-scope boundaries, vague MVP-vs-future split |
| **Technical unknowns** | Undecided architecture/technology, unresolved implementation or integration approaches, decisions stated without rationale |
| **Edge cases** | Boundary conditions, failure modes, concurrent access, empty/null states, overflow, data-volume limits |
| **Integration points** | Unclear interfaces (internal or external), undefined API contracts, missing data-flow specs |
| **Data & state** | Unclear data models/relationships, undefined ownership, missing validation rules, unspecified formats/cardinality |
| **Security & compliance** | Unaddressed threat vectors, undefined auth flows/models, missing data-protection decisions, regulatory gaps |
| **Non-functional gaps** | Missing performance targets, undefined scalability, unspecified availability |
| **UX & presentation** | Undefined user-facing text, missing error messages, unspecified display formats, unclear navigation |
| **Stakeholder conflicts** | Competing needs between user types, unresolved priority disputes, unclear permission boundaries |
| **Naming & terminology** | Unconfirmed file/dir/class/function/API names, domain terms used inconsistently, undefined jargon, ambiguous labels |

### Register template

```markdown
## Ambiguity Register: [Artifact Name]

> **Status**: ❌ GATE BLOCKED — [X] items unresolved
> *(When all resolved, change to: ✅ GATE PASSED — all [X] items resolved)*
> **Last Updated**: [Date — via `date '+%Y-%m-%d %H:%M'`]

| # | Category | Ambiguity / Gap | Options Presented | User Decision | Status |
|---|----------|-----------------|-------------------|---------------|--------|
| 1 | Behavioral | [Specific ambiguity] | [Option A / B / C] | [User's answer] | ✅ Resolved |
| 2 | Scope | [Specific ambiguity] | [Option A / B] | — | ❌ Open |
| 3 | Technical | [Specific ambiguity] | [Option A / B] | Deferred: [named decision] · owner: [who] · revisit: [trigger] | ⏸ Deferred |

### Resolution Notes

**AR-1:** [Expanded context if needed]
**AR-2:** [Pending — presented to user, awaiting answer]
```

Write the register **to disk incrementally from the first entry** (never hold it only in
memory) — it is the audit trail and must survive a crash mid-phase.

## Gate enforcement rules

**🚫 PROHIBITED while the gate is blocked:**

- ❌ Create or modify any artifact the caller's preamble lists as blocked
- ❌ Make any decision without user authority or an active, eligible auto-design delegation
- ❌ Use phrases like "we'll assume…", "by default…", "a reasonable approach would be…"
- ❌ Proceed with a partially resolved register

**✅ The gate opens ONLY when ALL are true:**

1. ✅ Every row has Status = `✅ Resolved` **or** `⏸ Deferred` (see the deferral rules below —
   a Deferred row is valid ONLY in the fully-named form).
2. ✅ Every resolution contains either the **user's explicit decision** (not a recommendation
   accepted by silence) or, under active auto-design, the complete delegated provenance required
   by `auto-design.md`. Bulk acceptance counts — see below.
3. ✅ In normal mode, the user has reviewed and confirmed the complete register. For >15 items,
   present in batches by category — the user confirms each batch, then gives a final confirmation.
   In auto-design mode, every eligible delegated row passes the authority boundary and every
   reserved row is user-confirmed. Items imported pre-resolved (from a grill-me session or an
   earlier register) do **not** need re-confirmation — only new or changed rows do.
4. ✅ Zero items are **silently** deferred — "figure it out later" without a named Deferred
   row is NOT accepted.
5. ✅ The header reads `✅ GATE PASSED — all [X] items resolved`.

**Bulk acceptance IS an explicit decision.** When the user says *"accept all your
recommendations"* (or "accept recommendations for items N–M"), record each covered row as
`✅ Resolved — User accepted recommendation: [the recommended option, spelled out]`. Per-item
re-confirmation is not required. What remains prohibited is deciding for the user when they have
NOT said this.

**Auto-design delegated resolution.** When a supporting workflow was explicitly invoked with
`--auto-design`, read `auto-design.md`. An eligible technical decision may be recorded as
`Authority: AI — delegated by --auto-design` with the complete provenance required there. That
record counts as resolved without falsely attributing the choice to the user. Reserved authority,
insufficient evidence, and unsupported workflows still require the user. Without the flag, every
normal-mode rule in this document remains unchanged.

**User dismissals:** if the user says *"that's not ambiguous, the answer is obviously X"* — that
IS a valid resolution: `✅ Resolved — User: "[their stated answer]"`. You cannot dismiss items
yourself; only the user can.

**Zero-ambiguity register:** if the systematic review finds ZERO ambiguities, still create and
save the register with header `✅ GATE PASSED — 0 ambiguities identified (systematic review
completed)`. This proves the gate was executed.

## Deferral rules (named deferral only)

A decision may be **explicitly deferred** — the status the whole pipeline shares (grill-me
produces it, this gate accepts it, preflight maps it to "Accepted Risk"):

```
⏸ Deferred — <the decision, named precisely> · owner: <who will decide> · revisit: <the trigger>
```

- All three parts are mandatory. A Deferred row missing its name, owner, or revisit-trigger is
  treated as ❌ Open.
- The user must confirm each deferral explicitly, and the consequences of deferring must have
  been stated when they did.
- **Silent deferral stays forbidden.** "Figure it out later", "TBD", or moving on without a
  named row is a gate violation, exactly as before.
- Downstream skills honor the deferral: a plan may not silently implement a deferred decision,
  and preflight records findings that touch one as `Accepted Risk — deferred per AR #N`,
  cross-referencing rather than re-litigating it.

**If the user says "I don't know" / "decide later":** (1) explain why the decision matters and
the cost of getting it wrong, (2) present options with trade-offs, (3) recommend one with
rationale, (4) guide them to an explicit choice — **or** to an explicit named deferral, (5)
record THEIR choice.

**If the user says "you decide" / "just pick one":** in normal mode, politely refuse — "I can recommend, but the
decision must be yours." Present options with your recommendation marked and wait for "I choose
[option]" (or a bulk acceptance, which qualifies). Never record "AI decided".

## Register persistence

The register is a permanent file saved with the artifact it gates (resolve the directory per
`_shared/layout-convention.md`):

- Plans: `<plan folder>/00-ambiguity-register.md`
- Requirements: `<requirements dir>/00-ambiguity-register.md`
- Upgrades: the existing register of the artifact being upgraded (append, tag `(upgrade)`,
  continue numbering) — or a fresh one if the artifact predates the gate.

## Traceability requirement

Every decision in the gated artifact must back-reference the register entry that resolved it:

```markdown
> **Decision per AR #7:** User chose Option B — time-based cache invalidation with 5-minute TTL.
```

Unbroken chain in normal mode: **user question → user answer → register entry → artifact.**
With active auto-design: **identified ambiguity → delegated provenance → register entry →
artifact**. Reserved decisions always use the normal-mode chain.

The ONLY items exempt from `AR #` back-references: **(a)** universally obvious facts with exactly
one possible interpretation (e.g., "TypeScript files use `.ts`"), and **(b)** formatting choices
with zero semantic impact. **When in doubt, it is NOT an exception — add it to the register.**

## Surface-during-authoring rule

Even after the gate passes, if you discover a NEW ambiguity while writing the gated artifact:

1. **STOP writing immediately.**
2. **Add** it to the register with the next sequential number.
3. **Resolve authority.** In normal mode, present it to the user with options and trade-offs.
   With active auto-design, resolve an eligible technical item under `auto-design.md` or present
   a reserved item to the user.
4. **Wait** for the user's explicit decision (or named deferral) whenever normal mode or reserved
   authority applies; otherwise record the complete delegated provenance.
5. **Record** the resolution, **then** resume writing.

Never "make a reasonable choice and move on."

## Interaction with the grill-me skill

The gate fires regardless of how discovery was conducted — including when grill-me ran first. The
grill-me shared understanding feeds INTO the register as pre-resolved context but does not replace
the gate: still scan all 12 categories. Items settled by grill-me import as `✅ Resolved` rows
(with a session note), grill-me's explicitly-deferred items import as `⏸ Deferred` rows in the
named form, and per gate rule 3 imported rows are not re-confirmed — only new rows are.

## Interaction with the upgrade-plan skill

When an artifact is upgraded, the gate applies to **new** decisions introduced during the upgrade
(entries tagged `(upgrade)`). Existing resolved decisions are preserved; only new or changed items
go through the gate.
