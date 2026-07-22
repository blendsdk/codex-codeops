# CodeOps for Codex — Port Program

> **Status:** Discovery and architecture planning
> **Source baseline:** CodeOps for Claude Code 3.12.0
> **Target:** A Codex-native CodeOps implementation that meets or exceeds the Claude edition for complex-system development

## Objective

Build a Codex-native edition of CodeOps that can safely drive the design and implementation of complex systems such as compilers, financial platforms, protocols, infrastructure, and web applications.

This is not a syntax port. The product must preserve CodeOps' defining behavior:

1. discover requirements;
2. recursively expose and resolve material ambiguities;
3. create grounded technical specifications;
4. recursively expose and resolve specification and plan ambiguities;
5. prove readiness before implementation;
6. execute with durable progress, verification, and independent review; and
7. track the project across features and sessions.

## Non-negotiable product invariant

> Implementation may begin only when every material requirement, architectural decision, interface, invariant, failure mode, and verification obligation in scope is resolved or explicitly deferred by the user with its risk recorded.

A material ambiguity is one for which two plausible answers could change observable behavior, language semantics, data integrity, security, financial outcomes, public contracts, persistence, concurrency, recovery, compatibility, performance requirements, test expectations, architecture, operations, scope, or delivery ordering.

## Governing documents

| Document | Owns |
|---|---|
| [00-ambiguity-register.md](00-ambiguity-register.md) | Unresolved and resolved port-level decisions |
| [01-requirements.md](01-requirements.md) | Behavioral and product requirements |
| [02-current-state.md](02-current-state.md) | Evidence from the Claude implementation and Codex platform |
| [03-01-target-architecture.md](03-01-target-architecture.md) | Codex-native plugin architecture and durable state model |
| [03-02-workflow-and-gates.md](03-02-workflow-and-gates.md) | Recursive refinement, traceability, readiness, execution, and recovery |
| [03-03-port-mapping.md](03-03-port-mapping.md) | Keep/adapt/replace/remove decisions for the current surface |
| [07-testing-strategy.md](07-testing-strategy.md) | Parity, conformance, adversarial, and end-to-end validation |
| [99-execution-plan.md](99-execution-plan.md) | Ordered implementation program and completion gates |

## Success definition

The Codex edition is ready for real complex-project work only when:

- all critical Claude workflows have executable Codex equivalents;
- recursive ambiguity closure is demonstrably preserved;
- requirements, specifications, tests, tasks, changes, and verification evidence are traceable;
- project and portfolio status can be reconstructed without conversation history;
- Codex hooks, skills, agents, prompts, and plugin packaging are verified against the current product;
- interruption and resumption do not corrupt workflow state;
- the project passes compiler, financial-system, and web-application scenario evaluations; and
- no claimed parity depends on an untested Claude compatibility behavior.

## Scope boundary

This program creates the Codex implementation under this `codex/` directory. The sibling Claude repository is an evidence source and behavioral oracle; it is not modified by the port.

