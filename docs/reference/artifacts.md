# Artifacts and ownership

CodeOps keeps workflow truth in reviewable repository files. One fact has one authoritative owner;
derived views link back to it rather than restating it as independent state.

| Fact | Authoritative owner |
|---|---|
| Product behavior and acceptance criteria | Numbered requirement document |
| Open or deferred material choices | Target's ambiguity register |
| Optional scope proposals and rulings | Target-qualified scope-expansion register |
| Requirement-to-plan mapping | Plan `00-index.md` `Implements` declaration |
| Technical design for one plan | Plan specification and architecture documents |
| Verification obligations | Plan testing strategy and specification tests |
| Task progress and blocker reason | Plan `99-execution-plan.md` |
| Layout selection and integration branch | `codeops/.codeops.yml` |
| Quality, routing, and metrics policy | `codeops/codeops.json` |
| Feature and portfolio summary | Derived roadmap files |
| Change history and recovery | Git |

## Nested layout

```text
codeops/
├── .codeops.yml
├── codeops.json
├── 00-roadmap.md
├── features/
│   └── feature-slug/
│       ├── 00-roadmap.md
│       ├── requirements/
│       └── plans/
└── _archive/
```

Feature folders are created lazily. Requirement IDs reset within each feature; cross-feature links
therefore include the feature slug. Lightweight tasks use their own `T-*` sequence.

Historical flat layouts remain readable until migrated. See [project layout](/guide/project-layout)
and [migration](/migration).
