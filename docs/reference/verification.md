# Quality and verification

CodeOps combines semantic review with executable repository checks. Neither substitutes for the
other.

## Artifact readiness

Before execution, confirm directly that:

- required requirement, specification, testing, and plan documents exist;
- every material ambiguity is resolved or explicitly deferred with risk;
- the plan declares the requirements it implements;
- specification tests precede production-code tasks;
- every task has an executable verification command; and
- no unresolved critical or major finding remains.

Inspect derived plan state with:

```bash
python3 /path/to/codeops/scripts/codeops_plan.py --root . --json
```

## Implementation verification

Each task follows this order:

```text
specification test → confirm red → implementation → confirm green
  → implementation tests → full verification → independent review
```

Repository guidance owns the exact build, test, lint, security, and documentation commands. CodeOps
does not invent plausible commands when the repository has not defined them.

## CodeOps plugin verification

Contributors to this plugin run all repository checks from its root:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```
