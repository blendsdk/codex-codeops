# Port Ambiguity Register

> **Gate rule:** No implementation phase affected by an open material item may begin until that item is resolved or explicitly deferred with recorded risk.

## Open decisions

None. The native Windows support decisions passed the requirements ambiguity
gate on 2026-08-06.

## Resolved Windows support decisions

| ID | Category | Ambiguity / gap | Options presented | User decision | Status |
|---|---|---|---|---|---|
| AR-015 | Scope | Which Codex surfaces must pass before CodeOps claims native Windows support? | Native CLI only / native CLI plus Windows desktop app | Fully certify the native CLI and smoke-test installation plus a representative workflow in the Windows desktop app. | ✅ Resolved |
| AR-016 | Compatibility | Which Windows and Python versions form the initial supported matrix? | Windows 11 with Python 3.10+ / a broader Windows or historical Python 3 matrix | Support Windows 11 initially. Require native Python 3.10 or newer without a patch pin. | ✅ Resolved |
| AR-017 | Behavior | How often must the Windows prerequisite gate run? | Every skill invocation / once per session plus recheck before mutation | Check once per session and recheck mutation-sensitive prerequisites immediately before project writes. | ✅ Resolved |
| AR-018 | Filesystem | Which workspace/filesystem boundary is certified in the first Windows release? | Trusted fixed local NTFS workspace without reparse points / broader local, removable, reparse, UNC, and network filesystems | Certify a trusted fixed local NTFS workspace where every existing component from the workspace root through each mutation target is reparse-free. Removable, reparse-backed, UNC, and network workspaces remain unsupported until separately certified. | ✅ Resolved |
| AR-019 | Security | Does an operational but unelevated native Codex sandbox block CodeOps? | Warn and continue / block until elevated sandbox works | Warn and continue when the supported unelevated native Codex sandbox is operational. | ✅ Resolved |
| AR-020 | Verification | What native-Windows evidence is required beyond GitHub Actions? | CI only / CI plus a real installed-plugin workflow on Windows 11 | Require Windows CI plus a real installed-plugin workflow on native Windows 11. | ✅ Resolved |
| AR-021 | Runtime | May native-Windows CodeOps depend on Git Bash when it does not use WSL? | Native PowerShell/Python only / Git Bash may remain a runtime dependency | Use native PowerShell and Python; Git for Windows is required but Git Bash is not a runtime dependency. | ✅ Resolved |

### Confirmed Windows constraints

- WSL may be installed and enabled. Its presence is not a failure condition.
- CodeOps must never invoke `wsl.exe`, launch a WSL distribution, translate paths through `/mnt`,
  or depend on WSL for any workflow.
- If CodeOps is actually executing inside WSL, it must stop before project mutation and direct the
  user to launch Codex natively on Windows.
- CodeOps must verify native Python 3.10 or newer by executing a version probe before
  project mutation. Missing or unsupported Python stops the workflow; CodeOps never installs it
  automatically.
- CodeOps must check its Windows-specific prerequisites before proceeding.
- The initial Windows threat boundary assumes the current local developer account and processes it
  deliberately launches are trusted. CodeOps still rejects unsafe names, path escapes, aliases,
  and reparse-backed workspace paths before mutation.

## Earlier resolved decisions

| ID | Resolution | Basis |
|---|---|---|
| AR-011 | The Codex port lives in `/home/gevik/workdir/github/claude-codeops/codex`; the Claude source remains unchanged during initial development. | User-approved placement and isolation requirement. |
| AR-012 | Project/portfolio tracking is a required first-class feature, not an optional follow-up. | Explicit user direction. |
| AR-013 | Recursive ambiguity elimination must meet or beat the Claude edition; simplification may remove duplication but not specification rigor. | Explicit user direction and core product purpose. |
| AR-014 | Initial planning must precede implementation because this is a crown-jewel system with high regression cost. | Explicit user direction and CodeOps' own governing method. |
| AR-001 | The Codex edition is an independent repository at `git@github.com:blendsdk/codex-codeops.git`, with its own history, releases, CI, and installable distribution. Shared-source extraction may be reconsidered only after the Codex design stabilizes. | Explicit product-owner decision; repository created and local workspace connected. |
| AR-002 | Linux with Bash and Python 3 is the tested CLI beta host. macOS compatibility is expected but not release-tested; Windows is not supported. | Platform claims now match retained evidence instead of POSIX assumptions. |
| AR-003 | Both flat and nested layouts remain readable; migration to the nested layout is preview-first, explicit, and idempotent. | Preserves existing projects without making destructive migration automatic. |
| AR-004 | Codex uses schema-1 traceability/config artifacts plus a lossless migration path from supported Claude layouts. Human-readable artifacts remain portable. | Enables stronger typed traceability while preserving project continuity. |
| AR-005 | Codex CLI is the release-critical beta surface. Desktop/IDE consumption may use the same marketplace, but is not a release claim until independently exercised. | The user authorized implementation from the CLI repository and all retained live evidence is CLI evidence. |
| AR-006 | Deterministic reports and roadmap counters may be derived from authoritative artifacts; generated views must be reproducible and drift-checkable. | Implemented state and roadmap engines keep authored decisions authoritative. |
| AR-007 | Legacy telemetry is removed. Optional metrics are local, content-free, enumerated, and disabled by default. | Minimizes privacy surface while retaining measurable workflow outcomes. |
| AR-008 | Strict complex-project gates are the default for features; small fixes route to a lightweight task lane without weakening feature gates. | Preserves the crown-jewel workflow without forcing full RD ceremony onto trivial work. |
| AR-009 | Checked-in routing is capability based and contains no model names. The runtime/user chooses available models. | Prevents model churn from aging project policy. |
| AR-010 | Complete dynamic dispatch packets are the correctness baseline. Optional project-local TOML agents may be installed behind managed markers. | Works without plugin-root agent discovery and permits local optimization safely. |

## Working defaults pending resolution

None.
