# Portable Control Layer: Native Windows Support

> **Document**: 03-02-portable-control-layer.md
> **Parent**: [Index](00-index.md)

## Overview

This component moves reusable CodeOps behavior out of Bash into importable Python modules. Host
launchers remain intentionally thin so Unix and Windows execute one behavioral implementation.

## Architecture

### Current Architecture

Migration, roadmap synchronization/compaction, verification orchestration, hooks, and worktree
management contain behavior in Bash, including embedded Python fragments. Their shell parsing,
exit codes, and direct filesystem changes form public workflow contracts that must be preserved.

### Proposed Changes

Create focused Python entry modules for migration, roadmap, worktree, hooks, and repository
verification. Existing `.sh` files become argument-forwarding launchers that locate Python 3 on
Unix and execute the authoritative module. Windows uses Python directly after 03-01 preflight or a
minimal PowerShell launcher where bootstrap is required (AR-2, AR-8).

No launcher invokes a shell with user-controlled command text. Python uses `subprocess.run()` with
argument arrays through one small shared command adapter, closed option parsing, canonical paths,
and explicit working directories. The adapter can append sanitized command/exit metadata to an
evidence sink selected by the certification runner; ordinary runs do not persist a trace. Git
for Windows is invoked as `git`, never through Git Bash or WSL (AR-4).

## Implementation Details

### Modules and Public Commands

| Module | Commands | Existing owner replaced | AR Ref |
|---|---|---|---|
| `scripts/codeops_migrate.py` | `preview`, `apply` | `codeops-migrate.sh` behavior | AR-2, AR-8 |
| `scripts/codeops_roadmap.py` | `sync`, `compact` with `--check`/`--write` | roadmap shell scripts | AR-2, AR-8 |
| `scripts/codeops_worktree.py` | `new`, `list`, `remove`, `help` | `bin/codeops-worktree` | AR-2, AR-8 |
| `scripts/codeops_hooks.py` | `session-context`, `marker-guard` | hook shell scripts | AR-2, AR-5 |
| `scripts/codeops_verify.py` | named checks and `all` | five shell verification orchestrators | AR-8, AR-14 |

Each module exposes `main(argv: Sequence[str] | None = None) -> int` and small importable domain
functions. Public functions and non-trivial internal invariants receive the repository-required
Python documentation. Files are split by concern before they become large; existing state modules
remain separate.

Every command with a write/apply/remove mode calls the shared Windows mutation preflight after
closed argument validation and immediately before its first mutation. Read/check/preview modes do
not claim mutation readiness. Shared atomic writers repeat filesystem check 10 at the final write.

### Compatibility Launchers

The retained Unix launchers contain only strict-mode setup, interpreter resolution, and `exec`
with unchanged arguments. They do not own parsing or mutations. Exit statuses and stdout/stderr
classes are preserved by characterization tests (AR-2).

Windows examples and skill commands use the interpreter selected by preflight. Skills must not
hardcode a minor version. They may call the resolved executable recorded in the active
attestation, or invoke the PowerShell bootstrap for the first call (AR-3, AR-5).

### Migration

The Python layout migrator preserves preview-before-apply, clean-worktree checks, explicit
authorization, `git mv` semantics, marker-last behavior, path containment, idempotence, and
recoverable failure. Its `apply` boundary runs mutation preflight, rejects unsupported filesystems
through 03-01, and uses 03-03 path/write primitives (AR-8, AR-11).

### Roadmap

One module owns parsing, derivation, rendering, compaction, `--check`, and write behavior for flat
and nested layouts. Dates are injected or derived through one clock interface for deterministic
tests. Write/compact modes run mutation preflight; writes use 03-03 atomic primitives (AR-2, AR-10).

### Worktrees

The Python CLI preserves the existing command surface while using Git porcelain output through
argument arrays. Topic/branch/path validation uses the shared Windows-safe name and containment
rules. `new` and `remove` run mutation preflight before Git/filesystem changes. `--launch` starts
native `codex` on Windows and never delegates through a shell, Git Bash, or WSL (AR-4, AR-11).

### Repository Verification

`codeops_verify.py` is the portable owner of the five logical gates named in AR-14. The existing
shell filenames remain Unix launchers. A native PowerShell wrapper exposes the same five names or
`all`; CI may call the Python dispatcher directly. Check implementations reuse Python modules and
fixtures rather than transliterating Bash into PowerShell (AR-2, AR-8, AR-14).

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Launcher cannot find Python 3 | Unix reports the existing dependency failure; Windows uses 03-01 BLOCKED result | AR-3, AR-6 |
| Unknown option or malformed input | Closed parser exits 2 without mutation | AR-6, AR-11 |
| Git executable missing/non-native on Windows | Preflight blocks; command also fails closed if state changed after preflight | AR-3, AR-5 |
| Path escapes project or targets invalid Windows name | Reject before preview/write/Git invocation | AR-11 |
| Ported output differs from characterized contract | Treat as regression unless an owning spec explicitly changes it | AR-2 |
| Verification subcheck fails | Continue only where needed to report independent failures; aggregate nonzero and preserve diagnostic order | AR-14 |

## Testing Requirements

- Specification tests own ST-31–ST-38. Phase 4 reuses ST-35 and ST-36 as workflow regressions and
  owns ST-39–ST-40.
- Characterization runs compare Python commands with retained Unix behavior on approved fixtures.
- Windows CI calls only native Python/PowerShell entry points.
- Security tests use hostile names, arguments, environment values, and paths; no test relies on
  `shell=True`.
