# Codex Port Execution Plan

> **Status:** Planning
> **Progress:** 0/57 tasks
> **Execution prohibition:** Do not begin implementation phases affected by open material items in `00-ambiguity-register.md`.

## Phase 0 — Validate product decisions

- [ ] 0.1 Review this plan with the product owner and record corrections.
- [ ] 0.2 Resolve initial release surfaces and platform support (AR-002, AR-005).
- [ ] 0.3 Resolve artifact compatibility and legacy-layout policy (AR-003, AR-004).
- [ ] 0.4 Resolve telemetry and strict-profile policy (AR-007, AR-008).
- [ ] 0.5 Resolve model/agent distribution policy through bounded prototypes (AR-009, AR-010).
- [ ] 0.6 Confirm repository protections, licensing, release tags, and CI policy for the independent repository (AR-001 resolved).
- [ ] 0.7 Run requirements preflight and close all critical/major findings.

**Verify:** Requirements gate G1 passes and no architecture-affecting ambiguity remains open.

## Phase 1 — Codex platform spikes

- [ ] 1.1 Scaffold the minimum valid `.codex-plugin/plugin.json` and local marketplace entry.
- [ ] 1.2 Prove skill discovery, explicit invocation, implicit invocation, and referenced-file loading.
- [ ] 1.3 Capture real hook payloads for lifecycle, patch, shell, and subagent events.
- [ ] 1.4 Prove SessionStart standards injection and hook trust/update behavior.
- [ ] 1.5 Prove marker protection against Codex `apply_patch` and document enforcement limits.
- [ ] 1.6 Prototype project-local TOML agents versus dynamic role packets.
- [ ] 1.7 Verify behavior on every release-critical Codex surface.
- [ ] 1.8 Write spike decisions into the architecture and rerun specification preflight.

**Verify:** Every Codex integration assumption has an executable fixture or is explicitly bounded as unsupported.

## Phase 2 — Artifact schema and deterministic core

- [ ] 2.1 Define versioned schemas for requirements, ambiguities/decisions, specifications, criteria, tests, tasks, findings, and evidence.
- [ ] 2.2 Define lifecycle and readiness state machines with valid transitions.
- [ ] 2.3 Implement artifact discovery and layout resolution.
- [ ] 2.4 Implement bidirectional traceability validation.
- [ ] 2.5 Implement ambiguity/gate validation and downstream invalidation.
- [ ] 2.6 Implement deterministic readiness reports.
- [ ] 2.7 Implement durable execution-state transitions and recovery inspection.
- [ ] 2.8 Port and enhance roadmap derivation, review, compact, and archive behavior.
- [ ] 2.9 Add hostile, corrupt, stale, and interrupted-state fixtures.

**Verify:** T2 suite passes; generated views contain no independent authoritative state.

## Phase 3 — Requirements and planning workflows

- [ ] 3.1 Port shared standards, layout conventions, zero-ambiguity rules, and recommendation hardening.
- [ ] 3.2 Port requirements discovery and add/review modes.
- [ ] 3.3 Port reverse requirements, confidence classification, and bug/feature triage.
- [ ] 3.4 Port relentless ambiguity interviewing with durable resume state.
- [ ] 3.5 Add adaptive domain-lens selection and domain reference packs.
- [ ] 3.6 Port plan creation, templates, current-state analysis, and specification-first ordering.
- [ ] 3.7 Integrate traceability and readiness proofs into planning.
- [ ] 3.8 Port preflight with deterministic/semantic separation and dynamic review teams.
- [ ] 3.9 Run requirements, specification, and plan gates on the port itself.

**Verify:** A seeded compiler scenario reaches G3 with every injected material ambiguity discovered and resolved.

## Phase 4 — Execution and review workflows

- [ ] 4.1 Port commit modes and update-before-verify semantics.
- [ ] 4.2 Port specification-test authoring and immutable-oracle enforcement.
- [ ] 4.3 Implement capability-based executor dispatch with safe inline fallback.
- [ ] 4.4 Implement risk-derived independent review teams.
- [ ] 4.5 Port verification-output capture and evidence attachment.
- [ ] 4.6 Implement runtime ambiguity reopening and downstream invalidation.
- [ ] 4.7 Implement session recovery from artifacts, Git state, logs, and findings.
- [ ] 4.8 Port guarded commit/push behavior without making commits implicit.

**Verify:** T6 interruption/recovery matrix passes without conversation context.

## Phase 5 — Setup, migration, tracking, and utilities

- [ ] 5.1 Build Codex-native project setup for `AGENTS.md`, CodeOps config, artifacts, and optional agents.
- [ ] 5.2 Implement preview-first migration from supported Claude/legacy CodeOps layouts.
- [ ] 5.3 Port technical documentation workflows and architecture traceability.
- [ ] 5.4 Port GitHub issue workflows as a Codex skill.
- [ ] 5.5 Generalize the worktree utility to Codex and selected platforms.
- [ ] 5.6 Implement optional outcome metrics if AR-007 retains them.
- [ ] 5.7 Complete portfolio tracking, drift checks, and cross-session next-action reporting.

**Verify:** Migration fixtures are idempotent and recoverable; tracking reconstructs exact state from disk.

## Phase 6 — Product validation and release

- [ ] 6.1 Complete static/plugin/hook/skill conformance suites.
- [ ] 6.2 Pass compiler, financial, and web application adversarial scenarios.
- [ ] 6.3 Run matched Claude-versus-Codex parity evaluations.
- [ ] 6.4 Resolve every safety/correctness regression before optimizing cost or convenience.
- [ ] 6.5 Validate installation, update, disable, uninstall, and hook trust flows.
- [ ] 6.6 Write and validate the root `README.md` against RD-021, including tested install, quick-start, update, disable, and uninstall commands.
- [ ] 6.7 Complete tutorials, reference docs, migration guide, and troubleshooting.
- [ ] 6.8 Pilot on a real complex project milestone and incorporate findings.
- [ ] 6.9 Pass final readiness and independent release review.

**Verify:** The 1.0 release gate in `07-testing-strategy.md` passes with retained evidence.
