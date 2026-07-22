# Installation and trust

## Install from GitHub

```bash
codex plugin marketplace add blendsdk/codex-codeops --ref main
codex plugin add codeops@codeops-marketplace
```

The first command configures the repository's marketplace. The second installs the `codeops` plugin into Codex's plugin cache. Confirm with `codex plugin list` and start a new thread.

## Hooks

CodeOps bundles two hook behaviors:

- SessionStart reads the plugin's coding and output standards into the new thread.
- PreToolUse warns when an edit targets the CodeOps layout marker.

Codex does not automatically trust non-managed plugin hooks. Use `/hooks` to inspect their exact commands and approve them. Changed hook definitions require review again. The warning hook is a guardrail, not a security boundary.

## Updates

```bash
codex plugin marketplace upgrade codeops-marketplace
codex plugin add codeops@codeops-marketplace
```

Released versions use semantic versions. Development builds may include a Codex cachebuster suffix so the plugin cache receives updated files without pretending a new product release exists.

## Removal

```bash
codex plugin remove codeops@codeops-marketplace
```

Optionally remove the marketplace:

```bash
codex plugin marketplace remove codeops-marketplace
```

Project artifacts created by CodeOps are repository content and are deliberately not deleted by plugin removal.

## Development checkout

```bash
git clone git@github.com:blendsdk/codex-codeops.git
cd codex-codeops
python -m pip install -r requirements-dev.txt
./scripts/validate-codex.sh
```

Do not hand-edit installed cache files.
