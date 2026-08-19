# `techdocs`

Use `techdocs` to create or maintain VitePress-compatible technical architecture documentation and
architecture decision records for a software project.

```text
Use techdocs to document this service's architecture.
Use review_techdocs to audit the existing architecture docs.
```

## Modes

| Request | Behavior |
|---|---|
| `make_techdocs` | Create or comprehensively regenerate architecture documentation |
| `make_techdocs --continue` | Resume an interrupted authoring session |
| `review_techdocs` | Run a read-only seven-dimension health check |

When a project opts in through the documented marker, completed requirements and execution phases
can trigger incremental or comprehensive updates. Existing ADR intent is preserved; observed code
that diverges from an ADR is reported rather than silently rewriting the decision.

This skill owns developer-facing architecture material: system design, data, APIs, infrastructure,
security, ADRs, and developer guides. It does not generate end-user product documentation.
