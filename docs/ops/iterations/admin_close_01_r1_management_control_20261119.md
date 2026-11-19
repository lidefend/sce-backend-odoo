# ADMIN-CLOSE-01-R1: Management action and diagnostic correction

## Result boundary

This batch corrects five confirmed post-#941 defects without rebuilding the
already delivered six-layer capability states:

1. legal enterprise scenario disablement must remain executable;
2. native-entry group diagnosis must reuse formal navigation semantics;
3. every candidate promotion action must carry the complete operator contract;
4. enterprise write readback must identify its real storage carrier and bind the
   response to the submitted company, scene, scope and target state;
5. browser acceptance must prove a positive publish/enable/use/disable chain
   rather than accepting unrelated pages or denials as substitutes.

The project-ledger entry remains the only cross-role sample:
`smart_construction_core.menu_sc_project_project`. Runtime menu and action IDs
are resolved in the selected acceptance database.

## Architecture declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P0 management/diagnostic mechanisms with P1 construction qualification and enterprise enablement |
| Layer Target | `smart_core`, `smart_construction_core`, `smart_construction_scene`, shared frontend contract consumption |
| Module | `smart_core`, `smart_construction_scene`, `frontend/apps/web`, registered verification tools |
| Standard vs User-Specific | Standard construction product with explicit company-scoped runtime enablement |
| Why Here | These layers own native navigation authority, release action contracts, persistence readback and generic consumption |
| Why Not Elsewhere | Frontend cannot infer OR permission or release action metadata; P4 may execute but not own product semantics |
| Blast Radius | project-ledger capability details, candidate promotion controls, enterprise scenario enable/disable, ordinary-user entry |

## Pre-iteration gate responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | `main@68828a9a` and clean candidate before handoff | always |
| owning module baseline coverage | required | reusable receipt or `verify.admin_close_01.scene.module_baseline`; affected `smart_core` families and full-module fallback if dependency proof is incomplete | P0/P1 service and handler behavior |
| existing affected test families | required | capability explorer, release operator, navigation publication and tenant scene activation | changed shared behavior |
| focused changed tests | required | registered admin-close backend target and scene ORM sample | new positive/negative assertions |
| contract/schema/consumer | required | capability explorer and release/activation producer-consumer tests | contract shape and strict consumption |
| frontend lint/type/build | required | registered frontend targets | Vue/TypeScript changes |
| runtime/browser journey | required | isolated candidate platform/enterprise/ordinary-user journey | user-visible management behavior |
| remote required gates | required | exact-head PR checks | publication and merge |

## Stage ownership

Only one writer is active in this product worktree at a time.

1. `BE-ADMIN-CLOSE-01-R1`: repair native access diagnosis, promotion action
   decoration and activation readback source; produce focused production samples.
2. `FE-ADMIN-CLOSE-01-R1`: repair disable interaction, strict action/readback
   consumption and the positive joined browser journey.
3. Owner review: independent review on the frozen exact candidate.

## Current state

- Base: `68828a9a3919b95ca931d41559889a93bf7fa622`
- Branch: `feature/admin-close-01-r1-management-control-20261119`
- Backend stage: completed; clean handoff commit follows this record
- Frontend stage: pending backend handoff
- Center ownership and composite-version convergence: later batches
- Deployment and product publication: not authorized by this batch

## Rollback

Revert the R1 backend and frontend commits together. Restore any acceptance
company enablement through the same governed scenario activation intent and
verify the previous persisted value. No schema migration is introduced.

## Backend handoff

BE-R1-01 now evaluates menu groups and action groups as two independent native
authorization layers. Each layer uses Odoo's OR-within-layer group semantics;
both layers must pass. `PlatformCapabilityExplorerService` reuses the public
`MenuService._groups_authorize_current_user()` decision, including implied
groups; no second permission algorithm is introduced.

BE-R1-02 decorates each non-empty candidate promotion array before the generic
dictionary guard. Every promotion action now carries actor, product scope,
snapshot operation object, prerequisites and authoritative-readback metadata.

BE-R1-03 binds enterprise activation readback to the actual
`ir.config_parameter` storage key:

- response `source` is `ir.config_parameter`;
- `storage_key` is
  `sc.scene.tenant.enablement.<company_id>.<stored_scene_key>`;
- the response includes requested scene, stored scene, enablement scope and
  target state;
- legacy `sc.scene.company.enablement` remains read-only compatibility;
- `access_granted` remains false because enablement never grants user access.

BE-R1-04 production samples are stored under:

`.runtime/agent-runs/ADMIN-CLOSE-01-R1-MANAGEMENT-CONTROL-20261119/backend_contract_sample/`

The samples bind:

- project-ledger menu `382`, action `590`, model `project.project` in the
  selected runtime database; these IDs are evidence only and are not frontend
  constants;
- candidate snapshot `7`, fully decorated promotion contract and rollback
  readback;
- company `1` enable and disable with `target_state=true` / `false`;
- unaffected company `2`;
- an authorized native-access diagnosis and a denied-user diagnostic sample.

Focused backend validation passed:

- `verify.admin_close_01.backend.unit`;
- `verify.navigation.publication_consumers.unit`;
- `verify.backend.navigation_delivery.unit`;
- `verify.admin_close_01.runtime.orm` (3 tests);
- `verify.admin_close_01.scene.module_baseline` (9 tests).

`verify.smart_core.close_02.module_baseline` remains failed with
`count=0`. Its observed failures are unrelated authentication, maintenance,
configuration and ORM-family failures; no failure references the changed R1
files. This remains a recorded baseline/coverage blocker rather than a claimed
pass.
