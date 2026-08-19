# Security and privacy

CodeOps operates through Codex with the filesystem, shell, Git, and external tools available to the
active session. Review Codex permissions and repository changes just as you would for any other
development agent.

## Hooks

Non-managed plugin hooks do not run until you inspect and trust them through `/hooks`. CodeOps uses
a session-start hook for coding and output standards and an edit-warning hook for the layout marker.
A changed definition requires review again.

## Authority boundaries

Delegated design and automated commits do not authorize:

- credentials or secret access beyond the active environment;
- destructive or irreversible operations;
- deployment, publication, spending, or external communication;
- product-scope or risk-acceptance decisions; or
- force-pushes or bypassing verification and hooks.

## Project data

Requirements, plans, findings, and roadmaps remain local repository content unless you explicitly
commit, push, publish, or send them elsewhere. Optional outcome evidence is local and content-free;
CodeOps does not upload project content as telemetry.

Inspect changes and untracked files before every commit. Never add generated documentation output,
credentials, environment files, or local caches to the repository.
