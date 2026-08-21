# Payment Request Repository Gate — Batch F

## Boundary

- Formal Product Layer: P4 CI and repository governance.
- Layer Target: immutable synthetic-fixture false-positive registry and verify-script lifecycle registry.
- Module: `scripts/ci` and `scripts/verify` registries only.
- Why here: the authoritative PR checks rejected an already tracked synthetic payment fixture blob and seven unacknowledged verification scripts before product acceptance could run.
- Why not elsewhere: no contract, renderer, Native capability implementation, UI kit, business rule, database, fixture value, or runtime configuration is changed.
- Blast Radius: one exact personal-data tuple and seven existing orphan-script acknowledgements.

## Changes

- Registered `PD003`, the exact payment-capability test path, immutable blob `1a28e3faa37d77c9a2ac52c15c80b06c9579f5c3`, `BANK_ACCOUNT_PATTERN`, and a synthetic-payment-fixture reason.
- Seeded lifecycle records for seven already present Native/product-view verification scripts as `status: orphan`. This acknowledges review debt without activating, extending, or promoting their capability ledgers.

## Evidence

- `python3 scripts/ci/test_personal_data_scan.py` — PASS, 6 tests.
- `python3 scripts/ci/personal_data_scan.py --scope all` — PASS, confirmed matches 0, recorded values false.
- `make verify.guard.registry` — PASS, 1102 scripts, 92/92 orphan scripts acknowledged.
- `git diff --check` — required before commit.
