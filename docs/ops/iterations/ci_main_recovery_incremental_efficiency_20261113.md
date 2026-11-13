# CI main recovery and incremental efficiency

Date: 2026-11-13

Branch: `codex/ci-main-recovery-incremental-efficiency-20261113`

Baseline: `70ad2e6af3b6794a9bcba0ea2b4dde499a6ecf07`

## Product result

Restore scheduled-main static correctness and make known tooling changes select
their exact checks instead of the full backend runtime lane. Clean acceptance
database creation should perform only the work required for a newly installed
database.

## Ownership

- Formal Product Layer: P4 operations delivery tooling
- Layer Target: CI path ownership, static guards and clean database preparation
- Module: governed CI and verification tooling
- Why here: the failures are in routing and validation tools, not product semantics
- Why not elsewhere: broad backend/ORM runs or product-special-case changes would
  hide incorrect dependency selection
- Blast Radius: the declared CI/path, static guard, workflow ordering and
  acceptance database preparation files only

## Current evidence

The three scheduled-main failures were classified as validation-tool defects:

- `my-work` became a compatibility redirect to `scene-my-work`; the guard now
  verifies the redirect and the final scene heading declaration.
- activity cache identity moved to the shared
  `activityPageCacheIdentity.ts` helper; both negative tests and the deployed
  App consumption chain are now checked.
- the assembler cache pin followed the already-reviewed `v37` cache version and
  the exact combined input digest.

The local browser probe's two internal TDesign option selectors were replaced
with public role-based selectors, bringing the vendor-selector count back within
the decrease-only baseline.

Path ownership now assigns the two known #880 tooling inputs before broad
patterns:

- `config/frontend/probe_toolchain_registry.json` owns
  `verify.local.dev.project_profile_write.unit`;
- `config/security/secret_scan_false_positives.v1.json` owns
  `security.secrets.scan`;
- both are non-runtime paths and neither selects an Odoo module or ORM scope.

Replaying the complete #880 change set produced:

```text
paths=31 unknown=0 backend_runtime_changed=false orm_required=false
backend_modules=[] managed_orm_required=false payment_orm_required=false
```

The unknown-path negative remained fail-closed: it produced
`unknown_path_fail_closed`, `mode=full`, `orm_required=true`, and selected every
synthetic backend module.

The professional workflow now runs the three cheap static owners before ORM
reporting and settlement preparation. Clean acceptance databases are detected
from the existing governed `db.create` outcome. A newly created database proves
installed module versions, required XMLIDs and the construction product baseline,
then skips the two persistent-database upgrade passes. Existing databases retain
both upgrades.

The first remote run of the new ordering exposed one dependency mistake in the
early step: the full page-header Make target also runs component contract cases
that require `esbuild`, which is not installed until the normal frontend
dependency phase. The early step now invokes the dependency-free Python page
header and delivery-hardening guards directly, plus the existing argument-bound
assembler target. The complete Make targets still run in the normal full lane.

Independent review of `8a9f3c41` also identified two additional P4 corrections:

- the role and responsible-person controls are standard `ScSelect` option rows
  and do not receive `role="option"`; their selectors now target the rendered
  `li.t-select-option` rows within the existing vendor-coupling baseline;
- a nonzero `db.create` now retains and prints the original diagnostic before
  returning the original status, instead of being lost to `set -e`.

## Validation

`make ci.local.iteration` passed with 12/12 required targets, zero unmapped
paths and non-zero test execution. Original logs and per-target hashes are in
`.runtime/frontend-dev-validation/executions/20261113T042123Z-4007581-230044531/receipt.json`.

| Check | Result |
|---|---|
| path ownership | PASS, 19 tests |
| CI workflow contract | PASS, 411 tests across the registered suites |
| page-header guard | PASS, 84 tests plus 28 model and adapter contract cases |
| delivery-hardening guard | PASS, 17 tests |
| Unified Page Contract v2 assembler | PASS, `sources=4` |
| incremental routing | PASS, 133 tests |
| guard registry after new dependency mapping | PASS, 24 tests |
| release-local/runtime-profile/carrier suites | PASS, 94 tests |
| clean vs existing database preparation | PASS: clean skips upgrades; existing retains both |
| unknown `db.create` result | PASS: fails closed before module work |
| secret scan | PASS, `confirmed_matches=0` |
| `make ci.delivery.freeze.prepare` | PASS, generated evidence current |

The clean/existing split was verified with the original shell entry and governed
Make adapter stubs. No real acceptance database was rebuilt in this source-only
layer, so the remote CI fresh-database lane remains the first full Odoo execution
of that path. Business-entry matrix and browser acceptance were intentionally not
rerun because no business-consumption input changed.

The first full local Quick stopped in shard 4 because the newly wired profile
fixture test was still acknowledged as an orphan in `scripts/verify/registry.yaml`.
`make guard.registry.seed` removed that stale acknowledgement and the registered
guard audit passed; the exact-head Quick is rerun after the candidate is amended.

## Rollback

Revert this P4 batch. No business data or persistent database is intentionally
mutated.
