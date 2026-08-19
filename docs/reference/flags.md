# Flags and modes

Flags are exact standalone tokens. Put them before any `--` sentinel used to separate free-form
target text.

## Shared workflow controls

| Flag | Skills | Effect |
|---|---|---|
| `--auto-design` | `make-requirements`, `make-plan`, `preflight`, `exec-plan` | Delegate eligible technical decisions for one invocation |
| `--explore-scope` | `make-plan`, `preflight`, `exec-plan` | Propose optional scope additions for user rulings |
| `--continue` | `grill-me`, `make-requirements`, `retro-requirements`, `preflight`, `techdocs` | Resume the matching persisted session |

## Execution commit modes

| Flag | Effect |
|---|---|
| `--ask-commit` | Ask after every verified task; this is the default |
| `--no-commit` | Never commit or prompt for a commit |
| `--auto-commit` | Commit and push each verified task through `git-commit` |

Commit modes are mutually exclusive. `--auto-design` never implies `--auto-commit`.

## Setup and archaeology controls

| Flag | Skill | Effect |
|---|---|---|
| `--dry-run` | `setup-codeops` | Preview setup or migration without writes |
| `--yes` | `setup-codeops` | Apply an unblocked preview without another confirmation |
| `--scope PATH` | `retro-requirements` | Limit archaeology to one module or package |

Natural-language modes such as `review requirements`, `show roadmap`, and `report-only comments`
are documented on their respective skill pages.
