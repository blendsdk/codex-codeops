# Codex CLI installation lifecycle evidence

- Captured: 2026-07-31
- Host: Linux
- Codex CLI: `0.146.0`
- Marketplace: `blendsdk/codex-codeops`, ref `main`
- Plugin: `codeops@codeops-marketplace`, version `0.4.0`
- Repository source: release tag `v0.4.0`

The following lifecycle was executed successfully against commit `b29ab79` on the public GitHub
repository in this order:

1. `codex plugin marketplace upgrade codeops-marketplace --json` refreshed the public marketplace
   without errors.
2. `codex plugin add codeops@codeops-marketplace --json` installed version `0.4.0`.
3. `codex plugin list --json` reported the plugin installed and enabled at `0.4.0`, sourced from
   `https://github.com/blendsdk/codex-codeops.git` at ref `main`.

Start a new Codex thread to load the installed 0.4.0 skill definitions.
