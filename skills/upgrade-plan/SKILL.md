---
name: upgrade-plan
description: Upgrade an existing CodeOps requirements set, specification, plan, or project from a legacy artifact format to the current schema and quality standards. Use for upgrade my plan, upgrade requirements, migrate CodeOps artifacts, add traceability, or bring project artifacts up to date. Assesses and previews changes, closes content ambiguities before structural migration, preserves user-authored semantics and progress, and verifies the result without advancing the roadmap.
---

# Upgrade CodeOps artifacts

The current Codex artifact schema is `1`. Historical Claude CodeOps `3.x` stamps describe the producing skill release, not this schema. Treat them as legacy input requiring assessment, not as numeric predecessors of schema 1.

## Scope

Upgrade content and structure in place. Layout moves belong to `setup-codeops`. Never combine a layout migration and semantic/schema upgrade into one irreversible operation.

Targets may be a requirements set, one feature plan, one feature, or the whole CodeOps project. Resolve flat/nested paths via [../../_shared/layout-convention.md](../../_shared/layout-convention.md).

## Phase 1 — Read-only assessment

1. Read every target artifact and its links.
2. Detect `CodeOps Artifact Schema: 1`, legacy `CodeOps Skills Version`, partial migrations, missing traceability, and contradictory stamps.
3. Run current requirement, specification, plan, domain-lens, and content-quality checks.
4. Inventory user-owned semantics, completed/in-progress task marks, custom notes, identifiers, and links that must survive byte-for-byte or meaning-for-meaning.
5. Produce an upgrade report listing additions, structural changes, semantic gaps, preserved content, risks, and rollback/recovery method.

If every graph is schema 2, traceability validates, and current semantic gates pass, report no
upgrade needed. For schema 1, use the public preview, resolution, apply, and validate protocol:

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" traceability-upgrade --root . \
  --feature <feature> --preview <preview>
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" traceability-upgrade --root . \
  --feature <feature> --preview <preview> --resolutions <resolutions> --apply
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" validate --root .
```

The preview and closed-form resolutions are reviewable artifacts. Apply is atomic and may require
`transition-recover`; never hand-edit around a recovery-required result.

## Phase 2 — Approval and content-quality gate

Present the report before writing. The user may approve all, request details, narrow scope, or decline.

After approval, run [content-quality-gate.md](content-quality-gate.md). Structural modernization must not hide vague or contradictory content. Record every material gap as an ambiguity, resolve it explicitly, and update its authoritative owner before migration.

## Phase 3 — Structural migration

Follow [upgrade-checklists.md](upgrade-checklists.md):

- add `> **CodeOps Artifact Schema**: 1` where artifact stamps belong;
- create/update feature `traceability.json` with stable typed nodes;
- preserve completed `[x]` and implemented `[~]` task states;
- preserve technical decisions, requirements, criteria, rationale, and notes;
- update renamed skill/project-guidance references;
- add missing readiness, recovery, domain, security, verification, and project-tracking sections; and
- never silently renumber identifiers that external artifacts reference.

Use small recoverable edits. If interrupted, schema stamps and graph validation identify remaining work.

## Phase 4 — Verification

Run:

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" validate --root .
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness --root .
```

Then verify document/task/requirement counts and user semantics are preserved; every migrated node has valid relationships; material ambiguities are resolved or explicitly approved deferrals; active content is approved; tests, tasks, implementation, and verification are traced; roadmap lifecycle state is unchanged except for approved drift repair; and the Git diff contains only the approved migration.

Report old formats, new schema, files changed, ambiguities resolved, traceability coverage, preserved progress, and residual risk. Do not auto-advance lifecycle stages.
