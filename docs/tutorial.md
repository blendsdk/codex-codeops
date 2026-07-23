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

## 3. Build and challenge the plan

After requirements are approved:

```text
Use make-plan for RD-01. Analyze the current code, write specifications before
implementation tasks, and resolve every plan ambiguity with me.
```

Then run `preflight`. Critical and major findings reopen the affected gate; they
are not converted silently into implementation assumptions.

## 4. Prove readiness and execute

Run the deterministic check from the project root:

```bash
python3 /path/to/codeops/scripts/codeops_state.py readiness --root .
```

When semantic preflight and deterministic readiness both pass, ask Codex to use
`exec-plan`. Specification tests establish the oracle before production code.
Each completed task records implementation, verification, review, and roadmap
state before moving to the next task.

## 5. Resume safely

In a fresh thread, ask CodeOps for project status or use the `roadmap` skill.
It reconstructs state from artifacts, traceability, plan checkboxes, findings,
and Git drift. If implementation uncovers a missing upstream decision, reopen
the ambiguity, mark linked downstream work stale, resolve it, and re-run the
affected gates before continuing.
