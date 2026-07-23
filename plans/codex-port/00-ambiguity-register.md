# Port Ambiguity Register

> **Gate rule:** No implementation phase affected by an open material item may begin until that item is resolved or explicitly deferred with recorded risk.

## Open decisions

None for the installable CLI beta. Surface expansion and the real-project 1.0
pilot are release work, not unresolved semantics in the implemented beta.

## Resolved decisions

| ID | Resolution | Basis |
|---|---|---|
| AR-011 | The Codex port lives in `/home/gevik/workdir/github/claude-codeops/codex`; the Claude source remains unchanged during initial development. | User-approved placement and isolation requirement. |
| AR-012 | Project/portfolio tracking is a required first-class feature, not an optional follow-up. | Explicit user direction. |
| AR-013 | Recursive ambiguity elimination must meet or beat the Claude edition; simplification may remove duplication but not specification rigor. | Explicit user direction and core product purpose. |
| AR-014 | Initial planning must precede implementation because this is a crown-jewel system with high regression cost. | Explicit user direction and CodeOps' own governing method. |
| AR-001 | The Codex edition is an independent repository at `git@github.com:blendsdk/codex-codeops.git`, with its own history, releases, CI, and installable distribution. Shared-source extraction may be reconsidered only after the Codex design stabilizes. | Explicit product-owner decision; repository created and local workspace connected. |
| AR-002 | Linux with Bash and Python 3 is the tested CLI beta host. macOS compatibility is expected but not release-tested; Windows is not supported. | Platform claims now match retained evidence instead of POSIX assumptions. |
| AR-003 | Both flat and nested layouts remain readable; migration to the nested layout is preview-first, explicit, and idempotent. | Preserves existing projects without making destructive migration automatic. |
| AR-004 | Codex uses schema-1 traceability/config artifacts plus a lossless migration path from supported Claude layouts. Human-readable artifacts remain portable. | Enables stronger typed traceability while preserving project continuity. |
| AR-005 | Codex CLI is the release-critical beta surface. Desktop/IDE consumption may use the same marketplace, but is not a release claim until independently exercised. | The user authorized implementation from the CLI repository and all retained live evidence is CLI evidence. |
| AR-006 | Deterministic reports and roadmap counters may be derived from authoritative artifacts; generated views must be reproducible and drift-checkable. | Implemented state and roadmap engines keep authored decisions authoritative. |
| AR-007 | Legacy telemetry is removed. Optional metrics are local, content-free, enumerated, and disabled by default. | Minimizes privacy surface while retaining measurable workflow outcomes. |
| AR-008 | Strict complex-project gates are the default for features; small fixes route to a lightweight task lane without weakening feature gates. | Preserves the crown-jewel workflow without forcing full RD ceremony onto trivial work. |
| AR-009 | Checked-in routing is capability based and contains no model names. The runtime/user chooses available models. | Prevents model churn from aging project policy. |
| AR-010 | Complete dynamic dispatch packets are the correctness baseline. Optional project-local TOML agents may be installed behind managed markers. | Works without plugin-root agent discovery and permits local optimization safely. |

## Working defaults pending resolution

None.
