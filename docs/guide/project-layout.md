# Project layout

New CodeOps projects use a nested layout so each feature owns its requirements, plans, findings,
and roadmap while the portfolio retains a concise cross-feature view.

```text
codeops/
├── .codeops.yml
├── codeops.json
├── 00-roadmap.md
├── features/
│   └── example-feature/
│       ├── 00-roadmap.md
│       ├── requirements/
│       └── plans/
└── _archive/
```

The exact files inside a feature depend on which workflows have run. Markdown artifacts are the
durable, reviewable source of requirements, decisions, specifications, test obligations, findings,
and progress.

## Layout ownership

`setup-codeops` is the sole writer of `codeops/.codeops.yml`. Other skills read the marker to
resolve the layout and policy. Do not hand-edit it during an active migration.

Historical projects with top-level `requirements/` and `plans/` remain recognizable. Preview their
migration with `setup-codeops --dry-run` and apply it only from a clean Git state.

See [artifacts and ownership](/reference/artifacts) for the source-of-truth rules.
