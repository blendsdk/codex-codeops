# Migration

## Existing CodeOps projects

CodeOps recognizes the historical flat `requirements/` plus `plans/` layout and the nested `codeops/` layout. The `setup-codeops` skill previews a flat-to-nested migration, refuses dirty Git state, uses `git mv`, writes structured strict policy, and places the layout marker last.

Run the setup skill in dry-run mode first. Review all source-relative-link warnings and the derived feature slug. Apply only after explicit confirmation.

## Claude project guidance

Project instructions belong in `AGENTS.md` for Codex. Do not mechanically copy global Claude instructions or model-routing blocks. Preserve repository commands and conventions that remain true, then express routing and quality policy in `codeops/codeops.json` or `.codex/config.toml`.

## Legacy workflow-state artifacts

Upgrade legacy Markdown in place: preserve requirements and checklist progress, add one
`> **Implements**:` declaration listing every RD implemented by the plan, convert blocked work to
`[!]` with a visible reason, and retain `[~]`/`[x]` accurately. After confirming no external tool
still consumes it, delete `traceability.json`; do not migrate it into another state platform.

Run `python3 /path/to/plugin/scripts/codeops_plan.py --root . --json`, then the repository's normal
verification. Git history is the rollback and recovery mechanism.
