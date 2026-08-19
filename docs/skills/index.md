# Skills

CodeOps skills are multi-step workflows that Codex loads when your request matches their purpose.
Name a skill explicitly when you want predictable dispatch.

## Core delivery workflow

| Skill | Use it for |
|---|---|
| [`grill-me`](grill-me.md) | Resolve a design tree before requirements or planning |
| [`make-requirements`](make-requirements.md) | Discover, add, or review formal requirements |
| [`retro-requirements`](retro-requirements.md) | Reconstruct requirements from an existing implementation |
| [`make-plan`](make-plan.md) | Produce specifications, tests, and an executable plan |
| [`preflight`](preflight.md) | Run an adversarial, codebase-grounded audit |
| [`exec-plan`](exec-plan.md) | Implement and verify an existing CodeOps plan |
| [`roadmap`](roadmap.md) | Track feature and portfolio lifecycle state |

## Project operations

| Skill | Use it for |
|---|---|
| [`setup-codeops`](setup-codeops.md) | Initialize or migrate the CodeOps layout |
| [`setup-routing`](setup-routing.md) | Configure risk-based specialist agents |
| [`analyze-project`](analyze-project.md) | Create concise, grounded `AGENTS.md` guidance |
| [`techdocs`](techdocs.md) | Maintain technical architecture documentation and ADRs |
| [`upgrade-plan`](upgrade-plan.md) | Upgrade legacy requirement and plan artifacts |

## Repository maintenance

| Skill | Use it for |
|---|---|
| [`clean-comments`](clean-comments.md) | Improve source documentation without changing behavior |
| [`git-commit`](git-commit.md) | Verify, stage, commit, and optionally push safely |
| [`github-issues`](github-issues.md) | Inspect or explicitly change GitHub issue state |
| [`outcome-review`](outcome-review.md) | Review local workflow evidence and rework patterns |

Flags are parsed as exact standalone tokens. See [flags and modes](/reference/flags) before
combining delegated design, scope exploration, resume, or commit behavior.
