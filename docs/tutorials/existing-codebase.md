# Reverse-engineer an existing codebase

Use this path when implementation exists but trustworthy requirements do not.

## 1. Bound the investigation

For a large repository, start with one coherent module:

```text
Use retro-requirements --scope packages/identity to reconstruct the current behavior.
```

The scope should contain enough code to observe complete contracts. If a boundary hides a required
dependency, expand it explicitly rather than inferring behavior from a call site.

## 2. Review evidence confidence

The reconstruction classifies behaviors according to the strength of code, tests, configuration,
documentation, and runtime evidence. Pay special attention to behavior inferred from only one weak
source.

Long investigations can resume in a new thread:

```text
Use retro-requirements --continue.
```

## 3. Triage bugs and features

Before turning observations into requirements, decide whether suspicious behavior is:

- intended and therefore a requirement;
- a defect that a replacement must not preserve; or
- unresolved and still requiring evidence or a product decision.

Do not accept “the code does it” as proof of intent.

## 4. Formalize and audit

Feed the approved reconstruction brief into requirements discovery:

```text
Use make-requirements from the identity reconstruction brief.
Preserve its confidence labels and unresolved decisions.
```

Then run `preflight` on the requirements. Only after the requirements pass should `make-plan`
design changes or a replacement.
