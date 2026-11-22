# Mainline Performance 02 R1: Request-Scoped Scene Facts

## Identity

- Base main: `cb182c9e94abe515b0d987fc514bc46ca98d1cfb`
- Diagnosis commit: `3eed67cee1ff2be5c9336f59687ba387de64b999`
- Branch: `fix/mainline-performance-02-scene-facts-20261122`
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
| Whole request | 998.08 ms | 843.45 ms | -154.63 ms / -15.5% |
| Warm request | 994.68 ms | 812.82 ms | -181.86 ms / -18.3% |
| Process-first request | 2008.11 ms | 1782.24 ms | -225.87 ms / -11.2% |
| `build_nav` | 670.00 ms | 583.00 ms | -87.00 ms / -13.0% |
| `execute_scene_runtime` | 57.00 ms | 34.00 ms | -23.00 ms / -40.4% |
| `finalize_startup_surface` | 144.50 ms | 108.00 ms | -36.50 ms / -25.3% |

Five-sample browser login observations, using the same browser version, DB,
frontend bundle and request sequence. R1 was measured twice against the same
base result to expose local run-to-run noise:

| Metric | Base median | R1 first run | R1 confirmation run | Change range |
| --- | ---: | ---: | ---: | ---: |
| Login to interactive | 2814 ms | 2651 ms | 2780 ms | -34 to -163 ms |
| `system.init` HTTP | 1328.58 ms | 1215.34 ms | 1230.26 ms | -98 to -113 ms |
| `build_nav` | 998 ms | 903 ms | 928 ms | -70 to -95 ms |
| Post-response UI | 892 ms | 886 ms | 901 ms | -6 to +9 ms |

These are local diagnostic measurements, not release-budget claims. They show
that both runs improved the backend `system.init` path while post-response UI
stayed within local noise; there is no evidence that cost was moved into a
different stage. The exact-head release gate remains the authoritative
end-to-end measurement.

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
| Base runtime equality matrix | `f06e54bce827014cb880af6f7a7685129462f7f84cc1f4075772a65589745f06` |
| R1 runtime equality matrix | `cfd0d40d03358b75ad905c678093e828266fc133e65839afc196e73bcdb3101a` |
| Base backend observation | `7c9fc80640c015586de09193f924dafb6200859d9d2f5019b6fe5d658b5b0b44` |
| R1 backend observation | `87b46666a1d6b834cf1f8adf8139e7e6c0381e0bffe0155f9ff086ca93ec1ab6` |
| Base browser observation | `d5acb9a70f1df0782c89cb55d2bd5a5dd51042d1685493f82ea2322e0aa7e536` |
| R1 browser observation | `4b2ac38a31f8006b943a7daaf29461f64ec50c32022f6430ab105813b093a04b` |
| R1 performance unit | `c19bdc43dd42aa110a510bb0225b648f88a45051dd3b116f1326cb23b8112680` |
| R1 navigation unit | `94c747a8d18e0686a3f9b21dcfed63628c2d97f8adabf48dd9343c29fd18bb5d` |

## Rollback

Revert the request context, scene declaration snapshot helpers and consumer
argument plumbing as one commit. Consumers then return to independent loading.
