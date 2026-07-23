# Migration and Invalidation: Dependency-Aware Readiness

> **Document**: 03-03-migration-and-invalidation.md
> **Parent**: [Index](00-index.md)

## Overview

Schema 1 remains readable with exact legacy semantics. Schema 2 is entered only through an explicit
upgrade that preserves facts it can prove and asks the user to resolve relationship meaning it
cannot prove. Semantic revisions then make downstream invalidation deterministic. (AR-8, AR-9)

## Compatibility Boundary

- Schema-1 validation, feature readiness, status, and output remain regression-compatible.
- That guarantee applies to legitimate configured/conventional roots and explicitly isolated
  fixture roots. Broad repository fixture ingestion is a corrected discovery defect and the sole
  authorized schema-1 discovery delta. (AR-28)
- Schema-1 graphs cannot participate in typed target closure.
- Mixed repositories are inspectable.
- A cross-feature typed dependency entering schema 1 blocks with an upgrade requirement.
- No legacy `links` value is assigned a typed meaning heuristically. (AR-9)

## Upgrade Protocol

The executable interface is:

```text
codeops_state.py traceability-upgrade --root ROOT --feature FEATURE --preview FILE
codeops_state.py traceability-upgrade --root ROOT --feature FEATURE \
  --apply --preview FILE --resolutions FILE
```

`--preview` writes no project artifact and emits a versioned JSON document containing source graph
hash, preserved nodes, candidate typed edges, unresolved edge/source classifications, proposed
schema-2 destination, and blocker codes. `--apply` requires the unchanged preview hash and a
versioned resolutions JSON object that supplies one choice for every unresolved item and no
unknown choice. Human output summarizes the same machine result. Exit 0 means preview produced or
upgrade committed; exit 1 means durable project state is byte-identical; exit 2 means a write
occurred and explicit recovery is required. (AR-21, AR-29)

The upgrade workflow:

1. Discovers schema-1 graphs and validates them without modification.
2. Produces a deterministic preview containing preserved nodes, candidate relationships,
   unresolved relationship conversions, and proposed schema-2 paths.
3. Collects explicit user decisions for every ambiguous conversion.
4. Writes a complete schema-2 graph atomically.
5. Preserves node IDs, statuses, paths, evidence, and risk.
6. Revalidates and proves idempotence.
7. Leaves the original state recoverable until successful verification.

Preview is read-only. Apply refuses incomplete resolutions, path escape, partial output, and
identity collisions. The old schema-1 graph is retained as `<name>.schema1.backup` until schema-2
validation and the confirmed repository gate pass; a successful subsequent idempotent apply
reports no change. Failed or interrupted apply removes an uncommitted temp file and retains the
backup/original. An existing non-identical backup is a collision and blocks without overwrite.
Backup deletion is a later explicit cleanup action, never part of apply. A post-replace validation
failure must restore the validated before-image before returning exit 1; if restoration cannot be
proven, return exit 2 `recovery-required` with the journal intact. (AR-9, AR-21, AR-29)

## Semantic Revision

Revision source fields, normalization, digest algorithm, ordering, and snapshot shape are
normatively owned by `03-01-graph-schema.md`. Upgrade preview requires source classification for
every semantic node, including multiple nodes sharing one Markdown file; the engine never guesses
a heading. (AR-8, AR-18)

## Atomic Transition Protocol

All lifecycle and validation mutations call one reusable state-transition module. Given canonical
target, expected status/revision, requested new status, gate, and snapshot additions, it:

1. Acquires an exclusive sibling lock using create-exclusive semantics.
2. Reloads and validates the graph and compares expected status/revision.
3. Computes revision and snapshot updates as one in-memory graph.
4. Serializes deterministic JSON to a same-directory uniquely named temp file.
5. Flushes and `fsync`s the temp file where supported.
6. Atomically replaces the graph, then syncs the parent directory where supported.
7. Reopens and validates the committed graph before reporting success.
8. On success or byte-identical failure, releases/archives normal lock and temp state. On
   `recovery-required`, retains the journal and recovery lock/evidence; only
   `transition-recover` may resolve and archive them.

An existing live lock blocks without writing and reports its owner metadata. A stale lock is never
silently removed; recovery requires an explicit command after proving no owner process remains.
Expected-state mismatch is compare-and-swap failure. Multi-graph transitions are not claimed
atomic: they are ordered, journaled operations whose incomplete journal blocks readiness until
explicit recovery completes or rolls back every member. (AR-19)

The transition journal is versioned JSON stored beside the initiating graph and contains operation
ID, ordered graph identities, before hashes, intended after hashes, committed members, and recovery
direction. It contains no artifact content. (AR-19)

### Recovery contract

`transition-recover` is the sole stale-lock and journal recovery path. A recovery request names the
operation and journal, supplies every expected hash, chooses `roll-forward` or `rollback`, and
supplies OS process identity/start metadata used to prove the prior owner is absent. Unsupported
platforms that cannot prove absence refuse automatic stale-lock removal.

Rollback restores validated before-images in reverse commit order. Roll-forward verifies every
already committed after-hash and commits remaining members in journal order. Neither direction
overwrites an unexpected current graph or non-identical backup. After recovery, every graph and
cross-graph invariant is validated before journal/lock archival. Repeating an identical completed
request returns `already-recovered`; changing direction after any recovery commit is refused.
(AR-29)

## Invalidation Rules

- Revision mismatch along `depends-on`, `consumes-contract`, or applicable trace ownership makes
  the dependent stale.
- `related` never propagates staleness.
- `release-coupled` invalidates release-gate evidence only.
- Reopened material ambiguities and findings propagate through `affected-by`.
- Group members invalidate atomic group readiness.
- Status and snapshot transitions use the atomic protocol above. (AR-8, AR-19)

## Error Handling

| Error Case | Handling Strategy | AR Ref |
|---|---|---|
| Ambiguous legacy link | Keep preview unresolved and require user classification | AR-9 |
| Upgrade interrupted before replace | Preserve original graph and discard/recover temporary output | AR-9 |
| Revision source unavailable | Block approval/validation snapshot creation | AR-8 |
| Revision mismatch | Report dependent, upstream node, expected revision, and actual revision | AR-8 |
| Partially updated snapshot/status | Structural error; never claim readiness | AR-8 |
| Concurrent or stale writer | Compare-and-swap/lock failure; no implicit overwrite or lock removal | AR-19 |
| Interrupted multi-graph transition | Journal blocks readiness until explicit roll-forward/rollback | AR-19 |
| Post-replace validation fails | Restore validated before-image; otherwise exit 2 with journal intact | AR-29 |
| Backup already exists with different hash | Refuse without overwrite | AR-29 |

## Testing Requirements

Normative ownership is defined only by the ST ownership table in `07-testing-strategy.md` (AR-27).
