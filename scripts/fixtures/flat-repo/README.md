# Fixture: flat-layout repo (migration test input)

A minimal **flat-layout** CodeOps repo used by `scripts/migration-check.sh` to exercise the
`scripts/codeops-migrate.sh` engine. It is committed read-only test data — tests must always
copy it to a temp dir and assert the copy, never mutate this tree.

## Contents

```
flat-repo/
├── requirements/
│   ├── 00-ambiguity-register.md
│   ├── RD-01-invoicing.md
│   └── RD-02-payments.md
├── plans/
│   ├── 00-roadmap.md            # Feature-Set header "Billing Platform" → slug billing-platform
│   ├── invoicing/               # plan listed in the roadmap
│   │   ├── 00-index.md
│   │   └── 99-execution-plan.md
│   ├── legacy/                  # plan NOT listed in the roadmap (warning case)
│   │   └── 03-old.md            # links ../../src/pay.ts (source-relative; warning case)
│   └── _archive/
│       └── billing-v1/          # already-archived set
│           └── 00-index.md
└── src/
    └── pay.ts                   # source outside the planning tree (never moved)
```

## Expected migration (slug `billing-platform`, from the roadmap header)

| Source | Destination |
| ------ | ----------- |
| `requirements/` | `codeops/features/billing-platform/requirements/` |
| `plans/invoicing/` | `codeops/features/billing-platform/plans/invoicing/` |
| `plans/legacy/` | `codeops/features/billing-platform/plans/legacy/` |
| `plans/00-roadmap.md` | `codeops/features/billing-platform/00-roadmap.md` |
| `plans/_archive/billing-v1/` | `codeops/_archive/billing-v1/` |
| *(create)* | `codeops/.codeops.yml` |
| *(create)* | `codeops/00-roadmap.md` (portfolio, 1 feature) |

Warnings the dry-run must surface:
- `plans/legacy/` is present on disk but not listed in the roadmap.
- `plans/legacy/03-old.md` links `../../src/pay.ts` (source-relative; verify after move).
