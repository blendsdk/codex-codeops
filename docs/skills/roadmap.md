# `roadmap`

Use `roadmap` to maintain and inspect a derived view of features, requirements, plans, tasks,
findings, blockers, and lifecycle state.

## Actions

| Request | Effect |
|---|---|
| `make roadmap` | Create and seed roadmap rows from repository evidence |
| `update roadmap` | Re-infer lifecycle stages and synchronize derived status |
| `review roadmap` | Report drift, broken links, and consistency problems without writing |
| `show roadmap` | Display current progress and next steps without synchronizing |
| `archive roadmap` | Move an explicitly completed feature into the archive |
| `compact roadmap` | Remove legacy notes and trim oversized cells |

Roadmaps are not the source of requirement or plan truth. They summarize authoritative artifacts
and deterministic plan state. Manual status text cannot advance work whose evidence is incomplete.

Archival is guarded: the feature must be complete, links must remain valid, and the operation must
not hide active blockers or dependencies.
