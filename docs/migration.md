# Migration

## Existing CodeOps projects

CodeOps recognizes the historical flat `requirements/` plus `plans/` layout and the nested `codeops/` layout. The `setup-codeops` skill previews a flat-to-nested migration, refuses dirty Git state, uses `git mv`, writes structured strict policy, and places the layout marker last.

Run the setup skill in dry-run mode first. Review all source-relative-link warnings and the derived feature slug. Apply only after explicit confirmation.

## Claude project guidance

Project instructions belong in `AGENTS.md` for Codex. Do not mechanically copy global Claude instructions or model-routing blocks. Preserve repository commands and conventions that remain true, then express routing and quality policy in `codeops/codeops.json` or `.codex/config.toml`.

## Legacy workflow-state artifacts

Use the one-shot migrator on a nested `codeops/` directory. It previews by default:

```bash
python3 /path/to/plugin/scripts/codeops_plan_migrate.py ./codeops
python3 /path/to/plugin/scripts/codeops_plan_migrate.py ./codeops --apply
```

The migrator preserves checklist progress, adds or normalizes each plan's single
`> **Implements**:` declaration, creates a minimal index for roadmap-linked lightweight plans,
validates the four task markers, and deletes active and archived feature `traceability.json`
files. It prefers existing declarations and roadmap links, then consumes the legacy graph once
to recover plan-local requirements before deleting it. Explicit index metadata and a
single-plan/single-RD feature are conservative fallbacks. Archived features without a graph are
outside this bounded conversion. Any missing or ambiguous mapping blocks the entire apply without
changing files. Apply requires a clean Git working tree.

For blocked legacy work that does not already use `[!]`, first use `upgrade-plan` to record a
visible reason. Do not migrate graph state into another state platform.

After apply, run `python3 /path/to/plugin/scripts/codeops_plan.py --root . --json`, then the
repository's normal verification. Git history is the rollback and recovery mechanism.
