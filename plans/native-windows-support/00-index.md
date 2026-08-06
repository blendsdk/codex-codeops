# Native Windows Support Implementation Plan

> **Feature**: Complete native Windows 11 operation without WSL or Git Bash dependencies
> **Status**: Planning Complete
> **Created**: 2026-08-06
> **Implements**: RD-022, RD-023
> **CodeOps Artifact Schema**: 1

## Overview

This plan makes every shipped CodeOps workflow operate through native Codex on Windows 11. It
replaces Bash-only runtime paths with a shared Python control layer and native PowerShell
bootstrap, while keeping Unix compatibility and the existing safety gates intact.

The effort includes the narrow state-transition failure tracked by GitHub issue #2, but treats it
as one part of the larger platform contract. Windows support is not claimed until automated native
Windows tests and retained real-host evidence satisfy RD-023.

## Document Index

| # | Document | Description |
|---|---|---|
| AR | [Ambiguity Register](00-ambiguity-register.md) | Approved scope and architecture decisions |
| 00 | [Index](00-index.md) | Overview and navigation |
| 01 | [Requirements](01-requirements.md) | RD-022/RD-023 delta view |
| 02 | [Current State](02-current-state.md) | Existing platform assumptions and gaps |
| 03-01 | [Runtime Preflight and Hooks](03-01-runtime-preflight-and-hooks.md) | Python bootstrap, WSL exclusion, prerequisites, and hook contract |
| 03-02 | [Portable Control Layer](03-02-portable-control-layer.md) | Cross-platform utilities and host launchers |
| 03-03 | [State and Filesystem Safety](03-03-state-and-filesystem-safety.md) | Windows ownership, atomicity, paths, and recovery |
| 03-04 | [Certification and Release](03-04-certification-and-release.md) | CI, real-host evidence, documentation, and claim gate |
| 07 | [Testing Strategy](07-testing-strategy.md) | Specification cases and verification |
| 99 | [Execution Plan](99-execution-plan.md) | Ordered implementation checklist |

## Quick Reference

### Expected Windows entry

```powershell
pwsh -NoProfile -File "$env:PLUGIN_ROOT\scripts\codeops-windows-preflight.ps1"
python "$env:PLUGIN_ROOT\scripts\codeops_state.py" status --root .
```

The launcher selection and result contract are owned by
[03-01](03-01-runtime-preflight-and-hooks.md); the final command surface is implemented and tested
before these examples become user documentation.

### Key Decisions

The governing decisions are AR-1 through AR-14 in the
[Ambiguity Register](00-ambiguity-register.md).

## Related Files

- `hooks/hooks.json`
- `scripts/codeops_windows_preflight.py`
- `scripts/codeops-windows-preflight.ps1`
- `scripts/codeops_state_lib/`
- `scripts/codeops_migrate.py`
- `scripts/codeops_roadmap.py`
- `scripts/codeops_worktree.py`
- `scripts/codeops_verify.py`
- `bin/codeops-worktree`
- `tests/conformance/`
- `.github/workflows/ci.yml`
- `docs/`
- `README.md`
