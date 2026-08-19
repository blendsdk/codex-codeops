# `analyze-project`

Use `analyze-project` to create or refresh concise CodeOps-aware `AGENTS.md` guidance from evidence
in the repository.

```text
Use analyze-project to refresh this repository's AGENTS.md.
```

The skill inspects manifests, build and test configuration, CI, source layout, package boundaries,
nested instructions, default and integration branches, and recent commit conventions. It derives
commands only from executable configuration or explicit documentation.

Hand-authored policy remains authoritative. CodeOps manages a delimited section, previews
consequential rewrites, and avoids repeating facts already owned by a narrower `AGENTS.md`.
Compact mode removes stale or duplicated generated guidance only; it does not silently rewrite
hand-authored content.
