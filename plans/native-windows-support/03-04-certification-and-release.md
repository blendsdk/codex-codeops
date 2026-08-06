# Certification and Release: Native Windows Support

> **Document**: 03-04-certification-and-release.md
> **Parent**: [Index](00-index.md)

## Overview

This component owns the evidence boundary for any Windows support claim. Passing unit tests alone
does not change the documented platform status.

## Architecture

### Current Architecture

CI has one Ubuntu job with Python 3.12 and invokes five Bash gates. Installation evidence is not a
native Windows installed-plugin run, and documentation explicitly says Windows is unsupported.

### Proposed Changes

Use a two-platform CI matrix or equivalent independent jobs: Ubuntu regression and
`windows-latest`, each with one current Python 3.x. Windows invokes the portable verification
owner through native PowerShell/Python only. No Python minor-version matrix is added (AR-12,
AR-14).

Retain a versioned evidence manifest for the real Windows 11 CLI run and a separate desktop smoke
record. Documentation and release metadata switch from unsupported to supported only in the task
that validates those records against the exact plugin version and commit (AR-13).

## Implementation Details

### CI Contract

The native Windows job:

1. checks out with a path that includes a space;
2. installs one current Python 3.x and development dependencies;
3. proves the PowerShell bootstrap selects Python 3;
4. runs all native specification and implementation tests;
5. runs the portable equivalents of all five AR-14 gates;
6. asserts no command line contains `bash`, `wsl`, `/mnt`, or a Git Bash executable;
7. uploads only test reports and synthetic evidence, never project content (AR-4, AR-12, AR-14).

Ubuntu continues to invoke the public shell launchers and the same Python-owned checks, proving
launcher compatibility (AR-2, AR-12).

### Evidence Manifest

`tests/evidence/windows-native-<version>.json` follows a JSON Schema and records:

- plugin semantic version and commit;
- Windows edition/build and native architecture;
- Codex CLI/desktop version used for certification;
- Python major/minor observed (evidence only, not a support pin);
- Git for Windows version;
- sandbox status and warning classification;
- plugin installation/enablement and hook review/trust results;
- each required workflow scenario, command class, result, timestamp, and sanitized artifact hash;
- explicit assertions that WSL/Git Bash were not invoked;
- reviewer identity/provenance appropriate to repository evidence policy.

The CLI scenarios cover installation, enablement, SessionStart/preflight, requirements, planning,
preflight audit, execution-state transition and recovery, layout migration, roadmap sync/compact,
worktree operation, agent check/install, outcomes, and the full verification gate. The desktop
record covers plugin installation/enablement, hook review, preflight, and one representative
requirements-to-plan workflow (AR-13).

Evidence validation rejects missing fields, mismatched version/commit, failed scenarios,
unsupported Windows, non-native execution, or stale schema. It does not infer a pass from prose
(AR-13).

### Documentation and Release Gate

README, installation, troubleshooting, migration, tutorial, changelog, plugin metadata, and
release notes describe:

- Windows 11, native Codex, PowerShell, Git for Windows, and Python 3.x prerequisites;
- WSL may be installed but CodeOps never uses it;
- actual WSL execution blocks before mutation;
- prerequisite statuses/remediation and the local-filesystem boundary;
- the exact native verification commands.

The support claim update and semantic release decision occur only after evidence validation.
Version selection follows the repository SemVer rules and is not predetermined by this plan
(AR-13).

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Windows CI fails while Ubuntu passes | Keep Windows unsupported and block release claim | AR-12, AR-13 |
| Real-host evidence is absent or stale | Keep Windows unsupported; report exact missing scenario | AR-13 |
| Evidence version/commit differs from release candidate | Reject evidence for that candidate | AR-13 |
| Desktop smoke cannot approve/load hooks | Keep desktop support claim blocked; CLI evidence remains informative only | AR-13 |
| A command invokes WSL or Git Bash | Certification fails regardless of functional result | AR-4, AR-13 |
| New exact Python minor is proposed as prerequisite | Reject documentation/config change; support remains Python major 3 | AR-3, AR-12 |

## Testing Requirements

- Specification tests cover ST-46–ST-54.
- Evidence schema tests cover missing, stale, mismatched, non-native, and prohibited-runtime data.
- CI configuration tests assert native command paths and one Python 3.x per platform.
- Documentation checks keep Windows unsupported until valid retained evidence exists, then require
  all declared surfaces to agree.
