# Ambiguity Register: Native Windows Support

> **Status**: ✅ GATE PASSED — all 14 items resolved
> **Last Updated**: 2026-08-06 17:09 CEST

| # | Category | Ambiguity / Gap | Options Presented | User Decision | Status |
|---|---|---|---|---|---|
| AR-1 | Naming | What plan path owns the complete Windows effort? | `plans/native-windows-support/` / another slug | Use `plans/native-windows-support/`. | ✅ Resolved |
| AR-2 | Architecture | Should Windows support duplicate each Bash workflow in PowerShell or move reusable behavior to one cross-platform engine? | Authoritative Python modules with thin host launchers / parallel Bash and PowerShell algorithms | Use authoritative Python 3 modules. Retain thin Bash launchers where Unix compatibility needs them and add thin native PowerShell launchers where Python cannot bootstrap itself. | ✅ Resolved |
| AR-3 | Runtime | How does Windows check Python when Python may be absent? | Native PowerShell bootstrap / depend on Git Bash or WSL | Use a signed-reviewable PowerShell bootstrap that probes `py -3` and then `python`, accepts any functional Python 3.x, never installs it, and blocks mutation when unavailable. | ✅ Resolved |
| AR-4 | WSL | How should an installed WSL feature affect native Windows readiness? | Ignore installed WSL but block actual WSL execution / reject machines with WSL installed | Ignore whether WSL is installed. Never invoke or delegate to WSL; block only when CodeOps is actually executing inside WSL. | ✅ Resolved |
| AR-5 | Prerequisites | How are prerequisite results shared and enforced? | Session attestation plus write-time rechecks / every command performs the full probe | The SessionStart hook writes a session-scoped attestation under `PLUGIN_DATA`; every mutating entry point rechecks mutation-sensitive conditions before writes and performs the full check when no valid attestation exists. | ✅ Resolved |
| AR-6 | Contract | What machine-readable prerequisite contract is stable? | Closed JSON result with stable check codes / prose-only output | Emit a versioned closed JSON result with `READY`, `WARNING`, or `BLOCKED`, ordered check records, and actionable messages. Exit 0 for READY/WARNING, 2 for BLOCKED, and 1 for malformed input or internal failure. | ✅ Resolved |
| AR-7 | Compatibility | Should CodeOps pin a Codex version for Windows? | Probe required native capabilities / guess a minimum version | Probe the required plugin, hook, native sandbox, and command capabilities. Record the certified Codex version in evidence, but do not hardcode a speculative minimum. | ✅ Resolved |
| AR-8 | Scope | Which shell-dependent utilities are in the port? | Every shipped runtime and repository verification workflow / runtime scripts only | Port every shipped CodeOps runtime utility and the repository verification orchestration to native Python/PowerShell entry points; Bash remains a Unix compatibility launcher, not a Windows dependency. | ✅ Resolved |
| AR-9 | Concurrency | How is process ownership represented across Linux and Windows? | Versioned backend-specific identity / reinterpret Linux fields on Windows | Use a versioned owner record with an explicit backend discriminator. Read existing Linux `{pid,startTicks,bootId}` records compatibly; use native Windows process creation time and boot/session identity, failing closed when absence cannot be proven. | ✅ Resolved |
| AR-10 | Filesystem | How should transient Windows sharing violations affect atomic writes? | Bounded retry for allowlisted transient errors / immediate failure | Retry only allowlisted Windows sharing/access violations within a documented bounded budget, then retain recovery state and fail closed. Never retry validation, permission-policy, or path-safety failures. | ✅ Resolved |
| AR-11 | Paths | What durable path and generated-name rules apply? | Canonical POSIX-relative storage with legacy reads / host-native serialized separators | Serialize project-relative durable paths with `/`, accept legacy `\` records only when they resolve safely on Windows, and reject reserved device names, trailing spaces/dots, absolute paths, and traversal before writes. Existing invalid state blocks and is never silently rewritten. | ✅ Resolved |
| AR-12 | Certification | What automated matrix is sufficient? | Ubuntu plus one current Python 3 on native Windows CI / multi-version Python matrix | Keep Ubuntu regression coverage and add native Windows CI using one current Python 3.x. Do not add a minor-version matrix. | ✅ Resolved |
| AR-13 | Evidence | What evidence closes the Windows claim? | CI plus real Windows 11 installed-plugin evidence and desktop smoke / CI alone | Require CI plus retained, version-matched native Windows 11 CLI installed-plugin evidence and a Windows desktop installation/representative-workflow smoke test before claiming support. | ✅ Resolved |
| AR-14 | Verification | Which repository commands are the authoritative full gate? | All five `AGENTS.md` commands / a narrower subset | Use all five commands from `AGENTS.md`; provide native Python/PowerShell entry points that prove the same checks on Windows. | ✅ Resolved |

## Resolution Notes

The user explicitly accepted the complete recommendation set after the issue analysis and Windows
scope expansion. AR-3 and AR-4 preserve the clarified boundary: WSL may be installed, but CodeOps
does not use it; Python is any functional major version 3 rather than one exact release.

The confirmed repository gate is:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

On Windows, equivalent native launchers must execute the same underlying checks without Bash,
Git Bash, or WSL (AR-2, AR-8, AR-14).
