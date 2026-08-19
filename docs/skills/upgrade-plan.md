# `upgrade-plan`

Use `upgrade-plan` to bring an older CodeOps requirements set, specification, plan, or project up to
the current artifact schema and quality standards.

```text
Use upgrade-plan on the legacy billing plan. Assess and preview it first.
```

The workflow separates content quality from structural migration:

1. Assess the target read-only and classify legacy constructs.
2. Resolve material ambiguities in their authoritative documents.
3. Preview the structural conversion.
4. Apply only after authorization.
5. Validate the result without advancing lifecycle state.

Layout movement belongs to `setup-codeops`; do not combine it with a semantic artifact upgrade in
one irreversible operation. Historical progress and user-authored meaning are preserved wherever
they remain valid.
