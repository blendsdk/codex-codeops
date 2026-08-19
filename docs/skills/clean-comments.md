# `clean-comments`

Use `clean-comments` to audit or improve source comments and API documentation without changing
program behavior.

```text
Use clean-comments in report-only mode for src/.
```

## Modes

| Mode | Behavior |
|---|---|
| Report-only | Cite findings and proposed scope without editing |
| References-only | Replace ephemeral planning references with durable domain rationale |
| Full | Document public contracts, invariants, units, failures, ownership, and non-obvious decisions |

The skill never changes executable tokens, declarations, types, imports, string literals,
generated files, vendored code, snapshots, CodeOps artifacts, or `AGENTS.md`. It verifies that the
resulting diff is comment-only and follows the repository's language conventions.
