# Payment Request Release Static Parity — Batch G

## Boundary

- Formal Product Layer: P4 ops delivery tool.
- Layer Target: governed frontend release static server.
- Module: `scripts/release/release_static_server.mjs` and its existing runtime-profile test.
- Why here: the production-like acceptance server must expose the same Odoo `/web` asset route already provided by the formal Nginx topology.
- Why not elsewhere: the failure is not owned by Contract V2, Canonical Render Model, Floorplan, semantic components, UI kits, or construction business semantics.
- Blast Radius: exact `/web` and `/web/*` requests only; API proxying and SPA routes retain their existing behavior.

## Change

- Classify `/web` and `/web/*` as backend routes before static SPA fallback.
- Preserve the original request URL, headers, method, body, upstream response status, and upstream response headers.
- Add a regression assertion to the existing acceptance runtime test instead of creating a new test entry or environment.
- Refresh the immutable acceptance-package digest and its promotion-preflight contract after the governed server changed.

## Evidence

- `node --check scripts/release/release_static_server.mjs` — PASS.
- `python3 -m unittest scripts/verify/test_frontend_acceptance_runtime_profile.py` — PASS, 9 tests.
- `make verify.frontend.scene_component_bridge.guard` — PASS, 63 checks.
- `make verify.frontend.release.unit` — PASS with non-zero unit and guard coverage.
- `make verify.frontend.typecheck.strict` — PASS.
- `make verify.production.release_contract` — PASS, including 25 promotion-preflight tests and the refreshed immutable package identity.
- `make acceptance.package.verify` — PASS, digest `89f844b075ac82badd62140a5b8482599dccb233c8c814fe7b1740c392fbdfdf`.
- `git diff --check` — PASS.
- Governed page-identity and frontend release results are recorded after runtime verification.
