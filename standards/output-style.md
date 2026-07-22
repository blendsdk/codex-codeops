# Output style (CodeOps) — how to report back

- **Be short and prefer tabular form.** Findings, comparisons, status and file lists go in a table;
  use prose only for reasoning a table can't carry. Never narrate work already visible in the
  transcript, and never restate a result twice in different words.
- **Recommend an effort level before starting any task** — one line, before the first tool call:
  the level, the reason, and that `/effort` can change it. The user adjusts or proceeds.
- **Advise `/compact` at clean boundaries**, not mid-task: after a phase verifies, before
  `preflight` or `make-plan`, and on a project switch. Say why now.
- **End with "Next steps"** wherever there is a next action — a small table of what to do and who
  owns it. When the repo has a roadmap, precede it with a one-line progress count (done / total)
  and a table of the remaining items, so the distance left to travel is always visible.
