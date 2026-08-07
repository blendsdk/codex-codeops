# Installation and trust

The release-tested host is Linux with Bash and Python 3. Native Windows 11 is a pending 0.5.0
release target until the exact final artifact passes CLI, Desktop, Ubuntu, and Windows evidence
gates and the annotated release is published. It requires PowerShell, Git for Windows, and Python
3.10 or newer. Do not invoke CodeOps through WSL, Git Bash, or a Bash launcher on Windows.

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

## Disable or re-enable

Open the Codex CLI plugin browser with `/plugins`, select the installed CodeOps
entry, and press Space. Codex stores the enabled state in its user config. Start
a new thread after changing it. Disabling keeps the installed bundle and project
artifacts; removal deletes the installed bundle.

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

### Native Windows 11

Use Windows PowerShell or PowerShell 7 with native Git for Windows. Do not use WSL, Git Bash, or a
Bash launcher for CodeOps on Windows.

```powershell
git clone git@github.com:blendsdk/codex-codeops.git
Set-Location codex-codeops
$python = & .\scripts\codeops-windows-preflight.ps1 -ResolvePython
& $python -m pip install -r requirements-dev.txt
& .\scripts\codeops-verify.ps1 all
```

The bootstrap requires Python 3.10 or newer. The native mutation preflight additionally requires
Windows 11, native Codex, Git for Windows, and a writable fixed local NTFS workspace without
reparse-backed path components. It reports actionable prerequisite status and blocks before a
write when the supported mutation boundary is not satisfied. WSL may remain installed; CodeOps
only prohibits executing through it.
