# Codex CLI installation lifecycle evidence

- Captured: 2026-08-07
- Host: native Windows 11 CLI and Desktop certification
- Codex CLI: `0.146.0`
- Marketplace: `blendsdk/codex-codeops`, ref `main`
- Plugin: `codeops@codeops-marketplace`, version `0.5.0`
- Evidence state: pre-publication package validation
- Candidate commit: `87978a39861686491156b1f847d6bf843069b9da`
- Candidate SHA-256: `d4b469cd522caf734e5f274857b5e89cff03e1013204c5c7ddf72280d3446ada`
- Source state: working tree for planned `v0.5.0`

The retained public-marketplace lifecycle below records the preceding `0.4.0` release. The 0.5.0
candidate was installed from its hash-bound package for native CLI and Desktop certification:

1. `codex plugin marketplace upgrade codeops-marketplace --json` refreshed the public marketplace
   without errors.
2. `codex plugin add codeops@codeops-marketplace --json` installed version `0.4.0`.
3. `codex plugin list --json` reported the plugin installed and enabled at `0.4.0`, sourced from
   `https://github.com/blendsdk/codex-codeops.git` at ref `main`.

The 0.5.0 candidate loaded successfully in a new native Windows Codex CLI thread and a new Codex
Desktop thread. The paired retained manifests bind those installations to the candidate hash,
version, commit, native runtime assertions, and completed workflow scenarios.
