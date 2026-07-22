# Domain-lens selection

Before requirements discovery and again before specification preflight, classify the system using repository evidence and user intent. Select every applicable lens; complex systems commonly require several.

| Evidence | Lens |
|---|---|
| Grammar, parser, IR, optimizer, type checker, evaluator, query planner, protocol codec | compiler and language |
| Money, balances, invoices, payments, pricing, tax, ledger, reconciliation | financial system |
| Browser UI, HTTP API, sessions, roles, tenant resources | web application |
| Threads, workers, queues, events, replicas, workflows, caches, multiple nodes | distributed and concurrent |
| Persistent schema, migration, backfill, import/export, retention | data and migration |

Always apply universal CodeOps ambiguity categories as well. Domain lenses add questions; they never replace scope, actors, failure behavior, security, quality attributes, traceability, or verification.
