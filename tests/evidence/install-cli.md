# Codex CLI installation lifecycle evidence

- Captured: 2026-08-07
- Host: release-candidate metadata preparation
- Codex CLI: `0.146.0`
- Marketplace: `blendsdk/codex-codeops`, ref `main`
- Plugin: `codeops@codeops-marketplace`, version `0.5.0`
- Evidence state: pre-publication package validation
- Source state: working tree for planned `v0.5.0`

The retained `0.4.0` lifecycle below remains the latest published installation proof while the
`0.5.0` candidate is certified:

1. `codex plugin marketplace upgrade codeops-marketplace --json` refreshed the public marketplace
   without errors.
2. `codex plugin add codeops@codeops-marketplace --json` installed version `0.4.0`.
3. `codex plugin list --json` reported the plugin installed and enabled at `0.4.0`, sourced from
   `https://github.com/blendsdk/codex-codeops.git` at ref `main`.

Start a new Codex thread to load the installed 0.4.0 skill definitions.
