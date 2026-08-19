# Compatibility

## Supported and evidenced environments

| Environment | Current evidence |
|---|---|
| Linux with Bash and Python 3 | Primary tested workflow host |
| macOS | Expected to work, but not yet a release-tested support claim |
| Windows | Plugin installation is retained as evidence; native end-to-end workflow support is not yet claimed |

Many CodeOps helpers are Python, but repository verification and migration entry points also use
Bash. On Windows, WSL or another compatible shell may run more of the workflow, but that is not a
substitute for native certification.

## Codex lifecycle

Start a new Codex thread after installing, upgrading, enabling, or disabling the plugin so skill
discovery and session hooks run from a clean lifecycle boundary.

## Artifact compatibility

CodeOps 1.0 reads the historical flat layout and can migrate it to the nested layout. It also
detects obsolete `traceability.json` state and converts unambiguous ownership and task progress to
the Markdown-authoritative model. Preview every migration and keep Git history as the rollback
mechanism.
