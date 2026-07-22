# CodeOps for Codex

CodeOps is a specification-first engineering system for building complex software with Codex. It recursively turns an idea or an existing codebase into complete requirements, explicit architectural decisions, grounded technical specifications, an ambiguity-free execution plan, verified implementation, and durable project tracking.

It is designed for work where an unstated assumption can become a correctness defect: programming languages and compilers, financial systems, protocols, distributed services, security-sensitive applications, developer tools, and substantial web applications.

> **Development status:** This repository contains the active Codex port. The workflow corpus and initial plugin package are present, but the port has not yet passed its 1.0 parity and release gates. Do not treat the current version as production-ready.

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

Codex-native traceability, readiness proofs, recovery, agent routing, and outcome evaluation are being implemented under the [port program](plans/codex-port/00-index.md).

## Installation

Installation commands will be published here after the clean-environment marketplace and plugin installation tests pass. The intended source is:

```text
git@github.com:blendsdk/codex-codeops.git
```

The release documentation will include verified install, update, disable, uninstall, and hook-trust procedures. Commands are intentionally not presented as working until the corresponding conformance tests pass.

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
