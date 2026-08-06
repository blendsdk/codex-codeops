# Windows evidence fixtures

`valid/cli.json` and `valid/desktop.json` are a complete synthetic candidate with hash-bound
supporting records. `valid/invalid-cli.json` deliberately omits a required scenario. Tests copy
fixtures before mutation; retained real-host evidence belongs in `tests/evidence/`.
