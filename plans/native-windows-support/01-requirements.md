# Requirements: Native Windows Support

> **Document**: 01-requirements.md
> **Parent**: [Index](00-index.md)
> **Source**: [RD-022 and RD-023](../codex-port/01-requirements.md#rd-022--native-windows-runtime) — the OWNING requirements document

## Scope of this plan (delta view)

### In this plan

- RD-022: native Windows 11 operation for every shipped core workflow without WSL or Git Bash.
- RD-022: deterministic Python 3.10+ and Windows prerequisite enforcement at mutating boundaries.
- RD-022: portable process ownership, atomic writes, recovery, paths, migration, roadmap,
  worktree, agent, outcome, hook, and utility behavior.
- RD-023: native Windows CI, retained installed-plugin evidence, and Windows desktop smoke evidence.

### Deferred / out of this plan

- Removable, reparse-backed, UNC, and network workspaces remain outside the certified boundary
  under governing AR-018.
- Windows 10 and future Windows releases require separate certification.
- Automatic prerequisite installation is prohibited rather than deferred.

## Plan-local decisions

| Decision | Chosen | AR Ref |
|---|---|---|
| Cross-platform implementation owner | Python modules with thin native host launchers | AR-2 |
| Prerequisite result and enforcement contract | Session attestation plus before-write recheck; closed JSON/exit contract | AR-5, AR-6 |
| State and path compatibility | Versioned owner records, canonical `/` paths, safe legacy reads | AR-9, AR-11 |
| Automation scope | Runtime and repository verification entry points | AR-8, AR-14 |

## Acceptance Criteria

1. [ ] No shipped Windows workflow requires or invokes Bash, Git Bash, `wsl.exe`, a WSL
   distribution, or `/mnt` path translation.
2. [ ] Windows preflight requires Python 3.10+, a trusted fixed local NTFS workspace, and rejects
   any existing reparse component from the workspace root through a mutation target.
3. [ ] GitHub issue #2 is closed by native owner-identity and recovery behavior that preserves
   existing Linux semantics.
4. [ ] Native Windows 11 CI and retained Windows 11 CLI/desktop evidence satisfy RD-023.
5. [ ] Ubuntu behavior and every confirmed repository verification check remain green.
