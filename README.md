# CodeOps for Codex

CodeOps is a specification-first engineering system for building complex software with Codex. It recursively turns an idea or an existing codebase into complete requirements, explicit architectural decisions, grounded technical specifications, a decision-complete or explicitly risk-deferred execution plan, verified implementation, and durable project tracking.

It is designed for work where an unstated assumption can become a correctness defect: programming languages and compilers, financial systems, protocols, distributed services, security-sensitive applications, developer tools, and substantial web applications.

> **Release status:** `0.5.0` is a release candidate pending its exact-artifact certification and annotated release tag. Native Windows 11 is not yet a published support claim. The current stable release remains `0.4.0`. A retained Claude 3.12.0 requirements-stage ambiguity benchmark passes; it is not a claim of complete product parity. A real complex-project milestone remains the 1.0 release gate.

## The workflow

```text
Intent or existing system
  → requirements discovery
  → requirements ambiguity closure
  → architecture and component specifications
  → specification ambiguity closure
  → execution plan
  → plan ambiguity closure
  → readiness proof
  → specification tests
  → implementation
  → verification and independent review
  → project and portfolio tracking
```

Later discoveries can reopen earlier gates. Implementation starts only when every material behavior, interface, invariant, failure mode, and verification obligation in scope is resolved or explicitly deferred by the user with its risk recorded.

## Current skills

The port begins from the proven CodeOps workflow set:

- requirements discovery, addition, and review;
- reverse requirements engineering;
- relentless ambiguity interviewing;
- implementation planning;
- multi-dimensional preflight review;
- specification-first plan execution;
- technical architecture documentation;
- feature and portfolio roadmaps;
- safe artifact upgrades and migration; and
- CodeOps project setup.

Codex-native traceability, readiness proofs, recovery, agent routing, and outcome evaluation are governed by the [port program](plans/codex-port/00-index.md).

Readiness commands are target-scoped: skills resolve the exact graph node and matching lifecycle
gate, while dependency closure supplies diagnostics without implicitly advancing sibling work.
Schema-1 graphs remain compatible and can be atomically upgraded to schema 2.

The retained [evaluation evidence](docs/evaluation.md) currently passes compiler, financial, and multi-tenant web ambiguity benchmarks against Claude CodeOps 3.12.0.
For a first project, follow the [complex-project quick start](docs/tutorial.md).

## Delegated technical design

Add `--auto-design` to `make-requirements`, `make-plan`, `preflight`, or `exec-plan` when CodeOps
should select the strongest supported technical option and record its evidence, alternatives,
counterargument, confidence, and reopen triggers. The delegation is invocation-scoped and
downward-only. It never delegates product scope, risk acceptance, spending, credentials,
deployment, destructive actions, or other reserved authority, and it grants no commit or action
permission. See [the authority model](docs/concepts.md#delegated-technical-design).

## Scope expansion control

CodeOps uses strict scope by default in `make-plan`, `preflight`, and `exec-plan`: it stays inside
the confirmed product boundary and does not suggest optional features, subsystems, or speculative
hardening. Evidence that the requested behavior itself cannot be correct, safe, or feasible is
still reported as a necessary correction or blocking uncertainty.

Add `--explore-scope` when you want optional additions proposed. CodeOps records each one as a
stable `SE-*` entry and waits for your `Keep`, `Defer`, or `Discard` ruling. Only `Keep` can add
executable work. `--auto-design`, finding acceptance, and permission to apply fixes never approve
scope expansion.

## Installation

Add the GitHub repository as a Codex marketplace, then install CodeOps:

```bash
codex plugin marketplace add blendsdk/codex-codeops --ref main
codex plugin add codeops@codeops-marketplace
```

These commands have been verified against the published repository. Start a new Codex thread after installation so skills and hooks are discovered.

The release-tested host is Linux with Bash and Python 3. Native Windows 11 certification requires
PowerShell, Git for Windows, Python 3.10 or newer, and final exact-artifact evidence before the
support claim is published. macOS is expected to be compatible but is not yet release-tested. On
Windows, CodeOps uses native executables only—never WSL or Git Bash.

Codex requires non-managed hooks to be reviewed before they run. Open `/hooks`, inspect the CodeOps SessionStart and edit-warning definitions, and trust them if they match this repository.

Verify installation with `codex plugin list`; `codeops@codeops-marketplace` should report `installed, enabled`.

## Update and uninstall

```bash
codex plugin marketplace upgrade codeops-marketplace
codex plugin add codeops@codeops-marketplace
```

Remove the plugin, and optionally its marketplace:

```bash
codex plugin remove codeops@codeops-marketplace
codex plugin marketplace remove codeops-marketplace
```

To disable without uninstalling, open `/plugins`, select the installed CodeOps entry, and press Space. Start a new thread after install, update, disable, re-enable, or removal. See [installation details](docs/installation.md) for trust, development, and troubleshooting notes.

## Development

```bash
git clone git@github.com:blendsdk/codex-codeops.git
cd codex-codeops
python -m pip install -r requirements-dev.txt
./scripts/validate-codex.sh
```

Native Windows 11 development uses Python 3.10 or newer and the PowerShell-owned portable
verification path:

```powershell
$python = & .\scripts\codeops-windows-preflight.ps1 -ResolvePython
& $python -m pip install -r requirements-dev.txt
& .\scripts\codeops-verify.ps1 all
```

The supported mutation boundary is a native Windows 11 Codex process in a writable, fixed local
NTFS workspace without reparse-backed path components. The preflight blocks before mutation when
that boundary or another prerequisite is not satisfied.

The sibling Claude CodeOps repository is the behavioral baseline during the port. Codex-specific improvements are accepted only when they preserve or strengthen ambiguity closure, verification, recovery, and project tracking.

## Security and privacy

CodeOps uses local repository tools and may install lifecycle hooks. Codex requires non-managed hooks to be reviewed and trusted before they run. CodeOps does not upload project content through telemetry; its optional outcome metrics are local, content-free, documented, and disabled by default.

## License

[MIT](LICENSE)
