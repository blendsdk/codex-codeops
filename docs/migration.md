# Migration

## Existing CodeOps projects

CodeOps recognizes the historical flat `requirements/` plus `plans/` layout and the nested `codeops/` layout. The `setup-codeops` skill previews a flat-to-nested migration, refuses dirty Git state, uses `git mv`, writes structured strict policy, and places the layout marker last.

Run the setup skill in dry-run mode first. Review all source-relative-link warnings and the derived feature slug. Apply only after explicit confirmation.

## Claude project guidance

Project instructions belong in `AGENTS.md` for Codex. Do not mechanically copy global Claude instructions or model-routing blocks. Preserve repository commands and conventions that remain true, then express routing and quality policy in `codeops/codeops.json` or `.codex/config.toml`.

## Traceability adoption and schema upgrade

Legacy Markdown artifacts and schema-1 graphs remain readable. Upgrade graphs with a deterministic
preview and explicit resolutions:

```bash
python3 /path/to/plugin/scripts/codeops_state.py traceability-upgrade --root . \
  --feature my-feature --preview upgrade.json
python3 /path/to/plugin/scripts/codeops_state.py traceability-upgrade --root . \
  --feature my-feature --preview upgrade.json --resolutions resolutions.json --apply
python3 /path/to/plugin/scripts/codeops_state.py validate --root .
```

Review the preview; resolve every classified ambiguity or explicitly omit the link. Apply is
atomic, creates a protected backup, and reports recovery-required state instead of guessing after
an interrupted write. Do not mark legacy work ready until every active node has valid links,
current source revisions and snapshots, and semantic review passes.
