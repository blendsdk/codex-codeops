# Plan a new feature

This tutorial takes a feature idea through requirements, preflight, and an executable plan without
starting implementation.

## 1. Initialize the project

From a clean Git repository, start with a preview:

```text
Use setup-codeops --dry-run to initialize this repository.
```

Review the integration branch, proposed files, and migration warnings. If the preview is correct:

```text
Use setup-codeops --yes to apply the preview and verify it.
```

## 2. Discover requirements

Provide the problem, users, constraints, non-goals, known integrations, and risk-sensitive areas.

```text
Use make-requirements for recurring invoice reconciliation.

Users are finance operators. Reconciliation imports bank transactions, matches them to invoices,
and requires human approval for ambiguous matches. Do not include payment initiation.
```

Answer behavior and scope questions concretely. If you want CodeOps to choose eligible technical
details, add `--auto-design`; product behavior and risk decisions still return to you.

## 3. Audit the requirements

```text
Use preflight on the recurring invoice reconciliation requirements.
```

Review each finding. Fix root causes in the authoritative requirement document and rerun the
affected scan until no blocking finding remains.

## 4. Create the plan

```text
Use make-plan for the recurring invoice reconciliation requirements.
Analyze the current repository and keep payment initiation out of scope.
```

The plan should identify its implemented RDs, define component behavior, establish specification
tests before production changes, and give each task an executable verification command.

## 5. Challenge the plan

```text
Use preflight on the recurring invoice reconciliation plan.
```

When the audit passes, inspect derived status:

```bash
python3 /path/to/codeops/scripts/codeops_plan.py --root . --json
```

You now have an implementation-ready plan. Continue with
[Execute a plan safely](execute-plan.md).
