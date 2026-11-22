# Mainline Performance 02 R1: Request-Scoped Scene Facts

## Identity

- Base main after required sync: `d8ce851a7222a07491518749faf9cf7e8f2f53ed`
- Diagnosis commit in replacement candidate: `27f9c86a28d8d59aa830a9c38fb11c6e708bd1f3`
- Branch: `fix/mainline-performance-02-scene-facts-r2-20261122`
- Formal product layer: P1 construction scene runtime mechanism
- P0 seam: generic request-scoped fact carrier only

## Objective

Load effective scene declarations once per `system.init` request and pass that
explicit fact to every consumer. This batch does not add a global cache and does
not use `env.context` to transport business objects.

## Consumer Inventory

The cold request has six scene declaration load sites:

| Consumer | Call path |
| --- | --- |
| Effective scene internal actions | `EffectiveDeliveryService._internal_actions` |
| Navigation authority filter | `smart_core_navigation_authority_filter` |
| Navigation scene maps | `OdooNavAdapter` -> `smart_core_nav_scene_maps` |
| Capability scene targets | capability registry -> `capability_scene_targets` |
| Scene runtime fallback | `SceneRuntimeOrchestrator` -> registry provider |
| Final scenario projection | navigation compiler -> `smart_core_scenario_surface_projection` |

The previous Profile reported five loads because the capability scene-map cache
was already warm. A cold process contains the sixth capability producer load.
R1 therefore verifies the stronger bound: six cold call sites, one request
fact, and one underlying effective declaration load.

## Boundary

- One request-scoped effective scene declaration load.
- Consumers read the same declaration content and create only local projections.
- Different requests, users, companies, products and databases never share a context object.
- No menu-index, XMLID, release-snapshot, broad deepcopy or frontend optimization is included.
- No schema, fixture, stored data or permission semantics change.

## Implementation

`SystemInitHandler` creates one `SystemInitRequestContext` after binding the
request env and product identity. The context stores only request-local facts
and is passed explicitly through the existing call chain.

`scene_registry` owns the effective declaration snapshot:

- the first consumer loads the effective declarations;
- the snapshot stores the ordered declarations, load timings and a canonical
  content SHA-256;
- later consumers receive the same request fact without invoking the registry
  loader again;
- `load_scene_configs` creates a shallow top-level scene mapping only where its
  tile projection replaces a value;
- no module-level or registry-wide scene declaration cache was added;
- no large object is placed in `env.context`.

The context identity records database, user, company, product key, base
product key and edition key. A new `system.init` invocation always creates a
new context and cannot consume another request's fact.

## Runtime Result

The same script was run on the clean base candidate and then on R1, using the
same `sc_dev_demo` database, roles, companies, product and navigation request.
Capability caches were cleared before each measured request so the cold call
sites were visible.

| Identity | Base load count | R1 load count | Scene content | Navigation SHA | Route Authority SHA | Full data SHA |
| --- | ---: | ---: | --- | --- | --- | --- |
| finance / company 1 | 6 | 1 | identical, 96 declarations | identical | identical | identical |
| owner / company 2 | 6 | 1 | identical, 96 declarations | identical | identical | identical |
| project manager / company 1 | 6 | 1 | identical, 96 declarations | identical | identical | identical |

The canonical effective scene declaration fingerprint was
`8e98be87a484821c14be4d0067d139f5763d1cb225180c586e7baf14ba825aec`
on every request and in both base and R1. The local effective declaration set
contains 96 declarations; this exceeds the 17-scene client-facing subset and
therefore provides a stronger content/order comparison. The complete response,
navigation and route-authority hashes were byte-identical per identity, while
different role/company identities retained their distinct authority hashes.

The 96 declaration count is local runtime evidence, not a hard-coded business
constant. The invariant is the identical content fingerprint and complete
response identity, not the number itself.

## Performance Result

Backend-only observation on the registered `sc-local-dev/sc_dev_demo` profile:

| Metric | Base median | R1 median | Change |
| --- | ---: | ---: | ---: |
| Whole request | 1001.84 ms | 866.67 ms | -135.17 ms / -13.5% |
| Warm request | 998.82 ms | 807.41 ms | -191.41 ms / -19.2% |
| Process-first request | 2155.73 ms | 1957.74 ms | -197.99 ms / -9.2% |
| `build_nav` | 604.50 ms | 594.50 ms | -10.00 ms / -1.7% |
| `execute_scene_runtime` | 58.00 ms | 37.00 ms | -21.00 ms / -36.2% |
| `finalize_startup_surface` | 157.50 ms | 110.50 ms | -47.00 ms / -29.8% |

Five-sample browser login observations, using the same browser version, DB,
frontend bundle and request sequence. R1 was measured twice against the same
base result to expose local run-to-run noise:

| Metric | Base median | R1 median | Change |
| --- | ---: | ---: | ---: |
| Login to interactive | 2947 ms | 2789 ms | -158 ms / -5.4% |
| `system.init` HTTP | 1413.47 ms | 1289.42 ms | -124.05 ms / -8.8% |
| `build_nav` | 990 ms | 1011 ms | +21 ms |
| Post-response UI | 915 ms | 904 ms | -11 ms |

These are local diagnostic measurements, not release-budget claims. They show
that the backend `system.init` path and login-to-interactive both improved
while post-response UI did not absorb the saved cost. The browser `build_nav`
delta is not monotonic in this run because it also contains the separate legacy
mainline navigation path; it is not used as proof of the scene-fact saving. The
exact-head release gate remains the authoritative end-to-end measurement.

## Validation

Passed:

- `verify.system.performance.baseline.unit`: request-context isolation plus
  performance baseline suites, 78 non-zero tests.
- `verify.backend.navigation_delivery.unit`: navigation, scene, capability and
  Hook consumer suites.
- `verify.navigation.publication_consumers.unit`: PASS.
- `verify.frontend.platform_capability_explorer.unit`: PASS.
- `verify.extension.hook_contracts.unit`,
  `verify.extension.hook_resolver.unit`,
  `verify.extension.runtime_context.unit`,
  `verify.extension.consumers.unit`: PASS.
- `verify.system_init.menu_boundary.guard`: PASS.
- `verify.daily.permission_truth.capability.orm`: PASS,
  `ORM_RESULT_GUARD=PASS`, 81 tests.
- `ci.local.iteration`: PASS after the affected execution set, including ORM.

Runtime assertions:

- one effective declaration load per request;
- initial and post-consumer content fingerprints equal;
- finance, project manager and owner/company 2 retain distinct authority
  results;
- no cross-context fact reuse;
- unit concurrency test runs eight independent contexts without sharing data.

Excluded:

- menu-index reuse and XMLID batching remain for R2;
- release snapshot reuse remains for R3;
- broad deepcopy ownership remains for R4;
- scenario projection Hook and frontend startup remain for R5/R6.

## Evidence

| Evidence | SHA-256 |
| --- | --- |
| Synced base runtime equality matrix | `4e313adaeec0269477483fb46ce840837619c597e38c92ede22550158514d7ec` |
| Synced R1 runtime equality matrix | `977599dabdcad747ad2e333eb2cc2f9097ad8970e3053e6c43941a9a4062a5e7` |
| Synced base backend observation | `70601b3189f7e1abd54ca9795507b9250ce2ebc2561db43707a9753926768bfc` |
| Synced R1 backend observation | `559610a80ece374b61e1d253c3a555e118c07a9da8b2ca68710e4e7f84772dee` |
| Synced base browser observation | `d34d1f8de4ce8abdbe2685fb769eb5cee3d9a5f2f687841387e55ed815d670ce` |
| Synced R1 browser observation | `084e20bf6c4942c4eabecef7bd1b0734349dd0fdc0adfb208cfb978904e5c7c8` |
| Synced R1 performance unit | `0ae41d8a8c6253613b8ceecd74d887699448bb6f18017345197a732266a7b6d8` |
| Synced R1 navigation unit | `52862e82361b5e3f2c034d9ebce236b9d14a3cf294ce1cdc63f9f73db21d8152` |

## Rollback

Revert the request context, scene declaration snapshot helpers and consumer
argument plumbing as one commit. Consumers then return to independent loading.
