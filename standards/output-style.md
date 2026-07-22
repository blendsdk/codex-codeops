# Output style (CodeOps) — how to report back

- **Be short and prefer tabular form.** Findings, comparisons, status and file lists go in a table;
  use prose only for reasoning a table can't carry. Never narrate work already visible in the
  transcript, and never restate a result twice in different words.
- **Match reasoning effort to stakes.** Use deeper reasoning for semantic, financial, security,
  concurrency, migration, or architecture decisions; avoid interrupting the user merely to
  narrate an internal effort choice.
- **Advise `/compact` at clean boundaries**, not mid-task: after a phase verifies, before
  `preflight` or `make-plan`, and on a project switch. Say why now.
- **End with "Next steps"** wherever there is a next action — a small table of what to do and who
  owns it. When the repo has a roadmap, precede it with a one-line progress count (done / total)
  and a table of the remaining items, so the distance left to travel is always visible.
