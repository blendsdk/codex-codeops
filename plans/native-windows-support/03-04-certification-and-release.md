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
the explicit GitHub-hosted `windows-11-arm` image, each with one Python 3.10+ interpreter. Windows
invokes the portable verification owner through native PowerShell/Python only. Windows Server is
not a CI or support target, and no Python minor-version matrix is added (AR-12,
AR-14).

Retain a versioned evidence manifest for the real Windows 11 CLI run and a separate desktop smoke
record. Documentation and release metadata switch from unsupported to supported only in the task
that validates those records against the exact plugin version and commit (AR-13).

## Implementation Details

### CI Contract

The native Windows job:

1. checks out with a path that includes a space;
2. asserts the runner reports Windows 11, then installs one Python 3.10+ and development dependencies;
3. proves the PowerShell bootstrap selects Python 3.10+;
4. runs all native specification and implementation tests;
5. runs the portable equivalents of all five AR-14 gates;
6. inspects the shared subprocess trace and asserts no executable/argument invokes `bash`,
   `wsl`, `/mnt`, or a Git Bash executable;
7. uploads only test reports and synthetic evidence, never project content (AR-4, AR-12, AR-14).

Ubuntu continues to invoke the public shell launchers and the same Python-owned checks, proving
launcher compatibility (AR-2, AR-12).

### Evidence Manifest

`scripts/capture_windows_evidence.py` owns the CLI capture procedure. It installs the exact packed
plugin candidate, sets a private evidence sink consumed by the shared subprocess adapter, runs the
closed scenario list with argument arrays, sanitizes outputs through an allowlist, and writes:

- `tests/evidence/windows-native-<version>.json` — the signed-off manifest;
- `tests/evidence/windows-native-<version>/commands.jsonl` — executable, normalized arguments,
  exit class, scenario ID, and timestamp for each observed command; and
- one sanitized JSON result per scenario, named by scenario ID and referenced by SHA-256 from the
  manifest.

The capture command refuses a dirty repository, a candidate whose manifest version/commit does not
match HEAD, an output field outside the sanitization allowlist, or a missing command trace. The
desktop smoke remains a structured reviewer-attested record because desktop interaction is manual;
it records reviewer GitHub identity, UTC timestamp, candidate hash, Codex version, and each observed
checklist result. It never substitutes for the CLI command trace.

The manifest follows a JSON Schema and records:

- plugin semantic version and commit;
- Windows edition/build and native architecture;
- Codex CLI/desktop version used for certification;
- Python major/minor observed and confirmation that it is at least 3.10;
- Git for Windows version;
- sandbox status and warning classification;
- plugin installation/enablement and hook review/trust results;
- each required workflow scenario, command class, result, timestamp, and sanitized artifact hash;
- explicit assertions that WSL/Git Bash were not invoked;
- reviewer GitHub identity, capture-command version, and exact supporting-record hashes.

The CLI scenarios cover installation, enablement, SessionStart/preflight, requirements, planning,
preflight audit, execution-state transition and recovery, layout migration, roadmap sync/compact,
worktree operation, agent check/install, outcomes, and the full verification gate. The desktop
record covers plugin installation/enablement, hook review, preflight, and one representative
requirements-to-plan workflow (AR-13).

Evidence validation recomputes every supporting-record hash and rejects missing records, missing
command coverage, mismatched version/commit/candidate hash, failed scenarios, unsupported Windows,
non-native execution, prohibited executables/arguments, or stale schema. It does not infer a pass
from prose or a schema-valid manifest without its supporting records (AR-13).

### Documentation and Release Gate

README, installation, troubleshooting, migration, tutorial, changelog, plugin metadata, and
release notes describe:

- Windows 11, native Codex, PowerShell, Git for Windows, Python 3.10+, and fixed local NTFS prerequisites;
- WSL may be installed but CodeOps never uses it;
- actual WSL execution blocks before mutation;
- prerequisite statuses/remediation and the fixed-local-NTFS/reparse-free boundary;
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
| Python older than 3.10 or an exact patch pin is proposed | Reject documentation/config change; support remains Python 3.10+ without a patch pin | AR-3, AR-12 |

## Testing Requirements

- Specification tests cover ST-46–ST-54.
- Evidence schema tests cover missing, stale, mismatched, non-native, and prohibited-runtime data.
- `test_windows_certification_impl.py` covers capture sanitization, command/supporting-record hash
  binding, reviewer provenance, and validator error boundaries.
- CI configuration tests assert the explicit Windows 11 runner, native command paths, and one
  Python 3.10+ interpreter per platform.
- Documentation checks keep Windows unsupported until valid retained evidence exists, then require
  all declared surfaces to agree.
