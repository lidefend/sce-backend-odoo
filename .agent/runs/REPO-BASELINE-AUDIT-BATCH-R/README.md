# Batch-R: Product-version single source

- Formal Product Layer: P4 release governance.
- Layer Target: repository product-version authority and derived observation validation.
- Authority: `VERSION` is the only source; the system-init snapshot is one exact derived fact.
- Why Here: the release guard owns version-source validation.
- Why Not Elsewhere: product code, schema, runtime state and actual version remain unchanged.
- Blast Radius: one documentation reference, one guard and its release tests.
- Status: verification pending; full gate outcomes are recorded in `evidence.yaml`.
