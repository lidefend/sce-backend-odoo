# Frontend Delivery Performance 2026-11-22

## Identity

- Repository: `lidefend/sce-backend-odoo`
- Base main: `cb182c9e94abe515b0d987fc514bc46ca98d1cfb`
- Candidate branch: `fix/frontend-delivery-performance-20261122`
- Formal product layer: P0 platform startup mechanism
- Scope: `system.init` startup navigation projection only

## Observed failure

Manual full frontend run `44980704390` failed the absolute performance budget:

| Scenario | Median | Budget |
| --- | ---: | ---: |
| `login_to_interactive` | 3411 ms | 3000 ms |
| `my_work` | 1618 ms | 1200 ms |
| `form_open` | 1604 ms | 1600 ms |
| `company_switch` | 2210 ms | 2000 ms |

The startup diagnostics show that `build_nav` consumed 1322-1676 ms of a
1830-2166 ms `system.init`. `EffectiveDeliveryService` already produced the
final qualified navigation, but `SystemInitHandler` subsequently rebuilt a
second navigation tree through `NavDispatcher` and then replaced it with the
effective delivery navigation.

## Repair

Boot-mode startup now derives compatibility navigation fields directly from the
already-qualified effective delivery payload. It no longer rebuilds and discards
the full `NavDispatcher` tree. The legacy `NavDispatcher` path remains for
preload/debug requests, explicit root-scoped requests and the existing
`app.menu.config` fallback.

Local governed observation after the change:

- `compatibility_navigation`: 0 ms
- warm `build_nav`: 481-551 ms
- navigation SHA across all samples:
  `6f78c0a147c33545c1407366d7e2bf74d32ea4bfafe90ec98ba4c300c03c2ddf`

## Validation

| Check | Result |
| --- | --- |
| `verify.system.performance.baseline.unit` | PASS, 72 tests |
| `verify.local.dev.runtime.performance.unit` | PASS, 34 tests |
| `verify.backend.navigation_delivery.unit` | PASS, 177 tests |
| Targeted smart_core ORM | PASS, 16 tests |
| `ci.local.iteration` | PASS |
| `ci.delivery.freeze.prepare` | PASS |

The local full release command reached production build and static release
audit, then stopped before browser performance sampling because the local
`sc_frontend_acceptance` database has no initialized product baseline. This is
an acceptance-environment prerequisite failure; it does not provide a new
performance result. The exact-head remote frontend release gate remains the
authoritative end-to-end measurement.

The first remote candidate measured only `login_to_interactive` above budget
(3152ms vs 3000ms); the other six scenarios passed. Profiling then identified
repeated full product-policy and navigation copies. Delivery payloads that were
materialized for the current request are now mutated by their owning projection
instead of copied again, and product-policy normalization performs one
isolation copy rather than nested copies of every group, menu and capability.
That candidate's `professional_quality_gate` coverage step then waited for the
failed frontend producer's managed ORM evidence and failed when the producer
finished; `merge_policy_gate` and `release_candidate_gate` followed the same
upstream result. These are consequences of the performance failure, not
additional product defects.

The profiled deepcopy cost fell from about 754ms to 465ms, while navigation SHA
remained
`6f78c0a147c33545c1407366d7e2bf74d32ea4bfafe90ec98ba4c300c03c2ddf`.

## Boundary

- Preserve the exact effective navigation, route authority, default route,
  capability/scene payload and user-visible behavior.
- Remove only duplicate runtime materialization and derive the required
  compatibility metadata from the qualified result.
- Do not change budgets, permissions, business semantics, database fixtures or
  frontend components to make the gate pass.
