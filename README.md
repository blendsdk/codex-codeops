# CodeOps for Codex

CodeOps is a specification-first engineering system for building complex software with Codex. It recursively turns an idea or an existing codebase into complete requirements, explicit architectural decisions, grounded technical specifications, an ambiguity-free execution plan, verified implementation, and durable project tracking.

It is designed for work where an unstated assumption can become a correctness defect: programming languages and compilers, financial systems, protocols, distributed services, security-sensitive applications, developer tools, and substantial web applications.

> **Development status:** The plugin is installable and under active pre-1.0 validation. Core workflows, deterministic state, project tracking, domain lenses, and Codex-native routing are present; comparative complex-system evaluations remain release gates.

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

## Installation

Add the GitHub repository as a Codex marketplace, then install CodeOps:

```bash
codex plugin marketplace add blendsdk/codex-codeops --ref main
codex plugin add codeops@codeops-marketplace
```

These commands have been verified against the published repository. Start a new Codex thread after installation so skills and hooks are discovered.

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

Start a new thread after install, update, disable, or removal. See [installation details](docs/installation.md) for trust, development, and troubleshooting notes.

## Development

```bash
git clone git@github.com:blendsdk/codex-codeops.git
cd codex-codeops
./scripts/validate-codex.sh
```

The sibling Claude CodeOps repository is the behavioral baseline during the port. Codex-specific improvements are accepted only when they preserve or strengthen ambiguity closure, verification, recovery, and project tracking.

## Security and privacy

CodeOps uses local repository tools and may install lifecycle hooks. Codex requires non-managed hooks to be reviewed and trusted before they run. The production release will not upload project content through CodeOps telemetry; any outcome metrics will be local, documented, and opt-in.

## License

[MIT](LICENSE)
