# Ambiguity Register: Native Windows Support

> **Status**: ✅ GATE PASSED — all 21 items resolved
> **Last Updated**: 2026-08-06 21:25 CEST

| # | Category | Ambiguity / Gap | Options Presented | User Decision | Status |
|---|---|---|---|---|---|
| AR-1 | Naming | What plan path owns the complete Windows effort? | `plans/native-windows-support/` / another slug | Use `plans/native-windows-support/`. | ✅ Resolved |
| AR-2 | Architecture | Should Windows support duplicate each Bash workflow in PowerShell or move reusable behavior to one cross-platform engine? | Authoritative Python modules with thin host launchers / parallel Bash and PowerShell algorithms | Use authoritative Python 3 modules. Retain thin Bash launchers where Unix compatibility needs them and add thin native PowerShell launchers where Python cannot bootstrap itself. | ✅ Resolved |
| AR-3 | Runtime | How does Windows check Python when Python may be absent? | Native PowerShell bootstrap / depend on Git Bash or WSL | Use a signed-reviewable PowerShell bootstrap that probes `py -3` and then `python`, requires Python 3.10 or newer, never installs it, and blocks mutation when unavailable. | ✅ Resolved |
| AR-4 | WSL | How should an installed WSL feature affect native Windows readiness? | Ignore installed WSL but block actual WSL execution / reject machines with WSL installed | Ignore whether WSL is installed. Never invoke or delegate to WSL; block only when CodeOps is actually executing inside WSL. | ✅ Resolved |
| AR-5 | Prerequisites | How are prerequisite results shared and enforced? | Session attestation plus write-time rechecks / every command performs the full probe | The SessionStart hook writes a session-scoped attestation under `PLUGIN_DATA`; every actual mutating command boundary reruns all safety-affecting checks immediately before its first write, and final filesystem validation repeats at each atomic write/recovery boundary. Hooks and skills remain defense in depth. | ✅ Resolved |
| AR-6 | Contract | What machine-readable prerequisite contract is stable? | Closed JSON result with stable check codes / prose-only output | Emit a versioned closed JSON result with `READY`, `WARNING`, or `BLOCKED`, ordered check records, and actionable messages. Exit 0 for READY/WARNING, 2 for BLOCKED, and 1 for malformed input or internal failure. | ✅ Resolved |
| AR-7 | Compatibility | Should CodeOps pin a Codex version for Windows? | Probe required native capabilities / guess a minimum version | Probe the required plugin, hook, native sandbox, and command capabilities. Record the certified Codex version in evidence, but do not hardcode a speculative minimum. | ✅ Resolved |
| AR-8 | Scope | Which shell-dependent utilities are in the port? | Every shipped runtime and repository verification workflow / runtime scripts only | Port every shipped CodeOps runtime utility and the repository verification orchestration to native Python/PowerShell entry points; Bash remains a Unix compatibility launcher, not a Windows dependency. | ✅ Resolved |
| AR-9 | Concurrency | How is process ownership represented across Linux and Windows? | Versioned backend-specific identity / reinterpret Linux fields on Windows | Use versioned backend-specific records. Read existing Linux `{pid,startTicks,bootId}` records compatibly; use native Windows `{pid,creationFileTime}` identity from `GetProcessTimes`, failing closed when absence cannot be proven. | ✅ Resolved |
| AR-10 | Filesystem | How should transient Windows sharing violations affect atomic writes? | Bounded retry for unambiguous sharing/lock errors / retry generic access denial | Retry only WinError 32 (`ERROR_SHARING_VIOLATION`) and 33 (`ERROR_LOCK_VIOLATION`) on a fixed bounded schedule, then retain recovery state and fail closed. Never retry generic `ACCESS_DENIED`, validation, permission-policy, or path-safety failures. | ✅ Resolved |
| AR-11 | Paths | What durable path and generated-name rules apply? | Canonical POSIX-relative storage on fixed local NTFS with safe legacy reads / broader filesystem support | Serialize project-relative durable paths with `/`; certify a trusted fixed local NTFS workspace only when every existing component from the root through each mutation target is reparse-free; reject reserved names, aliases/collisions, trailing spaces/dots, absolute paths, and traversal before writes. Existing invalid state blocks and is never silently rewritten. | ✅ Resolved |
| AR-12 | Certification | What automated matrix is sufficient? | Ubuntu plus explicit native Windows 11 CI / multi-version or Windows Server matrix | Keep Ubuntu regression coverage and add one explicit native Windows 11 CI runner with Python 3.10 or newer. Do not add a Windows Server or Python minor-version matrix. | ✅ Resolved |
| AR-13 | Evidence | What evidence closes the Windows claim? | CI plus real Windows 11 installed-plugin evidence and desktop smoke / CI alone | Require CI plus retained, version-matched native Windows 11 CLI installed-plugin evidence and a Windows desktop installation/representative-workflow smoke test before claiming support. | ✅ Resolved |
| AR-14 | Verification | Which repository commands are the authoritative full gate? | All five `AGENTS.md` commands / a narrower subset | Use all five commands from `AGENTS.md`; provide native Python/PowerShell entry points that prove the same checks on Windows. | ✅ Resolved |
| AR-15 | Execution bootstrap (runtime) | How is task progress tracked before the plan's own Windows process-identity work makes atomic traceability transitions available? | Pause all implementation / use an explicit temporary Markdown-first bootstrap and reconcile immediately after native transition integration | User authorized implementation to proceed without WSL. Keep the execution-plan marks current, commit only verified tasks, leave graph task nodes pending, and atomically reconcile every deferred task transition immediately after Task 2.2.6 makes native transitions available; do not proceed to Task 2.2.7 until reconciliation passes. | ✅ Resolved |
| AR-16 | Test architecture (runtime) | How can specification tests control Windows host/probe/clock/attestation and hook-order outcomes without depending on implementation internals or a test-only CLI mode? | Required dependency protocols at Python orchestration boundaries / patch private functions / environment-variable simulation | Add required `PreflightDependencies` and `HookDependencies` protocols to the preflight and hook orchestrators; production CLIs construct native dependencies, while specification tests supply in-memory implementations. No test-mode branch or environment backdoor ships. | ✅ Resolved |
| AR-17 | Hook proof (runtime) | How does the checker distinguish a trusted hook invocation from a direct command boundary without trusting mutable environment variables? | Closed `hook_event` input derived from validated hook JSON / hidden environment marker / infer trust from mode | Add explicit `hook_event` to the closed request. Session requires `SessionStart`; read accepts no hook proof; mutation accepts `PreToolUse` or no hook because the registered entrypoint remains authoritative. Unknown or mismatched events are malformed input. | ✅ Resolved |
| AR-18 | Windows shell (runtime) | May native Windows hooks require separately installed PowerShell 7 when the plan declares no such prerequisite? | Built-in Windows PowerShell 5.1 / add and probe a PowerShell 7 prerequisite | Use `powershell.exe`, which is part of the Windows 11 boundary. Do not add an undeclared PowerShell 7 dependency. | ✅ Resolved |
| AR-19 | Preflight CLI (runtime) | How does the PowerShell bootstrap transport the closed preflight request to Python? | Explicit allowlisted argument array / JSON stdin | Use explicit non-abbreviated flags with repeated `--target`; reject unknown or missing fields before probes, construct production dependencies internally, emit one closed JSON result, and preserve exits 0/1/2. | ✅ Resolved |
| AR-20 | Windows hook launcher (runtime) | How can hooks execute from legal hostile plugin paths without evaluating path content? | Checked-in `-File` launcher using `$env:PLUGIN_ROOT` and `$PSScriptRoot` / inline `-Command` interpolation | Use a checked-in PowerShell `-File` launcher. The manifest contains no `${PLUGIN_ROOT}` substitution or inline script block; the launcher derives sibling scripts from `$PSScriptRoot` and forwards stdin as data. | ✅ Resolved |
| AR-21 | Process adapter API (runtime) | What public Python surface owns versioned identities and absence decisions before platform backends exist? | Immutable backend-specific identities plus a three-state result and injectable protocol / raw dictionaries and nullable booleans | Use immutable Linux/Windows identity models, `AbsenceState`, an injected `ProcessBackend`, one exact parser including legacy Linux, and centralized mismatch/malformed handling. | ✅ Resolved |

## Resolution Notes

The user explicitly accepted the complete recommendation set after the issue analysis and Windows
scope expansion, then simplified the certified boundary during preflight. WSL may be installed,
but CodeOps does not use it. Windows support means Windows 11, Python 3.10 or newer, and a trusted
fixed local NTFS workspace without reparse points; broader host/filesystem matrices are out of scope.

The confirmed repository gate is:

```bash
./scripts/validate-codex.sh
./scripts/docs-check.sh
./scripts/migration-check.sh
./scripts/roadmap-sync-check.sh
./scripts/compact-check.sh
```

On Windows, equivalent native launchers must execute the same underlying checks without Bash,
Git Bash, or WSL (AR-2, AR-8, AR-14).

## Runtime Decision AR-16 Provenance

- **Authority:** AI — delegated by `--auto-design`.
- **Eligibility:** Internal testing/interface mechanism inside the approved runtime contract; no
  product behavior, compatibility boundary, or scope change.
- **Objective:** Preserve implementation-independent specification tests while making every host,
  clock, probe, attestation, and hook-order outcome deterministic.
- **Evidence:** The public orchestration signature is specified before implementation, Windows
  probes are platform-bound, and environment simulation would create a production backdoor.
- **Rejected alternatives:** Private-function patching couples tests to implementation structure;
  environment-variable simulation weakens production input boundaries.
- **Strongest counterargument:** A required dependency object adds one parameter and interface
  surface to an otherwise simple function.
- **Confidence:** High — the seam is internal, explicit, and directly testable; reopen if native
  integration proves the dependency boundary cannot represent a required OS operation.
- **Hardening:** The dependency object is mandatory, production construction stays outside the
  evaluator, and no test flag is accepted from CLI input.
- **Policy version:** 1.
- **Root invocation ID:** `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-17 Provenance

- **Authority:** AI — delegated by `--auto-design`.
- **Eligibility:** Internal request representation inside the approved hook/preflight behavior.
- **Decision:** Carry validated hook-event identity as a closed field; never derive trust from an
  environment variable or from the selected mode alone.
- **Evidence:** Hook JSON already names the event, while environment values are caller-controlled
  and mutation authority belongs to registered command entrypoints.
- **Rejected alternatives:** Environment markers are forgeable; mode inference cannot distinguish
  hooks from direct commands.
- **Strongest counterargument:** The additional field slightly enlarges every preflight call.
- **Confidence:** High; reopen if the Codex hook contract stops providing event identity.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-18 Provenance

- **Authority:** AI — delegated by `--auto-design` and constrained by the user's Windows 11-only
  direction.
- **Eligibility:** Native launcher selection within the approved Windows 11 compatibility boundary.
- **Decision:** Use inbox `powershell.exe` for hooks and examples; keep the bootstrap compatible
  with Windows PowerShell 5.1.
- **Evidence:** The execution host is Windows 11 with `powershell.exe` available and no `pwsh`;
  neither the requirements nor prerequisite checks declare PowerShell 7.
- **Rejected alternative:** Adding PowerShell 7 would introduce an unplanned install and probe
  requirement without improving the thin bootstrap contract.
- **Strongest counterargument:** PowerShell 7 has newer language and process behavior, but the
  bootstrap intentionally uses only Windows PowerShell-compatible constructs.
- **Confidence:** High; reopen only if Codex stops supporting `powershell.exe` hook commands.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-19 Provenance

- **Authority:** AI — delegated by `--auto-design` in response to RV-001 / SA-001.
- **Eligibility:** Internal transport for the already approved closed preflight request and exit
  contract; no product behavior or compatibility boundary changes.
- **Decision:** Use explicit, non-abbreviated argument-array flags and a repeated target flag.
- **Evidence:** PowerShell already forwards an argument array; the Python callable already owns
  the complete typed request; JSON stdin would compete with hook payload stdin.
- **Rejected alternative:** JSON stdin is closed but would require multiplexing the hook payload
  channel or another wrapper layer.
- **Strongest counterargument:** Flags add parser surface, but they make every field independently
  auditable and preserve shell-free invocation.
- **Confidence / hardening:** High; unknown, duplicate-singleton, missing, and malformed values
  fail with sanitized exit 1 before production probes.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-20 Provenance

- **Authority:** AI — delegated by `--auto-design` in response to SA-003.
- **Eligibility:** Internal launcher design inside the approved hook behavior.
- **Decision:** Replace inline PowerShell with a checked-in `-File` launcher that consumes
  `$env:PLUGIN_ROOT` only as data and derives sibling paths from `$PSScriptRoot`.
- **Evidence:** The security auditor reproduced command execution from legal plugin-root `$()`
  characters in the inline `-Command` form.
- **Rejected alternative:** Escaping substituted paths remains shell-specific and fragile for
  legal Windows characters.
- **Strongest counterargument:** One additional launcher file must be shipped and validated.
- **Confidence / hardening:** High; native tests execute it from paths containing spaces, `$()`,
  and a single quote and assert no side effect.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-21 Provenance

- **Authority:** AI — delegated by `--auto-design`.
- **Eligibility:** Internal adapter/interface design needed to express already approved AR-9
  behavior; it does not change process-ownership semantics.
- **Decision:** Use two immutable identity models, a three-state absence enum, an injectable
  backend protocol, and one strict parser for versioned plus legacy Linux records.
- **Evidence:** Nullable booleans currently conflate malformed input and platform uncertainty;
  backend-specific models preserve exact record shapes without reinterpretation.
- **Rejected alternative:** Raw dictionaries plus `bool | None` retain the current ambiguity and
  make backend mismatch handling easy to bypass.
- **Strongest counterargument:** Typed models add conversion code around existing dictionaries.
- **Confidence / hardening:** High; specification tests own exact payloads, malformed inputs,
  backend mismatch, absence, PID reuse, and uncertainty before implementation.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-22 Provenance

- **Authority:** AI — delegated by `--auto-design` after the Task 2.1.2 independent spec author
  identified a specification-independence gap.
- **Eligibility:** Internal adapter/interface design needed to test the already approved AR-10 and
  AR-11 filesystem policy; it changes neither the supported storage boundary nor error semantics.
- **Decision:** Expose narrow `PathProbe` and `AtomicWriteOps` protocols, optional keyword-only
  injection on the three path/write functions, and a transaction-path validator that rejects the
  complete set before mutation.
- **Evidence:** Retry scheduling, immediate revalidation, NTFS/reparse refusal, and alias collision
  behavior cannot be deterministically specified through the original three non-injectable
  functions without tests guessing private implementation details.
- **Rejected alternative:** Patching private helpers would make specification tests dependent on an
  implementation that does not exist yet; encoding host policy flags directly would permit callers
  to weaken production checks.
- **Strongest counterargument:** The public module surface is larger, but its default path remains
  the real host backend and the seams make security-boundary ordering auditable.
- **Confidence / hardening:** High; specification tests own call order, exact delays, generic-error
  refusal, interruption cleanup, whole-transaction collision rejection, and non-NTFS refusal.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.

## Runtime Decision AR-23 Provenance

- **Authority:** AI — delegated by `--auto-design` during Task 2.2.6 native integration.
- **Eligibility:** Internal executable selection inside the approved sandbox readiness probe; no
  prerequisite or support-boundary behavior changes.
- **Decision:** Execute the sandbox smoke through the concrete certified `sys.executable` instead
  of the Windows Store `py.exe` app-execution alias.
- **Evidence:** Native reproduction returned `CreateProcessAsUserW` access denied for the alias and
  exit 0 for the concrete interpreter under the same Codex restricted-token sandbox.
- **Rejected alternative:** Treating the access failure as an environmental block would make every
  registered direct mutation unusable despite a functioning sandbox and certified interpreter.
- **Strongest counterargument:** The probe no longer independently exercises launcher discovery;
  that discovery is already owned by the preceding Python check.
- **Confidence / hardening:** High; production probe and complete mutation preflight pass natively.
- **Policy version / invocation:** 1 / `exec-native-windows-support-20260806-01`.
