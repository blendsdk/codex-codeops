# Ambiguity Register: Auto Design

> **Status**: ✅ GATE PASSED — all 11 items resolved
> **Last Updated**: 2026-07-23 17:45

| # | Category | Ambiguity / Gap | Options Presented | User Decision | Status |
|---|---|---|---|---|---|
| AR-1 | Scope | What does `--auto-design` delegate? | Advice only / eligible technical decisions / all authority | Eligible technical design decisions; CodeOps investigates, decides, records, and verifies | ✅ Resolved |
| AR-2 | Stakeholder | Why delegate? | Convenience / expert-capability gap | Expert domains can exceed one person's knowledge; optimize for project success | ✅ Resolved |
| AR-3 | Technical | What is “strongest”? | Most sophisticated / cheapest / objective-weighted best fit | Quality-first best fit across correctness, safety, fitness, maintainability, verifiability, performance, compatibility, recovery, risk, and evolution | ✅ Resolved |
| AR-4 | Scope | Which workflows honor the flag? | Planning only / all decision-producing lifecycle workflows | Requirements, planning, preflight remediation, and execution-time ambiguity resolution | ✅ Resolved |
| AR-5 | Security | Does design delegation grant action authority? | Yes / no | No; commits, pushes, deployments, destructive actions, credentials, spending, and external communication retain their own permissions | ✅ Resolved |
| AR-6 | Stakeholder | What remains user-owned? | Nothing / product and consequential external authority | Product identity and priorities, legal/ethical acceptance, financial exposure, and materially different equally defensible products | ✅ Resolved |
| AR-7 | Technical | How are automatic decisions trusted? | Opaque choice / recommendation protocol / independent challenge | Grounded options, forced reframing, evidence, counterargument, confidence, and mandatory blind challenge for complex, sensitive, high-impact, or difficult-to-reverse choices | ✅ Resolved |
| AR-8 | Data & state | How is provenance recorded? | Conversation only / durable register | Durable AR entry using the canonical `_shared/auto-design.md` marker `Authority: AI — delegated by --auto-design`, plus objective, evidence, rejected alternatives, confidence, and reopen triggers | ✅ Resolved |
| AR-9 | Compatibility | How is mode activated? | Project default / invocation flag / global default | Invocation-scoped `--auto-design`; normal behavior is unchanged when absent | ✅ Resolved |
| AR-10 | Behavioral | What if evidence is insufficient? | Guess / always ask / research then bounded escalation | Research and challenge first; escalate only when no defensible eligible decision remains or the choice is reserved authority | ✅ Resolved |
| AR-11 | Behavioral | What happens when new evidence invalidates a choice? | Preserve / silently replace / reopen visibly | Reopen the AR, mark affected downstream state stale, decide again under the same policy, and re-run gates | ✅ Resolved |

### Resolution Notes

The user explicitly delegated technical design authority after explaining that complex domains
such as expert compiler optimization can exceed an individual operator's knowledge, then confirmed
the proposed authority boundary “1000%” and instructed implementation to proceed. These entries
record that explicit bulk decision; they are not inferred consent.

**Hardening:** The independent design challenger converged on the hybrid shared-policy design and
added downward-only capability propagation, policy/root-invocation provenance, and fail-closed
handling for material challenger divergence. Confidence: High. Challenger: converged.
