# `github-issues`

Use `github-issues` to inspect a repository's backlog or to close and reopen explicitly identified
GitHub issues.

```text
Use github-issues to show the open backlog grouped by the repository's priority scheme.
Close issue 42 as completed.
```

Overview mode is read-only. It discovers the repository's actual labels, issue types, project
fields, dependencies, priorities, and effort scheme rather than imposing a universal taxonomy.

Closing or reopening is an external mutation and therefore requires explicit intent and exact issue
identity. Supported closure reasons are recorded consistently, duplicates identify their target,
and the skill verifies the resulting remote state. It does not edit issue titles, bodies, labels,
assignees, milestones, or project fields unless separately requested.
