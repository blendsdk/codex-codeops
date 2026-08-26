# CodeOps for Codex

CodeOps is a specification-first engineering system for building complex software with Codex. It recursively turns an idea or an existing codebase into complete requirements, explicit architectural decisions, grounded technical specifications, a decision-complete or explicitly risk-deferred execution plan, verified implementation, and durable project tracking.

It is designed for work where an unstated assumption can become a correctness defect: programming languages and compilers, financial systems, protocols, distributed services, security-sensitive applications, developer tools, and substantial web applications.

**Documentation:** [blendsdk.github.io/codex-codeops](https://blendsdk.github.io/codex-codeops/)

> **Release status:** `1.0.1` is the stable release of the Markdown-authoritative CodeOps workflow surface. Core workflows, direct plan-derived progress, project tracking, domain lenses, Codex-native routing, opt-in delegated technical design, strict scope control with user-owned exploration, minimum-sufficient design guidance, automatic legacy-state migration, and a non-negotiable source-documentation gate are present. Migration has been exercised on JSVision with its full cross-platform CI matrix. The retained Claude 3.12.0 benchmark remains requirements-stage evidence and is not a claim of complete comparative parity.

## The workflow

```text
Intent or existing system
  → requirements discovery
  → requirements ambiguity closure
  → architecture and component specifications
  → specification ambiguity closure
  → execution plan
  → plan ambiguity closure
  → direct artifact readiness checks
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

Requirements own agreed behavior; plan metadata declares RD mapping; and each
`99-execution-plan.md` owns its task progress. Roadmaps and status summaries are derived. The
minimal lifecycle and the rest of the Codex-native workflow are governed by the
[port program](plans/codex-port/00-index.md).

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

The tested host is Linux with Bash and Python 3. macOS is expected to be
compatible but is not yet a release-tested claim; Windows is not currently supported.

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

The sibling Claude CodeOps repository is the behavioral baseline during the port. Codex-specific improvements are accepted only when they preserve or strengthen ambiguity closure, verification, recovery, and project tracking.

## Security and privacy

CodeOps uses local repository tools and may install lifecycle hooks. Codex requires non-managed hooks to be reviewed and trusted before they run. CodeOps does not upload project content through telemetry; its optional outcome metrics are local, content-free, documented, and disabled by default.

## License

[MIT](LICENSE)
