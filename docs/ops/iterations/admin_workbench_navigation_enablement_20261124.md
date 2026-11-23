# Business Center Navigation Follows Scenario Enablement

Status: verification_pending

## Product result

An authorized scenario-exempt page remains usable by the internal business
flow, but it no longer creates a visible business center while the owning
business scenario is disabled. This removes the contradictory state where the
scenario catalog reports the Workbench or Administration center as not enabled
while navigation still exposes that center.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | Construction scenario navigation eligibility |
| Module | `smart_construction_core`, `smart_construction_scene` |
| Standard vs User-Specific | Construction product standard |
| Why Here | P1 owns both center composition and tenant scenario enablement facts |
| Why Not Elsewhere | The frontend must not infer enablement; native ACL and internal route authority must remain unchanged |
| Blast Radius | `system.init` business-center navigation, Workbench and Administration visibility, configuration and initialization direct pages |

## Confirmed runtime observation

On local `sc_dev_demo` at source `7a41b86b073e0f062a1ee7f38aa628d375587954`:

- Workbench catalog status is `not_enabled`, but its navigation center is present.
- Administration catalog status is `not_enabled`, but its navigation center is present.
- All 4 Administration business scenarios report `tenant_enabled=false`.
- The Administration center is materialized by the direct initialization page
  `enterprise.user` (`smart_construction_core.menu_sc_runtime_user_management`).
- Configuration direct pages are intentional and must remain available.

## Implementation boundary

- Direct-platform exemptions continue to preserve backend route authority.
- Navigation eligibility is separate from route authority.
- `configuration` direct pages remain navigable.
- `workbench_direct` and `platform_initialization` pages do not manufacture a
  business-center navigation entry until their owning scenario is enabled.
- Enterprise initialization remains reachable through `enterprise.setup`.

## Verification plan

- P1 projection unit and contract tests.
- Non-zero `smart_construction_core` targeted ORM regression.
- Runtime readback proving Workbench and Administration are absent while all
  business scenes are disabled, and configuration remains available.
- Approving-scenario positive case proving the center returns when enabled.

## Verification result

- `make verify.admin_close_01.backend.unit`: PASS, 169 tests.
- `make verify.smart_construction_core.migration_compatibility.orm`: PASS, 19 tests.
- `make verify.daily.permission_truth.capability.orm`: PASS, 83 tests.
- `make verify.smart_core.intent_smoke.orm`: PASS, 10 tests.
- `make ci.local.iteration`: PASS, 6 required targets executed.
- Local runtime readback on `sc_dev_demo`:
  - all 10 business centers report `not_enabled`;
  - Workbench and Administration center are absent from `system.init` navigation;
  - Product Configuration remains visible;
  - default route remains `/s/enterprise.setup`;
  - no frontend source was changed.

Two initial ORM failures were test-fixture defects, not product regressions:

- the first used an actionless Workbench shell menu to construct an action
  authority;
- the second referenced a full-bundle-only scene XMLID in the smaller
  `smart_construction_core` test template.

The P0 `system.init` smoke had assumed that Workbench navigation must exist even
when every business scene is disabled. The test now validates the navigation
contract in both states; the P1 ORM positive case proves that enabling the
owning scenario restores the center.

## Exclusions

- No frontend source change.
- No new state model or registry.
- No ACL, route-authority, database-schema or tenant-selection change.
- No production deployment.

## Next exact step

Commit the clean candidate, publish the exact-head PR, and require current-base
CI before protected integration.
