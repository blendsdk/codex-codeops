# Complex-project quick start

This walkthrough starts a new project without skipping the ambiguity gates.

## 1. Initialize durable CodeOps state

In a new Codex thread, ask:

```text
Use the setup-codeops skill to initialize this repository in strict mode.
Preview every change before writing it.
```

Review the proposed `codeops/codeops.json`, artifact layout, and optional agent
files. Accept only the parts you want committed to the project.

## 2. Discover requirements

Give Codex the raw idea, constraints, existing notes, and known stakeholders:

```text
Use make-requirements for this system. Treat my description as seed material,
select every applicable domain lens, and keep the zero-ambiguity gate closed
until I explicitly resolve each material choice.
```

CodeOps records requirements and the ambiguity register on disk so discovery
can resume in a later thread. For an existing implementation, start with
`retro-requirements` instead.

If you want CodeOps to own eligible expert technical choices, use:

```text
Use make-requirements --auto-design for this system. Choose and record the
strongest eligible technical options. Escalate every product, risk, permission,
or other reserved-authority decision to me.
```

## 3. Build and challenge the plan

After requirements are approved:

```text
Use make-plan for RD-01. Analyze the current code, write specifications before
implementation tasks, and resolve every plan ambiguity with me.
```

Then run `preflight`. Critical and major findings reopen the affected gate; they
are not converted silently into implementation assumptions.

The same exact `--auto-design` flag may be used with `make-plan`, `preflight`, and `exec-plan`.
It does not imply `--auto-commit`; select commit behavior separately.

These workflows stay in strict scope by default and do not suggest optional product additions. To
review possible expansions without authorizing them, use:

```text
Use make-plan --explore-scope for RD-01. Keep the confirmed scope as the baseline, then present
optional additions as SE proposals so I can Keep, Defer, or Discard each one.
```

The same `--explore-scope` flag works with `preflight` and `exec-plan`. Necessary corrections and
blocking safety, correctness, or feasibility uncertainties are reported in either mode. Only an
explicit `Keep` decision turns a proposal into executable work; `--auto-design` cannot make that
decision.

## 4. Prove readiness and execute

Run the deterministic check from the project root. On Unix, use the existing `python3` command:

```bash
python3 /path/to/codeops/scripts/codeops_state.py readiness --root . \
  --gate requirements --target my-feature/RD-01
python3 /path/to/codeops/scripts/codeops_state.py readiness --root . \
  --gate execution --target my-feature/PLAN-01
```

On native Windows 11, use PowerShell and let the trusted bootstrap select Python 3.10 or newer:

```powershell
$python = & "$env:PLUGIN_ROOT\scripts\codeops-windows-preflight.ps1" -ResolvePython
& $python "$env:PLUGIN_ROOT\scripts\codeops_state.py" readiness --root . `
  --gate requirements --target my-feature/RD-01
& $python "$env:PLUGIN_ROOT\scripts\codeops_state.py" readiness --root . `
  --gate execution --target my-feature/PLAN-01
```

WSL may be installed, but do not run CodeOps inside WSL or through Git Bash on Windows. Native
mutation workflows require a writable fixed local NTFS checkout without reparse-backed path
components; unsupported Windows storage blocks before a write.

When semantic preflight and deterministic readiness both pass, ask Codex to use
`exec-plan`. Specification tests establish the oracle before production code.
Each completed task records implementation, verification, review, and roadmap
state before moving to the next task.

Use the exact target ID from `traceability.json`. For a completed task, run the
`task-complete` gate for that task and persist its transition; do not use a feature-wide check.

## 5. Resume safely

In a fresh thread, ask CodeOps for project status or use the `roadmap` skill.
It reconstructs state from artifacts, traceability, plan checkboxes, findings,
and Git drift. If implementation uncovers a missing upstream decision, reopen
the ambiguity, mark linked downstream work stale, resolve it, and re-run the
affected gates before continuing.
