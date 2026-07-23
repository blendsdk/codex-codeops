# Changelog

All notable changes to CodeOps for Codex are recorded here.

## 0.2.0-beta.7 — 2026-07-23

- Scope readiness gates to the selected feature so unrelated draft work does
  not block planning or execution.
- Treat traceability node IDs as feature-local and require explicit
  qualification for cross-feature links.
- Add planning target, context, and modification boundaries plus bounded
  post-gate ambiguity discovery.
- Align make-plan with the shared named-deferral contract.
- Review complete phase changes in every commit mode using worktree snapshots
  that include staged, unstaged, committed, and newly created files.
- Escalate repeated identical verification failures instead of retrying
  indefinitely.

## 0.2.0-beta.6 — 2026-07-23

- Keep single-document preflight audits scoped to their selected target while
  using related artifacts only as context.
- Bound corrective rescans, preserve finding identity by root cause, and stop
  cleanly when minor findings are explicitly accepted.
- Store narrow preflight evidence separately so sibling requirements and whole
  plans cannot advance from an out-of-scope pass.
- Add deterministic validation for preflight scope and convergence contracts.

## 0.2.0-beta.5 — 2026-07-23

- Make `status` a successful observation for structurally valid projects whose
  requirements or plans are not yet execution-ready.
- Treat migrated Claude roadmap, requirement, and plan documents as first-class
  Codex schema-1 artifacts during roadmap presentation.
- Add regression coverage for valid-but-blocked status and invalid status data.

## 0.2.0-beta.4 — 2026-07-23

- Exclude `codeops/_archive` traceability graphs and execution plans from live
  readiness, lifecycle, and task-progress reports.
- Add regression coverage for repositories with large archived project histories.

## 0.2.0-beta.3 — 2026-07-23

- Enforce per-node lifecycle status vocabularies and reopened-ambiguity invalidation.
- Make the migration layout marker the final commit point after required artifacts.
- Retain versioned ambiguity-benchmark, installation-lifecycle, and independent-review evidence.
- Reconcile release claims, platform boundaries, and governing plan state with evidence.

## 0.2.0-beta.2 — 2026-07-23

- Add deterministic traceability, readiness, lifecycle, drift, and strict-config validation.
- Add Codex-native capability roles and optional project agent installation.
- Add compiler, financial, web, distributed, and migration ambiguity lenses.
- Add retained adversarial scenario and Claude 3.12.0 parity evidence.
- Add install, migration, concepts, troubleshooting, CI, and release documentation.

## 0.2.0-beta.1 — 2026-07-23

- First installable Codex-native beta with requirements, planning, execution,
  review, roadmap, migration, documentation, routing, and utility skills.
