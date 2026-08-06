# Preflight Report: Native Windows Support

> **Status**: PASS — ready for execution within the documented Windows 11 boundary
> **Iteration**: 2 (bounded full re-scan after authorized fixes)
> **Artifact**: Full implementation plan at `plans/native-windows-support/`
> **Original Artifact Git Tree**: `be216f4463050e9b2888204e4010858399dd46fb`
> **Audit Target**: `plans/native-windows-support/` (all ten original plan documents)
> **Modification Set**: `plans/native-windows-support/`, `plans/codex-port/01-requirements.md`,
> `plans/codex-port/00-ambiguity-register.md`
> **Scope Mode**: Strict — RD-022 and RD-023 only
> **Codebase Grounded**: 10 plan documents, 30+ source/test/config references checked, 72 execution tasks reconciled
> **Last Updated**: 2026-08-06 18:18 +02:00

## Codebase Context Summary

**Repository:** CodeOps for Codex, plugin version 0.4.0

**Tech Stack:** Python standard-library runtime plus PyYAML development validation, Bash compatibility
launchers, PowerShell as the proposed Windows bootstrap, JSON/Markdown durable artifacts, and
GitHub Actions.

**Architecture:** Skills define reusable workflows; Python owns traceability state and several
utilities; Bash currently owns hooks, migration, roadmap, worktree, and repository-verification
entry paths. Traceability mutation uses fail-closed locks, journals, recovery images, and Linux
`/proc` process identity.

**Context Documents:** `AGENTS.md`; `plans/codex-port/01-requirements.md` and
`00-ambiguity-register.md`; GitHub issues #2 and #3; current hooks, state, migration, roadmap,
worktree, verification, outcome, agent, test, and CI files; Codex 0.146.0 hook configuration;
GitHub Actions runner-image definitions; relevant Microsoft Windows API documentation.

**Key Observations:**

- The plan's 72 task IDs and per-phase counts reconcile exactly, and local Markdown links pass.
- The current owner proof is Linux-specific at `scripts/codeops_state_lib/transitions.py:297-341`.
- Current CI is Ubuntu-only at `.github/workflows/ci.yml:10-23`.
- Codex 0.146.0 supports the proposed `commandWindows` hook field.
- Current Python sources use PEP 604 unions and built-in generics, establishing a Python 3.10 parser floor.
- No canonical traceability target exists for this flat plan, so deterministic graph readiness is
  unavailable; this is a semantic, codebase-grounded audit.

**Selected Domain Lenses:** Distributed/concurrent; data/migration. Compiler/language, financial,
and web-application lenses are not applicable.

## Iteration 1 Summary by Dimension

| # | Dimension | Findings | Highest Severity |
|---:|---|---:|---|
| 1 | Ambiguities | 2 | 🟠 MAJOR |
| 2 | Implicit Assumptions | 0 | — |
| 3 | Logical Contradictions | 1 | 🟠 MAJOR |
| 4 | Completeness Gaps | 1 | 🟠 MAJOR |
| 5 | Dependency Issues | 0 | — |
| 6 | Feasibility Concerns | 2 | 🟠 MAJOR |
| 7 | Testability | 2 | 🟠 MAJOR |
| 8 | Security Blind Spots | 1 | 🟠 MAJOR |
| 9 | Edge Cases | 1 | 🟠 MAJOR |
| 10 | Scope Creep Indicators | 0 | — |
| 11 | Ordering & Sequencing | 0 | — |
| 12 | Consistency | 1 | 🟠 MAJOR |
| 13 | Codebase Alignment | 2 | 🟠 MAJOR |

Secondary dimensions are cross-referenced inside findings rather than double-counted.

## Iteration 1 Summary by Severity

| Severity | Count | Status |
|---|---:|---|
| 🔴 CRITICAL | 0 | None |
| 🟠 MAJOR | 12 | All resolved and rechecked in iteration 2 |
| 🟡 MINOR | 1 | Resolved and rechecked in iteration 2 |
| 🔵 OBSERVATION | 0 | None |

---

## Major Findings

### PF-001: The Python compatibility contract accepts interpreters that cannot parse CodeOps 🟠 MAJOR

**Dimension:** 13 — Codebase Alignment (also 2 and 3)

**Location:** `00-ambiguity-register.md:10,27`; `03-01-runtime-preflight-and-hooks.md:21-24,84-85`;
`07-testing-strategy.md:27-28`; `03-04-certification-and-release.md:95`

**Codebase Evidence:** `scripts/codeops_state_lib/transitions.py:62,73-74,87` and
`scripts/codeops_state_lib/v2.py:171-174` use PEP 604 unions; built-in generic annotations are
widespread. Those files require Python 3.10+ to parse, while the plan probes only major version 3.

**Problem:** Python 3.0-3.9 can be declared READY and then fail before a workflow starts. This
invalidates the approved runtime assumption rather than merely omitting a test.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Set an explicit Python `>=3.10` floor; update the owning RD/AR, bootstrap, tests, CI, and docs | Transparent, deterministic, matches shipped syntax | Requires explicit authority to revise governing `plans/codex-port/` artifacts |
| B | Define “functional” through a complete shipped-runtime capability/import sentinel, without a numeric floor | Preserves no-minor-pin intent | Obscures a real language dependency and can miss unimported paths |

**Recommendation:** Option A. A parser dependency should be a public prerequisite, not inferred by
a sentinel. Applying it requires explicit expansion of the modification set to the governing
RD/AR documents.

**Confidence:** High — direct parser-syntax evidence. **Hardening:** Option B survived but ranked
second. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A; authorize the listed governing-document expansion.

### PF-002: The prerequisite result is not a closed platform × mode × input contract 🟠 MAJOR

**Dimension:** 1 — Ambiguities (also 8)

**Location:** `03-01-runtime-preflight-and-hooks.md:26-31,74-92,121-132`;
`07-testing-strategy.md:34-37,85`

**Codebase Evidence:** Codex hook inputs expose session ID, cwd, model, and permission mode, but the
plan must still define how those facts map into readiness. The plan declares `session`, `read`, and
`mutation` modes without enumerating every check/status/exit outcome. `native-windows` has an
undefined “not applicable” state, ST-11 permits either exit 1 or BLOCKED, and mutation's explicit
recheck list omits `sandbox` and ambiguously omits `codex-native`.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Add one normative platform × mode × input-class matrix, including attestation rules and every safety-affecting mutation recheck | One policy owner; deterministic specs | Larger design table |
| B | Split session/read/mutation into separate closed commands | Narrow interfaces | Duplicates policy and still needs equivalence rules |

**Recommendation:** Option A. Treat malformed contract input as exit 1; well-formed failed
prerequisites as BLOCKED/exit 2; rerun `sandbox` and `codex-native` for mutation.

**Confidence:** High. **Hardening:** split commands remained viable but did not remove the need for
a matrix. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-003: The Windows host epoch is not a stable process-ownership proof 🟠 MAJOR

**Dimension:** 6 — Feasibility Concerns (also 9 and 13)

**Location:** `03-03-state-and-filesystem-safety.md:29-52`;
`07-testing-strategy.md:43-46`; `99-execution-plan.md:95-100`

**Codebase Evidence:** Linux compares an exact kernel boot ID and process start ticks at
`scripts/codeops_state_lib/transitions.py:297-341`; recovery proceeds only when absence is proven
at `:1266-1267` and `:1410-1418`. The proposed Windows value is wall clock minus uptime, which
varies with sampling precision, clock correction, sleep, and hibernation.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Use exact `{backend, pid, GetProcessTimes creation FILETIME}` on Windows and omit `hostEpoch` there | Direct PID-reuse proof; no heuristic equality | Revises target AR-9's chosen shape |
| B | Identify and specify a genuinely stable native boot identifier, including Fast Startup/hibernate behavior | Retains a boot discriminator | No supported source is presently established; more API surface |

**Recommendation:** Option A. Creation FILETIME is the exact property issue #2 needs. Do not use a
tolerance around derived boot time; that would turn absence proof into a heuristic.

**Confidence:** Medium-high — a documented stable boot identifier could change the choice.
**Hardening:** tolerance was rejected. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-004: Prerequisite enforcement misses the actual mutating boundaries 🟠 MAJOR

**Dimension:** 4 — Completeness Gaps (also 5 and 11)

**Location:** `03-01-runtime-preflight-and-hooks.md:117-119`;
`99-execution-plan.md:84-101,164-181`; ST-45 at `07-testing-strategy.md:85`

**Codebase Evidence:** `scripts/codeops_state.py:22-33` exposes direct mutating commands;
`scripts/codeops_state_lib/v2.py:293-330` dispatches upgrade, transition, and recovery without a
Windows prerequisite. The plan adds skill instructions in Phase 4 but no early task gates these
public command/writer boundaries, even though Phase 2 expects final-before-write behavior.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Gate every shipped mutating command and final write/replace boundary early; retain hooks/skills as defense in depth; move ST-12 green ownership to Phase 4 | Enforces the contract at authority boundaries | Requires shared plumbing across writers and wrappers |
| B | Move every skill integration task into Phase 1 | Makes ST-12 green earlier | Couples Phase 1 to control layers not yet built |

**Recommendation:** Option A. A skill-level check cannot protect direct CLI calls or a condition
that changes between check and write.

**Confidence:** High. **Hardening:** skill-only enforcement was rejected as inconsistent with
RD-022 and issue #3. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-005: `windows-latest` is not the Windows 11 host that preflight certifies 🟠 MAJOR

**Dimension:** 13 — Codebase Alignment (also 5 and 6)

**Location:** `03-01-runtime-preflight-and-hooks.md:83-85`;
`03-04-certification-and-release.md:20-44`; `07-testing-strategy.md:31,80,86`;
`99-execution-plan.md:213-217`

**Codebase Evidence:** GitHub's runner-images definition currently maps `windows-latest` to
Windows Server 2025, while the plan blocks every non-Windows-11 host. See
<https://github.com/actions/runner-images/blob/main/README.md#available-images>.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Use one explicit Windows 11 runner for all Windows CI (hosted Arm64 if fully compatible, otherwise self-hosted) | Directly exercises the certified host | Hosted architecture may not match; self-hosting adds operations |
| B | Keep Windows Server CI for adapter/unit coverage and add a distinct automated Windows 11 prerequisite/workflow gate | Separates broad adapter coverage from the support claim | Adds a second Windows lane |

**Recommendation:** Option A. Use an explicit Windows 11 runner and keep the implementation,
automated gate, real-host evidence, and support claim on the same operating-system boundary. Do
not add a Windows Server compatibility lane or CI-only bypass.

**Confidence:** High. **Hardening:** simplified after the user confirmed that CodeOps on Windows
will be used on Windows 11. **Challenger:** previously preferred a separate Server lane, but that
extra boundary is unnecessary under the confirmed product scope.

**User Decision:** Resolved — use Windows 11 only; do not add Windows Server support or a separate
Server CI lane. User clarification on 2026-08-06: “CodeOps on Windows will be used on Windows 11.”

### PF-006: Specification ownership and execution evidence conflict 🟠 MAJOR

**Dimension:** 12 — Consistency (also 7 and 11)

**Location:** `03-02-portable-control-layer.md:95-99`;
`03-03-state-and-filesystem-safety.md:111-117`; `07-testing-strategy.md:100-114`;
`99-execution-plan.md:43-66,84-89,119-125,160-166,200-230`

**Codebase Evidence:** The documents variously assign ST-21-27 to portable/state, ST-35/36 to
portable/workflow, and ST-39/40 to two modules. Phase 1 requires ST-12 green before Phase 4
implements skill enforcement. The strategy declares `test_windows_certification_impl.py`, but no
Phase-5 task creates or runs it.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Create one canonical primary ST → module → phase mapping, mark later uses as regression reuse, move ST-12 green to Phase 4, and add the missing certification implementation-test task | Auditable ownership; preserves phase-local tests | Requires coordinated edits across several plan documents |
| B | Put ST-31-40 in one portable module and remove workflow modules | Simpler mapping | Weakens workflow-phase specification ownership and failure localization |

**Recommendation:** Option A.

**Confidence:** High. **Hardening:** duplicate symptoms were consolidated into one ownership root
cause. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-007: The plan's own commands violate its native-Windows interpreter contract 🟠 MAJOR

**Dimension:** 3 — Logical Contradictions (also 12)

**Location:** `00-index.md:36-45`; `03-02-portable-control-layer.md:53-55`;
`99-execution-plan.md:29-35`

**Codebase Evidence:** The quick reference calls literal `python` even when only `py -3` may be
available. The mandatory execution timestamp uses POSIX `date '+%Y-%m-%d %H:%M'`, which fails as a
PowerShell `Get-Date` invocation on the declared native host.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Provide tested host-specific bootstrap/interpreter and timestamp recipes, or one portable helper that owns both | Executable on each host; matches AR-3 | More than one displayed recipe unless a helper is added |

**Recommendation:** Option A. Adding literal `python` or Bash `date` as prerequisites was rejected
because it contradicts the approved boundary.

**Confidence:** High. **Hardening:** a portable helper may be cleaner than duplicated prose.
**Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-008: The retry policy requires an error distinction Windows cannot prove 🟠 MAJOR

**Dimension:** 6 — Feasibility Concerns (also 1 and 9)

**Location:** `03-03-state-and-filesystem-safety.md:67-75,100-109`;
`07-testing-strategy.md:54-57`; `99-execution-plan.md:99,107`

**Codebase Evidence:** Generic Windows `ACCESS_DENIED`/Python `PermissionError` may represent a
persistent ACL/read-only policy or handle/filter interference. The plan simultaneously says to
retry transient access violations and never retry permission-policy failures, without an observable
causal discriminator.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Retry only unambiguous sharing/lock codes; never retry generic `ACCESS_DENIED`; enumerate the closed code list and schedule | Preserves the no-policy-retry invariant | Some transient antivirus failures may fail immediately |
| B | Retry `ACCESS_DENIED` within the same bounded budget regardless of cause, and revise AR-10 accordingly | More resilient to ambiguous filter behavior | Delays permanent failures and weakens the stated policy distinction |

**Recommendation:** Option A.

**Confidence:** High. **Hardening:** no reliable probe was found that establishes the kernel error's
cause. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A.

### PF-009: Reparse-point substitution can escape containment between check and replace 🟠 MAJOR

**Dimension:** 8 — Security Blind Spots (also 9)

**Location:** `03-03-state-and-filesystem-safety.md:60-96`;
`07-testing-strategy.md:33,53,85`; `99-execution-plan.md:98-100,107-109`

**Codebase Evidence:** Current recovery resolves and then later reads/writes by pathname at
`scripts/codeops_state_lib/transitions.py:1041-1047,1605-1659`. Normal Windows opens follow
reparse targets; a junction/symlink can change after lexical/resolution checks. Microsoft documents
reparse behavior and `FILE_FLAG_OPEN_REPARSE_POINT` at
<https://learn.microsoft.com/en-us/windows/win32/fileio/reparse-points-and-file-operations>.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Reject reparse components, hold root/parent handles, validate volume/file IDs and reparse state, and retain the binding through replace/recovery | Closes the race at the authority boundary | More native API code and tests |
| B | Certify only reparse-free workspaces and immediately revalidate at writes | Smaller implementation | Weaker against concurrent local substitution; still requires boundary checks |

**Recommendation:** Option B, proportionately narrowed to the confirmed trusted local Windows 11
developer environment: certify fixed local NTFS, reject workspace reparse components, and repeat
containment/reparse validation immediately at each write/recovery boundary. A hostile concurrent
local actor is outside the certified threat model.

**Confidence:** High for the narrowed boundary. **Hardening:** the heavier handle-pinning design
was rejected after the user directed the plan not to overcomplicate local Windows 11 support.
**Challenger:** previously preferred enhanced A under a hostile-local-actor threat model.

**User Decision:** Resolved — apply the narrowed Option B.

### PF-010: Canonical strings do not prevent Windows path aliases and journal collisions 🟠 MAJOR

**Dimension:** 9 — Edge Cases (also 8 and 13)

**Location:** `03-03-state-and-filesystem-safety.md:77-96`;
`07-testing-strategy.md:51-57,83`; `99-execution-plan.md:98,107`

**Codebase Evidence:** Journal uniqueness is string-based at
`scripts/codeops_state_lib/transitions.py:1556-1587`. On ordinary Windows volumes, case-insensitive
names, directory case-sensitivity settings, 8.3 aliases, and existing file identities can cause
distinct serialized strings to address one object.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Add filesystem-aware comparison and volume/file-identity uniqueness; reject alias collisions before mutation and preserve invalid legacy state for repair | Preserves recovery ordering and hashes | Not-yet-created targets require parent identity plus name semantics |
| B | Certify only case-sensitive Windows directories | Simplifies comparison | Excludes ordinary Windows workspaces and conflicts with the intended host |

**Recommendation:** Option A.

**Confidence:** High. **Hardening:** the design must explicitly cover not-yet-created targets.
**Challenger:** converged on A.

**User Decision:** Resolved — apply Option A proportionately using filesystem-aware comparison and
collision rejection; do not add a general-purpose Windows namespace subsystem.

### PF-011: Branch-coverage promises are not measured or enforced 🟠 MAJOR

**Dimension:** 7 — Testability

**Location:** `07-testing-strategy.md:8-14,147-155`;
`99-execution-plan.md:61-76,103-111,143-152,186-194,219-230`

**Codebase Evidence:** `requirements-dev.txt:1` contains only PyYAML;
`.github/workflows/ci.yml:18-23` installs that file; `scripts/validate-codex.sh:305` runs plain
`unittest`. No tool collects branch coverage or fails below 95%/90%, so all 72 tasks can complete
without evaluating the stated targets.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Add pinned branch-coverage tooling, explicit source scopes, reviewed exclusions, portable combine behavior, and fail-under thresholds to CI/full verification | Makes the existing promises executable | Adds dependency/configuration and requires careful platform combines |
| B | Remove percentages and replace them with a closed branch/scenario inventory mapped to ST cases | Dependency-free and behavior-focused | Cannot reveal unanticipated untested branches |

**Recommendation:** Option B. Remove the unenforced percentages and make the existing closed ST
inventory plus explicit fault-boundary checklist the acceptance authority. This matches the
repository's dependency-light verification model.

**Confidence:** High. **Hardening:** the heavier coverage dependency was rejected after the user
directed the plan not to overcomplicate Windows 11 support. **Challenger:** previously preferred A.

**User Decision:** Resolved — apply Option B.

### PF-012: Real-host evidence is a schema-valid self-report, not a proof chain 🟠 MAJOR

**Dimension:** 7 — Testability (also 4 and 8)

**Location:** `03-04-certification-and-release.md:48-69`;
`99-execution-plan.md:224-227`

**Codebase Evidence:** The plan specifies a JSON manifest and hashes but no capture mechanism,
candidate-artifact provenance, supporting outputs, sanitization procedure, or validator binding.
A hand-authored conforming JSON file could pass without an installed native run, which does not
satisfy governing RD-023 at `plans/codex-port/01-requirements.md:120-129`.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Specify and task a reproducible capture runner/procedure binding candidate artifact hash, commit/version, exact commands, outputs/exit codes, native/prohibited-runtime observations, sanitized hash-addressed artifacts, reviewer provenance, and separate desktop attestation | Establishes auditable execution evidence | Adds operational and sanitization work |

**Recommendation:** Option A. Schema-only assertions were rejected because they prove shape, not execution.

**Confidence:** High. **Hardening:** cryptographic signing was considered unnecessary; retained
artifact bindings are sufficient. **Challenger:** converged on A.

**User Decision:** Resolved — apply Option A with a compact deterministic capture command and
sanitized supporting records.

## Minor Findings

### PF-013: Attestation expiry and retention are promised but undefined 🟡 MINOR

**Dimension:** 1 — Ambiguities

**Location:** `03-01-runtime-preflight-and-hooks.md:97-107`; `99-execution-plan.md:56`

**Problem:** The record binds creation time, “stale” records are ignored, and the task requires
expiry/refresh, but no TTL, clock-skew rule, cleanup policy, or refresh boundary is defined.

**Options:**

| Option | Description | Pros | Cons |
|---|---|---|---|
| A | Define session-lifetime validity, future-time rejection, bounded retention, and cleanup; mutation still reruns all safety checks | Matches the session-scoped design | Needs explicit session-end/orphan cleanup semantics |
| B | Define an exact UTC TTL and skew allowance | Simple time rule | Arbitrary expiry can interrupt a valid long session |

**Recommendation:** Option A.

**User Decision:** Resolved — apply Option A.

## Adversarial Review Check

- Creation-time assumptions were challenged against the current runtime parser and external host contracts.
- Windows process, path, replacement, reparse, and recovery semantics received explicit
  distributed/concurrent and data/migration review.
- The independent challenger reviewed the complete major-finding batch without seeing the lead's picks.
- No optional additions were promoted into findings under strict scope.

## Iteration 2 Resolution Verification

| Finding | Resolution evidence | Result |
|---|---|---|
| PF-001 | Governing RD/AR, bootstrap, CI, tests, and docs require Python 3.10+ without a patch pin | Resolved |
| PF-002 | Closed mode/input matrix now defines per-mode check behavior, entrypoint and complete target-set inputs, exit classes, and transaction-only checks | Resolved |
| PF-003 | Windows identity is exact `{pid, creationFileTime}` from `GetProcessTimes`; no derived host epoch | Resolved |
| PF-004 | Registered command boundaries own mutation gates; hooks and skills are defense in depth only | Resolved |
| PF-005 | The certification lane is explicitly native Windows 11; no Windows Server lane is claimed | Resolved |
| PF-006 | Every ST has one canonical owner; regression reuse is labeled; the certification implementation suite has an execution task | Resolved |
| PF-007 | Windows examples resolve the certified interpreter and use native PowerShell timestamps | Resolved |
| PF-008 | Only WinError 32/33 are retried on the fixed schedule; generic access denial fails closed | Resolved |
| PF-009 | Every existing root-to-target, temp, and recovery component is checked for reparses immediately before writes; hostile post-check local substitution is explicitly out of scope | Resolved |
| PF-010 | NTFS-aware volume, long-name, identity, case, and 8.3 collision rules block aliases | Resolved |
| PF-011 | ST-1–ST-54 is the sole closed coverage authority; no unenforced percentage or undeclared fault-ID inventory remains | Resolved |
| PF-012 | Candidate-bound capture, sanitized supporting records, command traces, hashes, provenance, and deterministic validation form the evidence chain | Resolved |
| PF-013 | Attestations are same-session only, reject future timestamps, and clean orphan records after seven days | Resolved |

The iteration-2 scan also closed three drafting residues found during challenge: passive WSL refusal
now occurs before host dispatch without invoking WSL; nested pre-existing reparses are rejected; and
the preflight API carries the registered entrypoint plus complete mutation target set.

Native-safe verification on Windows 11 passed `git diff --check`, local Markdown-link validation,
the 72-task count, stale-contract searches, and canonical ST ownership review. The current five
repository `.sh` commands are not native-Windows entrypoints: attempting the existing baseline on
Windows exposed its known POSIX assumptions (`/proc`, shell executables, and environment-specific
Python dependencies). Those failures are current-state evidence for this plan, not a passing
Windows gate. No WSL result is accepted as verification or certification evidence.

## Verdict

✅ **PREFLIGHT PASSED — 0 critical, 0 major, and 0 minor findings remain.** The plan is ready for
execution within its explicit boundary: native Windows 11, Python 3.10+, trusted fixed local NTFS,
and no WSL or Git Bash runtime/fallback/certification path. The roadmap hook is inert because
`plans/00-roadmap.md` does not exist.
