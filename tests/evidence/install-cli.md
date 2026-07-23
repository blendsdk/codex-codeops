# Codex CLI installation lifecycle evidence

- Captured: 2026-07-23
- Host: Linux
- Codex CLI: `0.145.0`
- Marketplace: `blendsdk/codex-codeops`, ref `main`
- Plugin: `codeops@codeops-marketplace`, version `0.3.0`
- Repository source: release tag `v0.3.0`

The following lifecycle was executed successfully against commit `ea62ea2` on the public GitHub
repository in this order:

1. `codex plugin marketplace upgrade codeops-marketplace --json`
2. `codex plugin remove codeops@codeops-marketplace --json`
3. `codex plugin add codeops@codeops-marketplace --json` installed version `0.3.0`.
4. `codex plugin list --json` reported the plugin installed and enabled at
   `0.3.0`, sourced from `https://github.com/blendsdk/codex-codeops.git` at ref `main`.

Disable/re-enable is an interactive `/plugins` browser action and is documented but not claimed as
automated evidence. Start a new Codex thread to load the installed 0.3.0 skill definitions.
