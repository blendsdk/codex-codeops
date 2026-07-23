# Ambiguity Register: Dependency-Aware Readiness

> **Status**: ✅ GATE PASSED — all 30 items resolved
> **Last Updated**: 2026-07-23 12:37 CEST

| # | Category | Ambiguity / Gap | Options Presented | User Decision | Status |
|---|---|---|---|---|---|
| AR-1 | Scope | Should this solve only the observed project case or provide a general readiness model? | General target-scoped model / project-specific patch | General target-scoped model for any coding project | ✅ Resolved |
| AR-2 | Data & state | How are graph relationships represented and directed? | Canonical directed typed edges with derived inverses / retain untyped bidirectional links | Canonical directed typed edges; derive inverse views and reject redundant or contradictory inverses | ✅ Resolved |
| AR-3 | Data & state | How are trace ownership and blocking dependencies distinguished? | Separate trace and dependency relation families / one overloaded relation family | Separate trace relations (`specified-by`, `accepted-by`, `tested-by`, `implemented-by`, `verified-by`, `affected-by`) from dependency relations (`depends-on`, `consumes-contract`, `related`, `release-coupled`) | ✅ Resolved |
| AR-4 | Behavioral | Which readiness rules apply at different lifecycle stages? | Explicit gate profiles / one universal readiness closure | Explicit requirements, plan, execution, task-completion, feature-acceptance, and release gate profiles | ✅ Resolved |
| AR-5 | Naming & terminology | How are targets identified? | Canonical `<feature>/<node-id>` with scoped shorthand / filenames or bare IDs | Canonical `<feature>/<node-id>`; accept `--feature f --target ID` shorthand and reject ambiguous bare targets | ✅ Resolved |
| AR-6 | Integration points | How are contracts and their stability represented? | Contract nodes plus orthogonal maturity / status-only approximation | Contract nodes with `experimental`, `provisional`, `stable`, and `frozen` maturity; consumption edges declare required maturity | ✅ Resolved |
| AR-7 | Edge cases | How are legitimate dependency cycles handled? | Atomic planning groups / allow arbitrary cycles / reject every cycle | Atomic planning-group nodes; contract groups before cycle analysis and reject remaining dependency cycles | ✅ Resolved |
| AR-8 | Data & state | What deterministically triggers downstream staleness? | Semantic revisions plus validation snapshots / status-only invalidation | Store semantic revisions and dependent validation snapshots; propagate only through affected trace/dependency relations | ✅ Resolved |
| AR-9 | Technical | How is compatibility with schema 1 preserved? | Explicit schema-2 migration while retaining schema-1 reads / in-place inference / breaking replacement | Add schema 2; retain exact schema-1 behavior; require explicit preview-first, idempotent upgrade and user resolution of ambiguous legacy links | ✅ Resolved |
| AR-10 | Behavioral | Should unrelated graph corruption block a selected target? | Scoped target blocking with portfolio-wide validation / preserve global blocking | `validate` remains portfolio-wide; target readiness blocks on configuration, canonical identity, target closure, and entering cross-feature references while reporting unrelated failures as diagnostics | ✅ Resolved |
| AR-11 | Scope | How do release gates choose included work? | Explicit release membership / every discovered graph | Explicit required, optional, excluded, and release-coupled membership; portfolio governance remains separate | ✅ Resolved |
| AR-12 | Integration points | Which workflows adopt targeted gates? | All lifecycle workflows / deterministic command only | Apply target-aware profiles to make-requirements, preflight, make-plan, exec-plan, roadmap, feature acceptance, and release readiness | ✅ Resolved |
| AR-13 | Naming & terminology | What is the plan name and path? | `dependency-aware-readiness` / another slug | `plans/dependency-aware-readiness/` | ✅ Resolved |
| AR-14 | Non-functional | Which repository command set is the authoritative full verification gate? | Five commands from `AGENTS.md` / a narrower command | Use all five commands specified by `AGENTS.md` | ✅ Resolved |
| AR-15 | Behavioral | How are lifecycle gate predicates specified? | Normative matrices / implementation-defined constants | Normative valid-target, closure, status, evidence, blocker, revision, and verdict matrices | ✅ Resolved |
| AR-16 | Scope | Does schema 2 preserve the governing specifications-complete gate? | Distinct `specifications` gate / fold into plan | Preserve distinct G2 `specifications` gate between requirements and plan | ✅ Resolved |
| AR-17 | Data & state | How are requirement sets, feature aggregates, and audited artifacts targeted? | Explicit aggregate/audit nodes / virtual directory identities / omit | Explicit aggregate node types and audit profile; graphless ad-hoc paths receive semantic audit only | ✅ Resolved |
| AR-18 | Data & state | How are semantic revisions made deterministic? | Versioned digest descriptor / monotonic revision | Persist source descriptors, canonical normalization, versioned SHA-256 digest, and validation snapshots | ✅ Resolved |
| AR-19 | Failure recovery | How are graph state transitions written safely? | Shared atomic transition library / manual skill edits | Shared transition library with validated compare-and-swap, temp write, flush, atomic replace, recovery, and post-write validation | ✅ Resolved |
| AR-20 | Integration points | How do workflows read and mutate target lifecycle state? | Explicit target status/transition CLI / private per-skill logic | Explicit target-aware `status` and transition commands backed by the shared state library | ✅ Resolved |
| AR-21 | Integration points | How is traceability schema upgraded? | State CLI subcommand / separate upgrader | A modular traceability-upgrade command with versioned preview/resolution schemas and complete recovery/exit contracts | ✅ Resolved |
| AR-22 | Ordering | When is schema-1 compatibility characterized? | Before shared rewrites / during migration phase | Before any parser/readiness rewrite and rerun in every phase | ✅ Resolved |
| AR-23 | Naming & terminology | How are Python spec and implementation test modules named? | Importable underscore modules / dotted names | Importable `test_*_spec.py` and `test_*_impl.py` modules plus collection assertions | ✅ Resolved |
| AR-24 | Scope | Which graphs count as live project state? | Artifact-root-aware discovery / recursive repository scan | Configured or conventional live artifact roots only; fixture roots load only when passed as the command root | ✅ Resolved |
| AR-25 | Technical | How is the state engine modularized? | Thin CLI plus focused modules / monolithic script | Thin CLI plus schema, discovery, gates, transitions, migration, and rendering modules | ✅ Resolved |
| AR-26 | Dependencies | How does this corrective plan relate to codex-port 6.8? | Verified child closeout / separate later owner | Treat as pilot corrective child; close 6.8 only after retained rerun evidence passes | ✅ Resolved |
| AR-27 | Consistency | Who owns ST-to-specification mapping? | One authoritative mapping / local ranges | One authoritative mapping in the testing strategy; specs and tasks cite it | ✅ Resolved |
| AR-28 | Compatibility | Is repository fixture ingestion protected schema-1 behavior? | Corrected discovery exception / retain in schema 1 | It is a corrected defect outside compatibility; preserve schema-1 behavior on legitimate isolated roots | ✅ Resolved |
| AR-29 | Failure recovery | How are stale locks and interrupted multi-graph operations recovered? | Explicit recovery command / single-graph-only release | Explicit `transition-recover` roll-forward/rollback contract with proof, hashes, collision protection, and stable outcomes | ✅ Resolved |
| AR-30 | Technical (runtime) | How can this plan bootstrap when the current root readiness command consumes invalid fixtures and no live graph exists? | Bounded Phase-1/2 bootstrap / isolated misleading v1 graph / stop | Permit only Phases 1–2 under the passed preflight and full repository gate; create schema-2 plan traceability after targeted readiness lands and require it for Phases 3–5 | ✅ Resolved |

## Resolution Notes

**AR-1 through AR-13:** The user approved the general baseline and then explicitly accepted all hardened recommendations after current-state analysis and an independent design challenge.

**AR-2:** An edge is stored as `source --relation--> target`. `blocks` and `provides-contract` are derived views, not stored dependency relations. `related` is contextual and symmetric; `release-coupled` affects release closure only.

**AR-3:** Gate profiles select the owned trace descendants required for that lifecycle stage and traverse only upstream blocking dependencies.

**AR-6:** Only contract nodes carry maturity in schema 2. `frozen` requires an explicit reopened decision and impact review; it does not mean permanently immutable.

**AR-7:** Targeting one group member expands atomically to the complete group, whose members must share the applicable gate.

**AR-8:** Revision snapshots and status transitions must be updated atomically. `related` never propagates staleness; `release-coupled` invalidates release readiness only.

**AR-9:** Typed target readiness is unavailable to schema-1 graphs until explicit upgrade. Migration preserves status and evidence and never guesses the meaning of an ambiguous legacy link.

**AR-10:** Duplicate canonical identities remain global blockers because target resolution would otherwise be untrustworthy.

**AR-11:** A release is an explicit graph target rather than an alias for portfolio readiness.

**AR-14:** The detected candidate is:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

The user explicitly confirmed this complete command set.

**AR-15 through AR-27:** During iteration-1 preflight, the user accepted the recommended resolution
for PF-001 through PF-013. The detailed evidence and alternatives remain owned by
`00-preflight-report.md`.

**AR-28 and AR-29:** During iteration-2 preflight, the user accepted the recommended resolutions
for PF-014 and PF-015.

**AR-30:** At execution entry, the user explicitly accepted the bounded bootstrap resolution.
This is not a general readiness bypass and expires before Phase 3.
