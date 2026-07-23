# Evaluation evidence

CodeOps is evaluated by observed ambiguity detection, not prompt-file similarity.
The repository retains a matched requirements-stage ambiguity benchmark from installed Codex CodeOps
`0.2.0-beta.2` and Claude CodeOps `3.12.0` for three adversarial seeds.

| Scenario | Required safety concepts | Codex blockers | Claude blockers | Benchmark verdict |
|---|---:|---:|---:|---|
| Generic aliases and incremental compiler | 8 | 20 | 10 | Pass |
| Multi-currency transfer ledger | 8 | 30 | 13 | Pass |
| Multi-tenant approval workflow | 8 | 32 | 13 | Pass |

Counts are not treated as quality by themselves. Both editions must first cover
the scenario's required correctness concepts and keep the plan gate closed.
Codex must then be no worse on blocking ambiguity discovery. The retained JSON
contains each question and its concrete impact for audit.

This benchmark is deliberately narrower than full product parity: it proves
domain-lens selection, material-question discovery, and correct gate closure at
the requirements stage. It does not prove execution, recovery, or final-system
quality. Machine-readable versions, commits, capture time, harness, and limits
are retained in `tests/scenarios/evidence.json`.

Run the deterministic comparison:

```bash
for scenario in compiler financial web; do
  python3 scripts/compare_scenarios.py "tests/scenarios/$scenario"
done
```

Regenerate live evidence only when both installed products are available:

```bash
python3 scripts/run_live_scenario.py codex tests/scenarios/compiler tests/scenarios/compiler/result.json
python3 scripts/run_live_scenario.py claude tests/scenarios/compiler tests/scenarios/compiler/claude-result.json
```

The live harness invokes installed plugins, disables writes in the prompt, and
requires schema-constrained output. The Codex process uses an ephemeral session;
the Claude process disables session persistence. Model behavior can vary, so a
release candidate must regenerate and review all three scenarios rather than
relying only on historical counts.
