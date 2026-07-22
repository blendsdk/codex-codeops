# Workflow and Gates

## Recursive workflow

```text
Seed intent or existing system
  → domain discovery
  → requirements set
  → requirements ambiguity closure
  → system decomposition and specifications
  → specification ambiguity closure
  → cross-system consistency and traceability audit
  → execution plan
  → plan ambiguity closure
  → readiness proof
  → specification tests and red confirmation
  → implementation
  → verification and independent review
  → acceptance and project tracking update
```

Every downstream stage may discover a defect in an upstream artifact. The system then reopens the owning gate, records the reason, updates the authoritative fact, and invalidates affected downstream readiness until revalidated.

## Gate G1 — Requirements complete

Required evidence:

- scope and exclusions;
- glossary and actors;
- behaviors and state transitions;
- domain invariants;
- failures and recovery expectations;
- security and authorization boundaries;
- measurable quality attributes;
- compatibility and operational constraints; and
- zero open material requirement ambiguities.

## Gate G2 — Specifications complete

Required evidence:

- every requirement is mapped to an owning specification;
- public and cross-component interfaces are explicit;
- data ownership and lifecycle are explicit;
- algorithms are specified where their behavior affects correctness;
- concurrency, persistence, recovery, security, and performance are addressed when applicable;
- acceptance criteria are objective;
- domain-lens reviews pass; and
- zero open material specification ambiguities.

## Gate G3 — Plan ready

Required evidence:

- every task maps to specifications and acceptance criteria;
- dependencies and ordering are coherent;
- every task has concrete deliverables and verification;
- specification-first ordering is represented where required;
- no task hides an unresolved architectural or behavioral decision;
- rollback/migration steps exist when applicable;
- cross-plan conflicts are absent; and
- zero open material plan ambiguities.

## Gate G4 — Execution entry

Required evidence:

- repository state still matches plan assumptions;
- readiness report is current;
- necessary tools and permissions are available;
- specification tests can be authored independently;
- destructive/external actions have required authority; and
- no upstream gate has been invalidated.

## Gate G5 — Task complete

Required evidence:

- durable state records implementation before verification;
- specified verification passes;
- acceptance evidence is attached;
- immutable specification tests were not weakened;
- scope drift is either absent or resolved through the ambiguity protocol; and
- progress and roadmap derivations agree.

## Gate G6 — Feature accepted

Required evidence:

- all planned tasks are verified;
- all acceptance criteria have passing evidence;
- independent review is complete;
- critical and major findings are resolved or explicitly accepted by the user;
- requirements, decisions, specifications, and docs reflect the shipped system;
- remaining risks and deferrals are explicit; and
- portfolio status is updated.

## Ambiguity protocol

For every candidate ambiguity:

1. State the unresolved question precisely.
2. Identify the authoritative artifact and affected graph nodes.
3. Establish whether the difference is material.
4. Investigate code, standards, documentation, and prior decisions before asking.
5. Present only viable options, trade-offs, and a grounded recommendation.
6. Obtain an explicit decision for material ambiguity.
7. Record the decision, basis, confidence, and affected nodes.
8. Revalidate downstream gates.

Implementation discretion is allowed only when an authoritative specification explicitly defines the decision class as non-material and delegated.

## Recovery protocol

A new session reconstructs state in this order:

1. locate CodeOps configuration and layout;
2. validate artifact schemas and identifiers;
3. read current lifecycle and readiness state;
4. compare Git status/diff/log with recorded task state;
5. locate verification logs and unresolved findings;
6. detect partially implemented or stale tasks;
7. report the reconstructed state and next safe action; and
8. require user direction only when evidence conflicts materially.

Conversation history may enrich context but is never the durable source of truth.

