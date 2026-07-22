# Migration

## Existing CodeOps projects

CodeOps recognizes the historical flat `requirements/` plus `plans/` layout and the nested `codeops/` layout. The `setup-codeops` skill previews a flat-to-nested migration, refuses dirty Git state, uses `git mv`, writes structured strict policy, and places the layout marker last.

Run the setup skill in dry-run mode first. Review all source-relative-link warnings and the derived feature slug. Apply only after explicit confirmation.

## Claude project guidance

Project instructions belong in `AGENTS.md` for Codex. Do not mechanically copy global Claude instructions or model-routing blocks. Preserve repository commands and conventions that remain true, then express routing and quality policy in `codeops/codeops.json` or `.codex/config.toml`.

## Traceability adoption

Legacy Markdown artifacts remain readable. Add feature `traceability.json` incrementally, then run:

```bash
python3 /path/to/plugin/scripts/codeops_state.py readiness --root .
```

Do not mark legacy work ready until every active requirement, specification, criterion, test, task, implementation, and verification node has valid links and semantic review passes.
