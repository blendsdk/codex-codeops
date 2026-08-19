# Introduction

CodeOps is for engineering work where an unstated assumption can become a correctness defect. It
adds structured discovery, planning, execution, review, and project tracking workflows to Codex.

## When to use it

CodeOps is most valuable for:

- systems with financial, security, concurrency, migration, or compatibility risk;
- features that cross several components or require architectural decisions;
- existing systems whose actual behavior must be reconstructed before replacement;
- long-running work that must resume safely across multiple Codex threads; and
- teams that need reviewable requirements and plans rather than conversation-only decisions.

For a tiny, reversible change, asking Codex directly may be sufficient. CodeOps intentionally adds
ceremony where ambiguity or rework would be expensive.

## What the plugin provides

- Sixteen user-invoked skills for requirements, plans, execution, review, documentation, Git, and
  project operations.
- Always-on coding, testing, security, and reporting standards through the trusted session hook.
- A repository-local artifact layout that preserves decisions and progress outside the chat.
- Deterministic helpers for plan state, migrations, roadmap synchronization, and validation.
- Optional risk- and capability-based routing to specialist Codex agents.

## What it does not replace

CodeOps does not replace product ownership, repository policy, code review, CI, or deployment
approval. It does not grant Codex permission to publish, spend money, use credentials, or take
destructive actions. Those boundaries remain user-owned even when delegated design is active.

## Continue

1. [Install CodeOps](/installation).
2. [Verify that it loaded](/guide/verify).
3. [Run the quick start](/tutorial).
