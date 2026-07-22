# Acme Fake Project (test fixture)

A minimal consumer repo used to exercise the per-repo telemetry kill switch: any emit run
from inside this repo must be a silent no-op because the quality block below turns
telemetry off.

## Quality profile (CodeOps)
<!-- CODEOPS-QUALITY:START -->
lenses: []
telemetry: off
<!-- CODEOPS-QUALITY:END -->
