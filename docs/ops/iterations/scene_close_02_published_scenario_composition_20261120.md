# SCENE-CLOSE-02 Published Scenario Composition

Status: active

Base: `f0df3409eca16f0852764aca4632307b026873a4`

Branch: `feature/scene-close-02-published-scenario-composition-20261120`

## Product result

Business scenario maintenance remains a draft. Product publication fixes the
`sc.product.scenario / sc.product.scenario.entry` composition captured by the
active release snapshot. Runtime navigation, enterprise scenario catalog and
diagnosis consume that published composition; current company enablement,
user roles, native ACL and company scope remain live runtime decisions.

Installed native capabilities do not pass through a second product-release
approval. Installation plus platform SEC/ACL determines their runtime
availability. Product publication only fixes which maintained business
scenarios are part of the product and how those installed entries are grouped.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P0/P1 |
| Layer Target | P0 product policy/release snapshot mechanism and P1 construction scenario composition |
| Standard vs User-Specific | Construction product standard with live company enablement |
| Why Here | P0 owns generic snapshots; P1 owns business scenario records and construction projection semantics |
| Why Not Elsewhere | `sc.scene` page versions are a distinct carrier; frontend cannot infer publication; no parallel publication table is added |
| Blast Radius | `sc.product.policy`, release snapshots, runtime scenario navigation, activation catalog, readiness diagnosis and rollback |

## Required validation responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base and dirty scope | required | `make agent.run.resume` | Always required |
| Owning-module ORM baseline | excluded | none | Continued contract-only owner boundary |
| Focused changed behavior | required | `verify.navigation.publication_consumers.unit` | Draft, freeze, published consumption and rollback |
| Existing navigation/runtime families | required | navigation delivery and runtime catalog targets | Adjacent producer/consumer behavior |
| Scene fact boundary | required | `verify.scene.fact_data.boundary.unit` | No fact or permission manufacture |
| Frontend contract family | required | existing workspace scenario lifecycle unit | Runtime navigation consumption remains valid |
| Module upgrade/browser/runtime | excluded | none | No database, environment or deployment work in this batch |
| Remote required gates | required at publication | exact-head PR checks | Integration qualification |

## Carrier mapping

`sc.product.policy.business_scene_composition` stores the maintained business
navigation composition from `sc.product.scenario / entry`. It does not store
page scene contracts or versions from `sc.scene`; those continue through the
existing `scenes` and `scene_version_bindings` carrier.

## Implemented behavior

- The product policy draft contract and freeze surface obtain the maintained
  `sc.product.scenario / entry` composition through a P0 extension seam.
- `business_scene_composition` participates in the draft fingerprint and the
  frozen policy digest. A scenario edit therefore makes a previously frozen
  candidate stale.
- The active release snapshot carries the composition at both policy and
  snapshot top level.
- Runtime navigation, enterprise scenario catalog and readiness diagnosis use
  the published composition. An active legacy snapshot without composition
  yields an explicit empty published scope instead of reading live draft data.
- Rollback naturally restores composition from the target snapshot.
- Current-company enablement, role eligibility, native ACL and company scope
  remain evaluated at runtime.
- Native capabilities are not re-qualified through a second publication step.
  Installation plus platform SEC/ACL determines their availability; product
  publication controls the business scenario composition.

## Review remediation

- Runtime authority no longer applies the product page publication allowlist to
  native execution. `PRODUCT_ENTRY_NOT_RELEASED` cannot originate from an
  installed, SEC-qualified action merely because the old page list omitted it.
- Release preflight accepts a valid business-scene composition even when the
  legacy `menu_groups` page list is empty. The composition's active bindings are
  checked for stable menu/action/model references before the snapshot is written.
- When no active release snapshot exists, the runtime surface is an explicit
  empty published composition. Retained company enablement keys cannot select
  maintained draft scenes, and `load_maintained_runtime_surface` is restricted to
  editing and freezing.
- Directed regression includes native denial control, composition-only freeze,
  draft isolation, publication, rollback and immutable snapshot behavior.

## Validation

| Check | Result |
| --- | --- |
| `verify.navigation.publication_consumers.unit` | passed; tenant activation 94, center projection 9, scenario surface 24 and adjacent suites non-zero |
| `verify.daily.published_face.target.unit` | passed, 6 tests |
| `verify.admin_close_01.backend.unit` | passed aggregate |
| `verify.frontend.workspace_scenario_lifecycle.unit` | passed; affected frontend lifecycle and scenario suites |
| `verify.backend.navigation_delivery.unit` | passed |
| `verify.runtime_capability_catalog.unit` | passed, 27 tests |
| `verify.product_center.policy.unit` | passed, 15 tests |
| `verify.scene.fact_data.boundary.unit` | passed, 1 test |
| `make ci.local.iteration` | passed, exit 0, contract-only |

Two early incremental attempts selected ORM targets outside the declared
contract-only boundary and were interrupted. They are retained as interrupted,
not counted as passes.

ORM, module baselines, module upgrade, browser matrix and environment rebuild
remain `not_run`.
