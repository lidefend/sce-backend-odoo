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

- Baseline: `d5b87e5847ee301dcf5289931ac5643333bad41b`
- Backend stage: completed on the delivery branch
- Frontend stage: completed on the delivery branch
- Independent review: pending on the frozen commit
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

## Frontend consumption

The frontend now consumes the backend contract without inferring qualification,
release state, company scope or access:

- the capability detail shows final availability, actor and target company,
  six independent fact layers, qualification evidence and active product
  version;
- the release console accepts backend-owned actor, target product scope,
  action prerequisites, blockers and post-write readback;
- the enterprise activation panel shows the configuration administrator,
  target company, product qualification/version, blockers and persisted
  company-scoped readback while stating that access was not granted;
- all new response fields are strict contract inputs and missing declarations
  fail closed.

Frontend validation passed:

- `verify.frontend.platform_capability_explorer.unit` (25 frontend cases plus
  the platform-duty family)
- `verify.frontend.workspace_scenario_lifecycle.unit` (13 management cases
  inside the complete lifecycle family)
- `verify.frontend.typecheck.strict`
- `verify.frontend.lint` (warnings only; zero errors)
- `verify.frontend.build` with the governed static-build script
- `verify.platform.capability_explorer.unit`
- `verify.admin_close_01.backend.unit`

The isolated candidate acceptance environment was bound to
`sc-frontend_acceptance_candidate` / `sc-fe-candidate-770`, upgraded for
`smart_core`, `smart_construction_core`, and `smart_construction_scene`, seeded
with the governed acceptance fixture, and given a standard product release
snapshot with 132 menus. Its production frontend was built and served at
`127.0.0.1:5178`; the candidate backend was read back on `127.0.0.1:18088`.

The unified candidate browser journey passed both the capability explorer and
management suites (20 management assertions):

- capability detail rendered the backend's availability and fact layers;
- a tenant identity was redirected away from the platform-control release
  surface, preserving the platform/enterprise identity boundary;
- the enterprise configuration administrator loaded 17 scenarios with an
  explicit company target and no global product-release scope;
- an ordinary business user opened the formal project dashboard.

Raw browser summary and screenshots:
`.runtime/agent-runs/ADMIN-CLOSE-01-PLATFORM-TO-ENTERPRISE-20261119/candidate_browser_journey/`.

### Current-main rerun

After rebasing onto `d5b87e58`, the candidate was rebuilt in the existing
isolated `candidate` profile (`sc-fe-candidate-770` /
`sc_frontend_acceptance_candidate`, frontend `127.0.0.1:5178`, backend
`127.0.0.1:18088`). No daily-development database or deployment environment
was used.

The current source identity was `bf3dcec2542e52b69d84c858636670a965fa52e2`
with only the run baseline/record corrections dirty. `make ci.local.iteration`
passed all 16 affected targets, including the fresh non-zero ORM groups (71 and
6 tests), strict frontend typecheck, lint with warnings only, static proxy and
contract guards.

The rebuilt candidate browser target passed:

- 33 capability-explorer assertions, including 17 governed entries, stale
  catalog-token recovery, detail layers and an exact 403 permission denial;
- 20 platform-to-enterprise management assertions, including tenant routing,
  explicit company scope, ordinary business entry and zero browser errors.

The rejection-probe input was bound to the acceptance carrier's actual
`x-tenant: default` value. This corrected the probe invocation only; no product,
assertion or tenant-scope rule was weakened.

Current raw readback:
`.runtime/agent-runs/ADMIN-CLOSE-01-PLATFORM-TO-ENTERPRISE-20261119/candidate_browser_journey/current-bf3dcec/browser_readback.json`
(SHA-256 `92c6b0ebee0c450c76db10742fc07c4c9fbd6a672ff725e1116c6423640ad0c4`).

The isolated candidate tenant's active capability set excludes the project
ledger and is not the declared `sc_platform_control` instance. Therefore the
positive project-ledger and platform-release browser result is not claimed from
this tenant; those contracts are exercised by the governed ORM sample above.
The independent review must decide whether that evidence boundary is acceptable
for this batch or require the dedicated platform-control/formal-entry runtime.
