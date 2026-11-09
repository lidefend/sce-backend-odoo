# Daily main release from detached candidate

Status: active

- Formal Product Layer: P4
- Layer Target: daily runtime release orchestration
- Baseline: `main@bbc1fabb65cfe2b5ac610e787d2863ef256a43d6`
- Exclusion: no product, contract, ACL, business data or production change

## Defect

The main release preflight derived duty-plan digests with the old `main` SHA.
When the daily server is a clean, recorded detached candidate, its actual HEAD is
the candidate SHA, so the read-only plan correctly refuses the stale expected
SHA before the release can normalize the runtime back to main.

## Rule

Use `expected-candidate-sha` as the read-only plan SHA when main mode is
normalizing a detached candidate; otherwise use `expected-old-sha`.
