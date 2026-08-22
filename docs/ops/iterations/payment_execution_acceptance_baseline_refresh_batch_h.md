# Payment Execution Acceptance Baseline Refresh — Batch H

## Boundary

- Formal Product Layer: P4 ops delivery tool, with P1 regression coverage.
- Layer Target: governed frontend acceptance baseline lifecycle and readonly
  payment-execution Contract V2 verification.
- Modules: `scripts/test/frontend_acceptance_db_ensure.sh`,
  `scripts/dev/frontend_acceptance_runtime.sh`, their existing tests, and
  `smart_construction_core` test coverage.
- Standard vs User-Specific: governed platform/product acceptance lifecycle;
  no customer-specific preference or data baseline.
- Why here: `sc_frontend_acceptance` is intentionally persistent, so installing
  an already-installed bundle cannot prove that its XML baseline matches the
  candidate source.
- Why not elsewhere: P0 must continue rejecting native form fields without
  occurrence identity. The frontend must not hide a backend 500, and P1 must
  not manufacture native locators for fields absent from its current form.
- Blast Radius: the existing acceptance database, project, ports, volumes,
  credentials, fixture system, and browser entries remain unchanged.

## Root Cause

The real `sc.payment.execution` readonly journey failed with:

```text
native form projection ... field='creator_name' locator='' occurrence_index=0
```

The field came from stale persisted orchestration data. The source tree's
current form and product contracts do not project that node. Running the
registered baseline upgrade removed the drift and immediately restored the
same browser route without a product-code workaround.

## Change

- Refresh `smart_core`, then `smart_construction_core`, after the governed
  acceptance bundle installation step.
- Reload the local Odoo registry after the baseline refresh, matching the
  existing isolated-CI behavior.
- Add an identity-validated backend log target that reads the configured Odoo
  logfile and falls back to container logs.
- Exercise the formal actual-outflow action with the same Contract V2 surface,
  source mode, delivery profile, and capability declaration used by the web
  client.

## Evidence

- `python3 -m unittest scripts.verify.test_frontend_release_local_entry scripts.verify.test_frontend_acceptance_runtime_profile` — PASS, 20 tests.
- `python3 scripts/verify/frontend_acceptance_environment_source_guard.py` — PASS.
- Targeted P1 Odoo test — PASS, 1 selected, 0 failed, 0 errors.
- `make db.frontend.acceptance.ensure` — PASS through install, ordered baseline
  upgrades, registry reload, and final preflight.
- Governed `FE-A-PE-001` readonly browser probe — PASS with the real record,
  zero HTTP 500 responses, and no load-failure surface.
- Full frontend release evidence is recorded after the frozen-candidate gate.
