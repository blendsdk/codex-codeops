# Migrate from Claude CodeOps

Treat the Claude implementation as behavioral history, not a directory tree to copy mechanically.
Codex uses different host instructions, plugin paths, agent routing, invocation names, and workflow
state.

## 1. Preserve project-specific intent

Move durable repository guidance into `AGENTS.md`. Keep commands, conventions, constraints, and
domain rules that remain true. Do not copy Claude model-routing blocks, global instructions,
`.claude/` paths, or hook configuration unchanged.

## 2. Preview the artifact layout migration

```text
Use setup-codeops --dry-run to migrate this existing CodeOps project.
```

Review feature slugs, relative-link warnings, integration branch, and every proposed move. Apply
only from a clean Git working tree.

## 3. Upgrade content separately

Use `upgrade-plan` when requirement or plan content uses an older schema or no longer satisfies the
current ambiguity and verification gates. Do not combine semantic rewriting and layout movement in
one irreversible operation.

## 4. Remove legacy state

CodeOps 1.0 derives state from Markdown and Git. Re-running `setup-codeops` detects obsolete
`traceability.json` files and previews their deterministic conversion into plan-local requirement
ownership and checklist progress. Ambiguous mappings block the whole apply.

## 5. Configure Codex routing

Run `setup-routing` only after the project structure is stable. Review proposed specialist roles
and model availability; the correctness gates must remain operable without custom agents.

See the complete [migration reference](/migration) for commands and safeguards.
