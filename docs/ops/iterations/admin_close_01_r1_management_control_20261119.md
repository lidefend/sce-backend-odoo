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
- Backend stage: completed at `84eddc23d743e2963e73687113add5922a028c09`
- Frontend stage: completed on the shared delivery branch
- Owner independent review: pending the frozen candidate
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

## Frontend handoff

FE-R1-01 keeps enterprise actions enabled according to backend execution state,
not their target value. A legal `disable` action with `enabled=false` remains
clickable and submits the target boolean `false`.

FE-R1-02 validates the enterprise response against the operation that initiated
it:

- same requested scene and stored scene;
- same company and enablement scope;
- same target state in the top-level and nested readback;
- `source=ir.config_parameter` and a nonempty storage key;
- committed write and `access_granted=false`.

Missing or mismatched readback never displays success and never replays the
write. Verified write followed by navigation failure retains the readback and
offers read-only refresh recovery.

FE-R1-03 and FE-R1-04 use the backend promotion action as the executable
contract. The frontend validates its actor, target product scope, snapshot
object, parameters, prerequisites, confirmation requirement and authoritative
readback. Missing declarations fail closed. Promotion submits the declared
params and requires the declared confirmation.

FE-R1-05 adds page-scoped console/page error collection for platform, enterprise
and business browser contexts.

## Joined candidate evidence

The existing isolated candidate profile was normalized through the governed
fixture and release-snapshot entries after the backend artifact was rebuilt from
Git object `a0d35288562adb52031fb1eabfc538294ead0ca2`.

- fixture: 14 managed users, companies `FE Company A/B`, project carriers and
  acceptance records re-applied;
- standard release: `frontend-audit-a0d35288562a`, snapshot `3`, 132 menus;
- candidate backend artifact digest:
  `699580b954c469fb240163994a4d0ca52a3e19a0b7196d0c257707b27e6b9678`;
- candidate frontend rebuilt through the registered preview entry.

The browser journey passed 45 assertions:

- enterprise enable returned an identity-bound readback from
  `ir.config_parameter`;
- the ordinary project user opened the project-ledger formal navigation route;
- enterprise disable submitted `false` and read back disabled;
- the platform context passed 17 governed entries and permission denial checks;
- all three browser contexts had zero unexpected console/page errors.

Raw readback:
`.runtime/agent-runs/ADMIN-CLOSE-01-R1-MANAGEMENT-CONTROL-20261119/browser/readback.json`
(SHA-256 `3ed9c7a2e63899c8bc82e65ded87fc1b9791024a91936f6680e5786b4591abb1`).

The candidate tenant has no platform-control administrator. Promotion execution
is therefore proven by the governed ORM sample and strict frontend contract
tests; the candidate browser does not claim a platform-release click.

## Final affected validation

The final `make ci.local.iteration` passed 11 target closures on the R1 branch,
including:

- backend admin unit and scene ORM groups;
- navigation delivery and publication consumers;
- capability explorer producer and frontend consumer;
- scenario lifecycle and strict promotion contract tests;
- strict frontend lint and typecheck.

The candidate frontend production preview build passed through the registered
`frontend.standard.preview.build` entry. `verify.frontend.build` was not used in
this worktree because its declared daily `.env.dev` input is absent; the
candidate preview build consumed the registered candidate profile instead.

The first candidate backend restart used the primary worktree's stale acceptance
artifact. That was detected from the old readback shape before acceptance was
recorded as a pass. `acceptance.artifact.verify` was rebuilt from candidate Git
object `a0d35288562adb52031fb1eabfc538294ead0ca2`, the candidate container was
replaced with a rollback container, and the readback source/version was checked
again before rerunning the browser.
