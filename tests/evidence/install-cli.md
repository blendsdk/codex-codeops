# Codex CLI installation lifecycle evidence

- Captured: 2026-07-23
- Host: Linux
- Codex CLI: `0.145.0`
- Marketplace: `blendsdk/codex-codeops`, ref `main`
- Plugin: `codeops@codeops-marketplace`, version `0.2.0-beta.5`
- Repository source: release tag `v0.2.0-beta.5`

The following lifecycle was executed successfully against the public GitHub
repository in this order:

1. `codex plugin marketplace upgrade codeops-marketplace --json`
2. `codex plugin list --json` reported the plugin installed and enabled at
   `0.2.0-beta.5`.
3. `codex plugin remove codeops@codeops-marketplace --json` removed it.
4. `codex plugin list --json` reported no installed plugins.
5. `codex plugin add codeops@codeops-marketplace --json` installed it again.
6. `codex plugin list --json` reported the reinstalled plugin enabled at
   `0.2.0-beta.5`, sourced from
   `https://github.com/blendsdk/codex-codeops.git` at ref `main`.

Disable/re-enable is an interactive `/plugins` browser action and is documented,
but was not claimed as automated evidence. Hook payload scripts are covered by
conformance fixtures; the live scenario runs prove SessionStart hook execution
with explicit automation trust bypass. User approval through `/hooks` remains a
user-controlled trust action.
