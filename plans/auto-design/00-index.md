# Auto Design Implementation Plan

> **Feature**: Delegated, quality-first technical design authority
> **Status**: Planning Complete
> **Created**: 2026-07-23
> **CodeOps Artifact Schema**: 1

## Overview

Add invocation-scoped `--auto-design` to CodeOps' decision-producing workflows. The mode preserves
zero ambiguity, specification-first execution, verification, review, and action permissions while
changing the eligible technical decision owner from the user to CodeOps. Decisions remain
evidence-grounded, adversarially hardened, durable, and reopenable.

## Document Index

| # | Document | Description |
|---|---|---|
| AR | [Ambiguity Register](00-ambiguity-register.md) | Authority and scope decisions |
| 00 | [Index](00-index.md) | Overview and navigation |
| 01 | [Requirements](01-requirements.md) | Feature contract |
| 02 | [Current State](02-current-state.md) | Existing workflow analysis |
| 03 | [Authority Policy](03-01-authority-policy.md) | Shared normative design |
| 04 | [Workflow Integration](03-02-workflow-integration.md) | Skill behavior |
| 07 | [Testing Strategy](07-testing-strategy.md) | Specification cases |
| 99 | [Execution Plan](99-execution-plan.md) | Ordered implementation |

## Quick Reference

```text
make-plan compiler-optimizer --auto-design
exec-plan compiler-optimizer --auto-design --auto-commit
```

`--auto-design` delegates eligible technical judgment. It never implies `--auto-commit` or any
other action permission. (AR-1, AR-5, AR-9)
