# The CodeOps workflow

CodeOps is recursive rather than strictly linear. Later evidence can reopen an earlier decision,
invalidate affected downstream work, and require a fresh review.

| Stage | Primary skill | Durable outcome |
|---|---|---|
| Clarify the idea | `grill-me` | Confirmed decisions and constraints |
| Discover requirements | `make-requirements` | Numbered requirement documents |
| Reconstruct existing behavior | `retro-requirements` | Confidence-classified reconstruction brief |
| Challenge an artifact | `preflight` | Severity-ranked findings and rulings |
| Design implementation | `make-plan` | Specifications, testing strategy, and execution plan |
| Execute safely | `exec-plan` | Verified tasks, review evidence, and commits as authorized |
| Track the portfolio | `roadmap` | Derived feature and portfolio status |
| Maintain architecture knowledge | `techdocs` | Architecture guides and decision records |

## The normal greenfield sequence

```text
setup-codeops
  → make-requirements
  → preflight requirements
  → make-plan
  → preflight plan
  → exec-plan
  → roadmap
```

Use `grill-me` before requirements when the initial idea contains major unresolved design branches.
For an existing codebase, begin with `retro-requirements` and triage observed behavior before
turning it into requirements.

## Why gates can reopen

A plan may reveal that a requirement did not define a failure mode. A specification test may expose
an incompatible contract. Implementation may uncover repository behavior that contradicts the
plan. CodeOps sends that discovery back to its authoritative artifact instead of inventing a local
assumption.

This is the central safety property: downstream progress never makes an upstream ambiguity true.
