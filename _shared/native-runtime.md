# Native Runtime and Prerequisite Contract

This file is the single owner of host-neutral Python selection and the workflow-level native
Windows prerequisite gate. A skill references this contract; it does not duplicate these rules.

## Certified interpreter

`<CODEOPS_PYTHON>` denotes one already-resolved Python 3.10-or-newer executable, invoked with an
argument array rather than a command string. Resolve it once per workflow:

- On native Windows 11, invoke `powershell.exe -NoProfile -File
  "$env:PLUGIN_ROOT/scripts/codeops-windows-preflight.ps1" -ResolvePython`, require exit 0, and
  use the single absolute path it returns.
- On Unix, resolve the existing `python3` executable and prove `sys.version_info >= (3, 10)` before
  use. This Unix rule never applies on Windows.

`<PLUGIN_ROOT>`, `<PLUGIN_DATA>`, `<PROJECT_ROOT>`, `<SESSION_ID>`, and `<TARGET>` in command
examples are data placeholders. Substitute each as one argument; never evaluate a constructed
shell command. Shipped workflow examples invoke Python as:

```text
<CODEOPS_PYTHON> <PLUGIN_ROOT>/scripts/<entrypoint>.py <arguments...>
```

Never pin a Python minor or patch version, install prerequisites automatically, or fall back to
Bash, Git Bash, WSL, a distribution executable, or `/mnt` path translation.

## Mutation defense in depth

On native Windows, every mutating skill performs this defense-in-depth check after it knows the
complete exact target set and immediately before its first project mutation:

```text
<CODEOPS_PYTHON> <PLUGIN_ROOT>/scripts/codeops_windows_preflight.py --mode mutation --entrypoint-code skill-mutation --target <TARGET> [--target <TARGET> ...] --root <PROJECT_ROOT> --plugin-root <PLUGIN_ROOT> --plugin-data <PLUGIN_DATA> --session-id <SESSION_ID>
```

Targets are absolute, unique, contained project paths passed as separate arguments. A missing
target, unavailable interpreter, exit 1, or exit 2 stops the mutation. Read-only discovery does
not claim mutation readiness. On Unix, skip this Windows-specific defense check.

This skill-level call is defense in depth only. Every shipped direct mutating command remains the
authoritative boundary and reruns its registered mutation gate immediately before its first write.
