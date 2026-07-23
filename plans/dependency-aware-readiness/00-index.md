# Dependency-Aware Readiness Implementation Plan

> **Feature**: Target-scoped, dependency-aware lifecycle gates for CodeOps
> **Status**: Planning Complete
> **Created**: 2026-07-23
> **CodeOps Artifact Schema**: 1

## Overview

CodeOps currently proves readiness at feature or portfolio scope. This plan evolves the durable
traceability graph so each lifecycle workflow can advance one requirement, plan, task, feature, or
release when that target and its blocking dependency closure are ready, without forcing unrelated
siblings to advance.

The design preserves strict gates while making their scope precise. It introduces schema-2 typed
edges, explicit gate profiles, contract maturity, atomic planning groups, semantic revision
snapshots, explicit releases, and a lossless schema-1 compatibility and upgrade path.

## Document Index

| # | Document | Description |
|---|---|---|
| AR | [Ambiguity Register](00-ambiguity-register.md) | Approved product and architecture decisions |
| 00 | [Index](00-index.md) | Overview and navigation |
| 01 | [Requirements](01-requirements.md) | Authoritative feature requirements and scope |
| 02 | [Current State](02-current-state.md) | Existing behavior, gaps, and risks |
| 03-01 | [Graph Schema](03-01-graph-schema.md) | Schema-2 nodes, edges, identities, and groups |
| 03-02 | [Readiness Engine](03-02-readiness-engine.md) | Gate profiles, closure, diagnostics, and releases |
| 03-03 | [Migration and Invalidation](03-03-migration-and-invalidation.md) | Schema compatibility, upgrades, and stale propagation |
| 03-04 | [Workflow Integration](03-04-workflow-integration.md) | Skill, roadmap, documentation, and release integration |
| 07 | [Testing Strategy](07-testing-strategy.md) | Specification cases and verification |
| 99 | [Execution Plan](99-execution-plan.md) | Ordered implementation checklist |

## Quick Reference

### Usage Examples

```bash
python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness \
  --root . --gate plan --feature accounting --target RD-AP-001

python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness \
  --root . --gate execution --target compiler/PLAN-FRONTEND-CORE

python3 "${PLUGIN_ROOT}/scripts/codeops_state.py" readiness \
  --root . --gate release --target portfolio/RELEASE-2027.1
```

### Key Decisions

The governing decisions are AR-1 through AR-14 in the
[Ambiguity Register](00-ambiguity-register.md).

## Related Files

- `scripts/codeops_state.py`
- `schemas/traceability.schema.json`
- `tests/conformance/test_state.py`
- `tests/fixtures/state-*`
- `references/artifacts/traceability.md`
- `skills/make-requirements/`
- `skills/preflight/`
- `skills/make-plan/`
- `skills/exec-plan/`
- `skills/roadmap/`
- `skills/upgrade-plan/`
- `docs/`
