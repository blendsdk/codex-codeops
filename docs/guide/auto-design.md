# Delegated technical design

`--auto-design` delegates eligible technical choices to CodeOps for one invocation. It is useful
when you want the workflow to compare viable designs, choose the strongest supported option, and
record why without stopping for every implementation-level choice.

It is supported by `make-requirements`, `make-plan`, `preflight`, and `exec-plan`.

```text
Use make-plan --auto-design for the invoice-reconciliation feature.
```

## What CodeOps may decide

Eligible choices include implementation architecture, algorithms, internal interfaces,
dependencies, storage techniques, compatibility approaches, and verification strategy—provided
the decision stays within confirmed product scope and granted authority.

Consequential decisions record evidence, alternatives, counterarguments, confidence, and reopen
triggers. High-impact choices receive an independent challenge when an eligible agent is available.

## What remains yours

CodeOps still escalates decisions about:

- product behavior, acceptance criteria, and scope;
- security or access policy and risk acceptance;
- destructive migration and irreversible operations;
- credentials, spending, publication, deployment, or external communication; and
- permission to implement, commit, or push.

Delegated design is not delegated authority. It also cannot approve a proposed scope expansion.
