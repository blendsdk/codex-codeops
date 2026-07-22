# Port Ambiguity Register

> **Gate rule:** No implementation phase affected by an open material item may begin until that item is resolved or explicitly deferred with recorded risk.

## Open decisions

| ID | Question | Why material | Owner | Needed before |
|---|---|---|---|---|
| AR-002 | Is cross-platform support required at initial release: Linux only, POSIX, or Linux/macOS/Windows? | Shell utilities and worktree launching currently assume Bash; this changes implementation and test scope. | Product owner | Utility port |
| AR-003 | Should legacy flat `requirements/` and `plans/` layouts remain supported indefinitely, or only through migration? | Affects every path resolver and doubles long-term test combinations. | Product owner | Artifact engine design |
| AR-004 | Should the Codex and Claude editions use the same artifact schema so projects can switch agents, or may the Codex edition introduce a new schema with migration tooling? | Determines compatibility versus freedom to improve traceability and gates. | Product owner | Schema implementation |
| AR-005 | Which Codex surfaces are release-critical: CLI, IDE extension, desktop app, or all three? | Plugins, prompts, agents, hooks, and UI behavior differ by surface. | Product owner | Acceptance matrix |
| AR-006 | May project tracking use deterministic generated indexes derived from authoritative artifacts? | Enables reliable status and drift detection but introduces generated-state policy. | Product owner | Tracking engine |
| AR-007 | What is the release policy for telemetry: removed, opt-in local outcome metrics, or full parity with current local telemetry? | Changes privacy surface, hook behavior, scripts, and documentation. | Product owner | Telemetry phase |
| AR-008 | Should complex-project mode be the universal default or an explicit strict profile, with a lighter profile for small work? | Affects invocation ergonomics without changing the strict workflow's guarantees. | Product owner | UX design |
| AR-009 | Are Codex model names allowed in checked-in defaults, or must routing remain role/capability based with environment resolution? | Hard-coded models age quickly; abstract roles require a resolver and fallback rules. | Product owner | Agent architecture |
| AR-010 | Should generated Codex custom-agent TOML files be project-local, user-local, or avoided in favor of complete dynamic dispatch packets? | Codex plugins do not document plugin-root custom agents as an installed component. | Technical prototype | Agent implementation |

## Resolved decisions

| ID | Resolution | Basis |
|---|---|---|
| AR-011 | The Codex port lives in `/home/gevik/workdir/github/claude-codeops/codex`; the Claude source remains unchanged during initial development. | User-approved placement and isolation requirement. |
| AR-012 | Project/portfolio tracking is a required first-class feature, not an optional follow-up. | Explicit user direction. |
| AR-013 | Recursive ambiguity elimination must meet or beat the Claude edition; simplification may remove duplication but not specification rigor. | Explicit user direction and core product purpose. |
| AR-014 | Initial planning must precede implementation because this is a crown-jewel system with high regression cost. | Explicit user direction and CodeOps' own governing method. |
| AR-001 | The Codex edition is an independent repository at `git@github.com:blendsdk/codex-codeops.git`, with its own history, releases, CI, and installable distribution. Shared-source extraction may be reconsidered only after the Codex design stabilizes. | Explicit product-owner decision; repository created and local workspace connected. |

## Working defaults pending resolution

These defaults permit planning and prototypes but must not silently become product decisions:

- Preserve current artifact compatibility until AR-004 is resolved.
- Target CLI first while maintaining an explicit surface compatibility matrix for AR-005.
- Make telemetry opt-in and store writable data under Codex plugin data paths until AR-007 is resolved.
- Use capability-based agent roles and resolve current models at runtime until AR-009 is resolved.
- Treat Linux and macOS as the provisional script baseline; do not claim Windows support before AR-002 is resolved.
