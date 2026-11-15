# ODOO-NATIVE-CAPABILITY-EXPLORER-04

## Candidate

- Baseline: `3e02a475f0a58b63472455dc0c42822e9743a945`
- Baseline tree: `c647702450a59fefa89d4097fddd0da0d42f4`
- Branch: `audit/platform-capability-studio-01-20261115`
- Stage: clean local candidate verified, pending exact-head Quick

## Product Boundary

- Formal product layer: P0 platform kernel product with P4 verification tooling.
- The Vue page consumes only the approved `platform.capability.explorer.list`,
  `detail`, and `diagnose` Intents.
- The page does not create a capability registry, persist catalog facts, infer
  Preview/Standard qualification, or perform scene/release writes.
- The browser requirement is ordinary management access; the backend Handler
  remains the authorization authority.

## Delivered Surface

- Added `/admin/capability-explorer` under platform management.
- Added live summary, native-center navigation, server search/filter controls,
  server pagination, desktop table and 390px mobile record cards.
- Added an on-demand detail Drawer for native Menu/Action identity, module,
  model, View/ACL/Record Rule summaries, scenario references, release state,
  qualification and technical blockers.
- Added shared `catalog_token` consumption for List, Detail and Diagnose.
- Added `CATALOG_STALE` recovery that closes stale detail state and refreshes
  the catalog without mixing snapshots.
- Added platform and tenant-config management duty entries pointing to the same
  official route.
- Added strict response decoders that raise `ContractGapError` for undeclared
  response shapes. An explicit empty center object remains a valid backend fact.
- Added the page to the existing page-contract runtime. The platform page now
  consumes declared title, description, section enablement and detail labels.
- Reused `ScButton`, `ScMobileRecordCard`, `ScSection` and the existing design
  system. No raw behavior surface or frontend persistence was added.

## Independent Review R1 Fixes

- Added an entry-request identity gate so a late Detail/Diagnose success,
  failure or `finally` from entry A cannot alter entry B or a closed Drawer.
- Re-diagnose now captures the selected entry identity and request sequence;
  close/invalidate prevents an old response from restoring a drawer state.
- Replaced the browser's permanent expected-409 boolean with a one-shot HTTP
  failure budget constrained by status and intent. A second or mismatched 409
  is unexpected, and an armed-but-unobserved failure fails the browser gate.
- Moved center-filter visual chrome from the `ScButton` primitive root to a
  consumer wrapper after remote CI exposed
  `verify.frontend.primitive_adapter.unit`; the primitive continues to use the
  existing `tree-item` appearance.
- The race browser probe now opens A completely, installs an interceptor only
  for A's next re-diagnose, opens and fully settles B, then releases A through
  an explicit deferred Promise. It no longer depends on a fixed sleep.
- The ordinary-user negative now requires exactly HTTP 403 and
  `PERMISSION_DENIED`; generic 4xx/5xx responses cannot pass.
- Added negative tests for exact-once expected failure consumption, mismatched
  intent/status, pending expectations, newer/older request sequences, and close
  invalidation.

## Implementation Corrections Found During Acceptance

- Detail and Diagnose use base metadata without List pagination fields; the
  decoder now separates `BaseMeta` from List-only pagination metadata.
- Explicit empty `center={}` is accepted as backend truth rather than treated
  as a contract gap.
- Detail section headings now render through the shared `ScSection` component.
- The platform page contract is included in the authenticated startup projection.
- Mobile rows now use `ScMobileRecordCard`; wrapping a structured record in a
  button had broken the field stack.
- The browser tool records `CATALOG_STALE` as the sole expected 409 and does not
  hide any other HTTP, Console or Page error.
- The verification-lane baseline deliberately registers the new browser target
  as a governed browser acceptance probe. The page-contract change also wires
  the formerly zero-reference public-auth bootstrap target, so that stale
  disposition was removed and the target was re-registered after mapping was
  narrowed back to the direct boundary gate.

## Verification

| Gate | Result |
| --- | --- |
| `make verify.platform.capability_explorer.unit` | PASS: 19 + 6 + 2 tests |
| `make verify.frontend.platform_capability_explorer.unit` | PASS: backend duty 27, duty action 4, route access 13 cases, browser budget 3 cases, strict decoder/request gate 21 cases |
| `make verify.backend.navigation_delivery.unit` | PASS: all navigation and page-contract units |
| `make verify.frontend.dev.incremental.unit` | PASS: 148 tests |
| `make verify.frontend.lint.src` | PASS: 0 errors; existing warnings only |
| `make verify.frontend.typecheck.strict` | PASS |
| `make verify.frontend.decision_authority.unit` | PASS: 21 tests; unclassified 0 |
| `make verify.frontend.component_driver_takeover.unit` | PASS: raw behavior surfaces 0 |
| `make verify.frontend.page_contract_boundary.guard` | PASS: 24 views covered |
| `make ci.local.iteration` | PASS: 16 required targets executed |
| `make ci.delivery.freeze.prepare` | PASS: content-bound generated evidence current |

The initial incremental run exposed an unrelated, pre-existing
`verify.frontend.public_auth_bootstrap.unit` sandbox failure. Page-contract
declaration mapping was narrowed to the direct page boundary gate; the existing
public-auth probe remains registered and is not claimed as passing in this batch.

## Browser Acceptance

Runtime: `local.dev` / `sc_dev_demo`, authenticated as `admin`.

- Current live catalog: 17 native entries, 0 bound scenarios, 17 unbound.
- Native centers: 5.
- Exact `catalog_token`:
  `sha256:37490e5695e1a632a4786716867e7d1f5f4b482346cde16d4a787fa19cdfec7b`.
- Browser assertions: 29/29 PASS.
- Screenshots: desktop list, desktop detail, 390px mobile list.
- Performance in this run: desktop list ready 1203 ms; detail ready 441 ms;
  stale refresh 1436 ms; mobile list ready 1497 ms.
- Search `项目` returned 1 filtered row from the live 17-row catalog.
- The `unclassified` center facet returned its matching 2/2 server rows after
  clearing the prior search.
- Pagination metadata: offset 0, limit 50, next offset null, has more false.
- HTTP failures: one expected `CATALOG_STALE` 409; no unexpected failures.
- Console/Page errors: 0.
- Late-diagnosis race probe: A returned blocker `LATE_ENTRY_A` after B was
  selected; B retained its own Action XMLID and displayed no A blocker.

Permission negative:

- `wutao` was redirected away from `/admin/capability-explorer`.
- Route access made 0 Explorer List requests.
- A direct List Intent call returned HTTP 403 `PERMISSION_DENIED`.

Evidence hashes:

- `report.json`: `d0250e3ff6a469c1457ef6f90c7ce1d8d21f8cd9ff4e33e43a23103dd3173554`
- `01-desktop-list.png`: `23a70aac6fe11f59435f2c422adfbe1feae7d4706281c8c2ae7a5380b76447ab`
- `02-desktop-detail.png`: `fabc6c288071be14687ffd1ab7af0cb2eabd76e0fe5700ede2d6386f40027d3a`
- `03-mobile-list.png`: `c218cbd22a28f9ec1ef7957795f2e3ac183f2dea7ae457b1135bab1b139d6957`

## Explicit Exclusions

- No historical 282/75/207 snapshot reconciliation is claimed from 17-entry
  `sc_dev_demo`; that remains a separate authorized-snapshot acceptance.
- No add-to-scene-draft, scene edit, tile edit, publication, or enterprise
  activation write.
- No new ORM model, Capability Registry, ACL/Record Rule change, migration, or
  frontend persistence.
- No push, merge, or deployment in this batch.

## Next Exact Step

Run one exact-head `make ci.local.quick.full`, verify the receipt/tree/clean
state, then stop for independent review.
