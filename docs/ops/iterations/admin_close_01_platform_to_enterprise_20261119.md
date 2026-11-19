# ADMIN-CLOSE-01: Platform management to enterprise receipt

## Result boundary

This run closes one product result: a platform administrator can understand and
operate a product-version flow, an enterprise configuration administrator can
enable an eligible released scenario for one explicit company, and an ordinary
authorized user can use the resulting formal entry. Capability discovery,
product qualification, active product version, enterprise enablement and
current-user access remain separate facts.

The first real sample is the project ledger entry:

- menu XMLID: `smart_construction_core.menu_sc_project_project`
- action, scene and native view identities: resolved from the governed runtime,
  never guessed in the frontend or test data
- expected business result: an authorized ordinary user reaches and uses the
  existing project ledger after platform and enterprise readiness are satisfied

The payment entry, personal preferences, custom fields, LC-CLOSE-01 form
configuration editing and production deployment are outside this batch.

## Architecture declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P0 platform kernel with P1 construction qualification and scenario enablement |
| Layer Target | `smart_core` release/capability mechanisms; `smart_construction_core` product qualification; `smart_construction_scene` company scenario activation; shared frontend contract consumption |
| Module | `smart_core`, `smart_construction_core`, `smart_construction_scene`, `frontend/apps/web` |
| Standard vs User-Specific | Standard construction product with explicit runtime company and role-target scope |
| Why Here | These layers own the existing release mechanism, construction publication evidence, enterprise activation decision and generic consumer UI |
| Why Not Elsewhere | The frontend cannot infer qualifications or precedence; P4 cannot become product authority; platform admin identity cannot broaden enterprise company scope |
| Blast Radius | project-ledger capability discovery, product draft/version actions, enterprise activation catalog/write and resulting ordinary-user navigation |

## Pre-iteration gate responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | L0 preflight and clean candidate before handoff | always |
| owning module baseline coverage | required | registered `smart_core` / construction module baseline or a recorded reusable receipt | P0/P1 behavior changes |
| existing affected test families | required | platform explorer, navigation publication consumers, capability identity and release-operator tests | changed shared handlers/services |
| focused changed tests | required | backend admin-flow target plus frontend explorer unit | new action/scope/qualification assertions |
| contract/schema/consumer | required | capability explorer, release surface and scenario activation consumers | contract shape changes |
| frontend lint/type/build | required after frontend writer | registered frontend targets | TypeScript/Vue changes |
| runtime/browser journey | required | governed platform-admin, enterprise-admin and ordinary-user journey | user-visible management flow |
| remote required gates | required | exact-head PR checks | publication and merge |

## Stage ownership

Only one writer is active at a time.

1. `BE-ADMIN-CLOSE-01`: backend writer owns all product and backend-test edits.
2. `FE-ADMIN-CLOSE-01`: frontend writer takes ownership only after an exact clean
   backend SHA and consumption samples are recorded.
3. `REVIEW-ADMIN-CLOSE-01`: independent read-only reviewer binds to the frozen
   combined candidate and does not edit the worktree.

## Acceptance sequence

1. Platform administrator finds the project-ledger capability and sees its native
   source, consumer/support state, product qualification and evidence.
2. The administrator sees the active product version, draft difference, release
   blockers, available actions and rollback target.
3. A product draft change is read back with its product scope and version; a
   promotion or rollback result is read from the authoritative surface.
4. Enterprise configuration administrator sees actor identity separately from
   target company, can enable only an eligible released scenario and gets a
   company-scoped readback.
5. An ordinary authorized user reaches the project ledger from the formal menu
   and completes the agreed existing read/business operation.
6. Another company, an unauthorized role and a direct link remain constrained by
   backend authority.

The implementation must keep product qualification distinct from native
existence, menu `release_state`, enterprise enablement and current-user access.
No frontend precedence rule may override backend source-tracing.

## Reuse and invalidation

CLOSE-03-R1 evidence remains historical and is reused only where its declared
inputs are unchanged. This run invalidates relevant capability explorer, release
surface, scenario activation and frontend consumer evidence when their source,
tests or governed runtime identity change.

## Current state

- Baseline: `0dc7778132a6814e3cb18eb7cecb3ba39ac5df71`
- Backend stage: completed on the delivery branch
- Frontend writer: active after backend handoff
- Production: not touched
- Deployment and user acceptance: separate from PR merge

## Backend handoff

The backend additions keep the five decisions separate:

1. native source existence and identity;
2. consumer/frontend support for the action surface;
3. construction product qualification backed by an active published snapshot;
4. the entry release state and active product version;
5. enterprise scenario enablement for one company, followed by current-user
   navigation/ACL evaluation.

Release operator actions now carry actor identity, target product scope,
operation object, prerequisites, reason codes and the authoritative readback
surface. Enterprise activation returns actor, explicit company target scope,
role-scope applicability, enablement blockers and a persisted company-scoped
readback. Enabling a scenario reports `access_granted=false`.

The runtime project-ledger sample binds:

- menu `smart_construction_core.menu_sc_project_project` / ID `382`
- action `smart_construction_core.action_sc_project_list` / ID `590`
- model `project.project`
- active construction standard snapshot version
  `admin-close-01-runtime-sample-v2`, with a changed page and rollback target
  `admin-close-01-runtime-sample`
- company scope `My Company` / ID `1`, not a global enterprise write
- an authorized project user resolving to `CURRENT_USER_ENTRY_AVAILABLE`
- a no-permission user resolving to explicit enterprise/group denial

Raw samples:

- `.runtime/agent-runs/ADMIN-CLOSE-01-PLATFORM-TO-ENTERPRISE-20261119/backend_contract_sample/project_ledger_runtime_sample.json`
- `.runtime/agent-runs/ADMIN-CLOSE-01-PLATFORM-TO-ENTERPRISE-20261119/backend_contract_sample/project_ledger_denied_sample.json`

Focused validation passed:

- `verify.admin_close_01.backend.unit`
- `verify.admin_close_01.runtime.orm` (2 ORM tests)
- `verify.admin_close_01.scene.module_baseline` (8 collected cases)
- `verify.navigation.publication_consumers.unit`
- `verify.capability.identity_boundary.unit`

Known baseline debt remains explicit:

- full `smart_core` module baseline: failed without a usable collected count;
- full `smart_construction_core` module baseline: 117 failures / 38 errors of
  1473 executed tests.

No logged failure names the changed capability explorer, contribution provider,
release operator or scenario activation files. The focused and affected
families above pass, while the full module results remain failed.
