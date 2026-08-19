# `setup-routing`

Use `setup-routing` to configure risk- and capability-based Codex subagent routing for a project.
It analyzes the system's domains and risks, proposes roles before writing, records structured
policy, and can generate project-local agent definitions.

```text
Use setup-routing for this financial service. Preview the proposed roles first.
```

Routing can isolate reconnaissance, specification-test authoring, security review, concurrency
review, or other specialist work. It is an optimization, not a correctness dependency: missing
agents never weaken ambiguity, verification, or review gates.

Generated agents receive bounded dispatch packets with their scope, authoritative excerpts,
target paths, verification command, forbidden actions, and expected output. Model names may be
pinned by project policy, but the workflow retains a fallback when a pin is unavailable.
