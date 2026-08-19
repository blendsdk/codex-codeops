# `setup-codeops`

Use `setup-codeops` to initialize the nested CodeOps layout or migrate a historical layout. It is
the sole owner of `codeops/.codeops.yml`.

```text
Use setup-codeops --dry-run for this repository.
```

## Flags

| Flag | Behavior |
|---|---|
| `--dry-run` | Compute and display the operation without changing files |
| `--yes` | Apply an unblocked migration without a confirmation prompt |

Every migration previews first. Apply requires a Git repository and clean working tree, refuses
ambiguous or unsafe mappings, uses deterministic migration helpers, and verifies the result. The
layout marker is written last so an interrupted operation cannot masquerade as a completed setup.

Start with `--dry-run`, especially when migrating a top-level `requirements/` and `plans/` layout or
removing obsolete workflow-state artifacts.
