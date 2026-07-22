# Roadmap: Widgets

> **Feature-Set**: Widgets
> **Status**: In Progress
> **Created**: 2025-01-10
> **Last Updated**: 2025-05-15 10:00
> **Progress**: 1 / 2 (50%)
> **CodeOps Artifact Schema**: 3.4.1

## Legend

⬜ Backlog · ✏️ RD Drafted · 🔎 RD Preflighted · 📋 Plan Created · 🔬 Plan Preflighted · 🔄 Executing · ✅ Done · ⛔ Blocked · ⏸️ Deferred

## Tracker

| ID | Title | RD | Plan | Stage | Status | Last Updated | Depends-on / Blocker |
|----|-------|----|------|-------|--------|--------------|----------------------|
| RD-01 | Rendering core | — | — | Done | ✅ | 2025-05-01 | — |
| RD-02 | Theme tokens | — | — | Executing | 🔄 | 2025-05-15 | Grew from a status note into a saga; blocked first on the upstream token format, then on the cascade resolution order after the palette changed, and now trails the dark-mode variant behind metering, so it reads like a changelog rather than a terse blocker note for the row. |

## Notes

- 2025-05-01: RD-01 shipped; kept a long spike write-up here about retained versus immediate mode
  that only git needs to remember now.
- 2025-05-15: RD-02 in progress; the token pipeline rewrite is described at length below and none
  of it is machine-read.
