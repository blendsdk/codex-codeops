# Preflight Report: Scope Expansion Control Mini-Plan

> **Status**: ✅ PREFLIGHT PASSED — all findings resolved
> **Iteration**: 3 (final bounded verification)
> **Artifact**: single plan document at `plans/scope-expansion-control/99-execution-plan.md`
> **Artifact Hash**: `sha256:ae52be25b9240bf65cc56cd604931b7d304616a1d0b155acab376b831899d7ec`
> **Codebase Grounded**: 14 workflow, policy, test, documentation, and validation files examined
> **Current Artifact Hash**: `sha256:41d13efb669080491ca8567daea79bb33d2c3c9c753a892f5f2f82b6ab35b16b`
> **Last Updated**: 2026-07-31 21:53
> **Passing Artifact Hash**: `sha256:4d73135d676a38a81255087c2c7d601345ceefeb5f9f900a00df453849b285a4`

> **SAME-SESSION REVIEW:** This artifact was created in the current session. Same-agent bias risk
> is elevated. Five independent dimension-cluster audits and one independent recommendation
> challenger were used to reduce that risk.

## Audit Scope

- **Audit target**: `plans/scope-expansion-control/99-execution-plan.md`
- **Context documents**: repository guidance; shared ambiguity, auto-design, specification-first,
  quality-profile, and recommendation-hardening policies; planning, preflight, and execution
  skills; conformance-test patterns; validation scripts; user documentation; changelog.
- **Modification set**: this report only. No plan fix is authorized by a finding decision alone.

## Codebase Context Summary

**Tech Stack:** Markdown workflow packages, Python conformance tooling, and Bash validation.

**Architecture:** Shared policies own cross-workflow invariants; skills link to those policies;
Python conformance tests and deterministic shell assertions protect shipped workflow contracts.

**Key Files Examined:** `AGENTS.md`, `_shared/auto-design.md`,
`_shared/spec-first-ordering.md`, `_shared/quality-profile.md`,
`skills/make-plan/SKILL.md`, `skills/preflight/SKILL.md`,
`skills/exec-plan/SKILL.md`, `skills/exec-plan/execution-protocol.md`,
`tests/conformance/test_scope_expansion_control_spec.py`, `scripts/validate-codex.sh`,
`docs/concepts.md`, `docs/tutorial.md`, and `CHANGELOG.md`.

**Reference Verification:** Every path and verification command named by the mini-plan exists. No
traceability graph owns this lightweight task, so deterministic graph readiness does not apply.

## Summary by Dimension

| # | Dimension | Findings | Highest Severity |
|---|---|---:|---|
| 1 | Ambiguities | 3 | 🟠 Major |
| 2 | Implicit Assumptions | 0 | — |
| 3 | Logical Contradictions | 0 | — |
| 4 | Completeness Gaps | 1 | 🟡 Minor |
| 5 | Dependency Issues | 0 | — |
| 6 | Feasibility Concerns | 0 | — |
| 7 | Testability | 0 | — |
| 8 | Security Blind Spots | 0 | — |
| 9 | Edge Cases | 0 | — |
| 10 | Scope Creep Indicators | 0 | — |
| 11 | Ordering & Sequencing | 1 | 🟠 Major |
| 12 | Consistency | 0 | — |
| 13 | Codebase Alignment | 0 | — |

## Summary by Severity

| Severity | Count | Status |
|---|---:|---|
| Critical | 0 | — |
| Major | 4 | Pending user ruling |
| Minor | 1 | Pending user ruling |
| Observation | 0 | — |

## Findings

### PF-001: Modification membership is not deterministic 🟠 MAJOR

**Dimension:** Ambiguities

**Location:** `99-execution-plan.md`, Scope, lines 20–21

**Codebase Evidence:** `skills/make-plan/SKILL.md:44-50`,
`skills/preflight/SKILL.md:72-89`, and `skills/exec-plan/execution-protocol.md:63-68` require exact
authorized or expected modification sets.

**The Problem:** Whole categories such as `_shared/`, "directly owned references," and "user
documentation" do not identify which files execution may edit.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Enumerate exact anticipated paths. | Deterministic initial scope. | No rule for a newly discovered necessary file. |
| B | Keep categories and require approval for additions. | Handles discovery. | Initial membership remains ambiguous. |
| C | Enumerate exact paths and require explicit approval before adding any later path. | Exact initial authority plus a safe discovery path. | May add an intentional execution pause. |

**Recommendation:** Option C. The challenger added the expansion gate because neither original
option fully satisfied both initial precision and safe discovery.

**User Decision:** Resolved — user accepted recommendation Option C.

**Confidence:** High. **Hardening:** changed to hybrid Option C. **Challenger:** converged on the
root cause and supplied the stronger hybrid.

### PF-002: Necessary-correction classification lacks a burden of proof 🟠 MAJOR

**Dimension:** Ambiguities

**Location:** `99-execution-plan.md`, Objective, lines 10–13; Tasks, lines 27–29

**Codebase Evidence:** `_shared/auto-design.md:41-60` keeps product scope and scope expansion
outside delegated technical authority.

**The Problem:** Without a causal classification rule, an agent can label optional work
"necessary" and bypass the scope boundary, or suppress a material unresolved risk as optional.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Necessary only when grounded evidence shows the smallest correction is required for the requested behavior to be correct, safe, or feasible and no compliant in-scope solution exists; treat credible unresolved material risk as a blocking investigation. | Preserves both safety and user scope authority. | May require investigation before classification. |

**Recommendation:** Option A. Speculative benefits remain silent by default; reporting necessity
still does not authorize editing outside the exact modification set.

**User Decision:** Resolved — user accepted recommendation Option A.

**Confidence:** High. **Hardening:** added the blocking-uncertainty state. **Challenger:** converged
on the evidence rule and strengthened its safety handling.

### PF-003: Stable proposal ownership and lifecycle are undefined 🟠 MAJOR

**Dimension:** Ambiguities

**Location:** `99-execution-plan.md`, Objective, lines 10–13; Tasks, lines 27–29

**Codebase Evidence:** `_shared/zero-ambiguity-gate.md:31-75` gives the Ambiguity Register a
different purpose and state vocabulary; the specification oracle currently checks prose tokens
but cannot choose a lifecycle design.

**The Problem:** The plan does not own ID allocation, persistence, state transitions, resume,
revival, or invalidation of work derived from a reversed decision.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Use an artifact-local `00-scope-expansion-register.md` with monotonic `SE-*` IDs, append-preserved history, and `Keep`, `Defer`, `Discard`, and `Superseded` states. | Separates optional-scope authority from ambiguity resolution and works for planning, audit, and execution. | Adds one durable artifact when exploration finds proposals. |
| B | Add an equivalent section to the Ambiguity Register. | Reuses an existing artifact. | Conflates optional scope with ambiguity-gate semantics and does not fit every audit target. |

**Recommendation:** Option A. Only `Keep` may generate executable work. Revival after `Discard`
requires new evidence and renewed authority without erasing history.

**User Decision:** Resolved — user accepted recommendation Option A.

**Confidence:** High. **Hardening:** no change. **Challenger:** converged.

**Iteration 2 evidence:** The first fix did not define deferred-entry resume behavior; a single
neighboring filename collides when several single-document or ad-hoc targets share a directory;
and reversing `Keep` invalidates tasks without invalidating causally derived specifications,
tests, implementation, and verification.

**Residual recommendation:** Record a named owner and observable revisit trigger for `Defer`; keep
it dormant on ordinary resume and re-present the same ID only when trigger evidence exists or the
user asks. Add `_shared/layout-convention.md` to the exact modification set and let it own
collision-free target-qualified register paths. Reversing `Keep` must stop affected execution,
stale dependency-traced downstream artifacts, supersede pending/in-progress derived tasks,
preserve history, and require explicit safe removal or remediation authority without automatic
irreversible rollback.

**Residual User Decision:** Resolved — user accepted the complete residual recommendation and
authorized `_shared/layout-convention.md` in the exact modification set.

### PF-004: Checklist-owned review creates a quality-gate cycle 🟠 MAJOR

**Dimension:** Ordering & Sequencing

**Location:** `99-execution-plan.md`, Task T-01.3, lines 32–33

**Codebase Evidence:** `skills/exec-plan/execution-protocol.md:132-176` starts whole-task quality
review only after the last task verifies and then verifies and re-reviews accepted blocking fixes.

**The Problem:** T-01.3 cannot verify until its included review finishes, while the mandatory
review cannot start until T-01.3 verifies.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Remove review and finding resolution from T-01.3; let the exec-plan post-task gate own review, fixes, verification, and one re-review. | Preserves one owner and valid ordering. | Review is no longer a task checkbox. |
| B | Add a later checklist review task. | Review remains visible in the checklist. | The new last task triggers another post-task review and preserves the cycle. |

**Recommendation:** Option A; Option B is not viable under the mandatory whole-task review
contract.

**User Decision:** Resolved — user accepted recommendation Option A.

### PF-006: Accepted rules are not covered by the specification oracle 🟠 MAJOR

**Dimension:** Testability

**Location:** `99-execution-plan.md`, classification and lifecycle at lines 15–18 and 40–46;
completed Task T-01.1 at lines 50–52

**Codebase Evidence:** `tests/conformance/test_scope_expansion_control_spec.py:56-108` checks broad
tokens but not the accepted causal proof, blocking uncertainty, target-qualified ownership,
monotonic history, deferred resume, or reverse-`Keep` invalidation. `_shared/spec-first-ordering.md`
requires the expanded oracle to be red before implementation.

**The Problem:** T-01.2 could make all seven existing cases green while omitting material rules
accepted during preflight.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Reopen T-01.1, preserve its earlier red evidence as historical, add behavior-focused cases for every accepted invariant, and reconfirm the expanded module red before implementation. | Restores specification-first independence and full authority coverage. | Adds another red-phase cycle. |

**Recommendation:** Option A.

**User Decision:** Resolved — user accepted recommendation Option A.

**Confidence:** Very high. **Hardening:** no change. **Challenger:** converged.

## Iteration 3 Verdict

The bounded final scan verified the complete PF-003 lifecycle and path-ownership correction and
the PF-006 specification-oracle reopening. All three independent verification clusters returned no
findings. PF-001 through PF-006 are resolved, and the mini-plan is ready for execution.

**Confidence:** Very high. **Hardening:** no change. **Challenger:** converged.

### PF-005: Validation and release-note deliverables are implicit 🟡 MINOR

**Dimension:** Completeness Gaps

**Location:** `99-execution-plan.md`, Scope, lines 20–21; Tasks, lines 27–33

**Codebase Evidence:** `scripts/validate-codex.sh:107-247` owns deterministic contract assertions;
`CHANGELOG.md:5-21` separately owns release notes.

**The Problem:** The modification set includes validation assertions and release notes, but no
task explicitly requires either deliverable.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Name `scripts/validate-codex.sh` and `CHANGELOG.md` explicitly in T-01.3. | Makes completion measurable. | Slightly lengthens the mini-plan. |

**Recommendation:** Option A.

**User Decision:** Resolved — user accepted recommendation Option A.
