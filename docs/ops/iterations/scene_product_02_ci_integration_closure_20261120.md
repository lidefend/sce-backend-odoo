# SCENE-PRODUCT-02 CI Integration Closure

Candidate under repair: `77bad6caf94e3ab01d18b8d45d4614bd2730b6ad`

Pull request: #951

## Product result

Keep the approved workbench plus ten-center skeleton, 46 scenario groups and
132 organized handling surfaces unchanged while closing the integration
failures between product scenario organization, platform direct-entry
initialization, enterprise scene publication/enablement and release composition.

## Fixed boundaries

- `sc.product.scenario` owns business organization.
- `sc.scene` owns scene content and publication state.
- `sc.scene.company.enablement` owns enterprise selection of a genuinely
  published scene.
- `sc_scenario_exempt` only controls scene-enablement filtering; it does not
  grant native ACL or company scope.
- Preview, ACL, company scope and release composition remain fail-closed.

## Work log

- Registered the closure run.
- Corrected the run baseline to the reviewed candidate
  `77bad6caf94e3ab01d18b8d45d4614bd2730b6ad`; the previous main base made
  the topic commits appear outside scope.
- Reproduced the frontend state guard mutation defect. The guard now checks
  both the contract-gap and product-state opening containers, and separate
  mutations remove each declaration.
- Audited the direct platform menu overlap. Scenario-bound system shell,
  workbench and platform initialization entries retain their scenario
  organization while an explicit `direct_platform_exempt` fact bypasses only
  company scenario filtering. Native menu groups, ACL and company access remain
  authoritative.
- Added `direct_platform_pages` to the generated scenario surface. Release
  validation now distinguishes business scenario references from explicitly
  declared platform direct pages and checks action targets only for the current
  release surface, so a partial product draft no longer validates unrelated
  shared composition members.
- Added `17.0.0.186` migration to append missing standard scenario bindings on
  an existing database through the existing idempotent, add-only importer. It
  does not delete maintained scenarios or overwrite administrator changes.
- Runtime readback showed the database held 63 scenario definitions: the 17
  retired process scenarios plus the current 46 business-result scenarios.
  Because add-only import never deletes, the retired 79 menu bindings blocked
  their replacement scenarios. `17.0.0.187` now retires only the exact 17
  known standard process identities, keeps the same menus and native actions,
  then adds the current 46 groups. Administrator-created scenario codes are
  outside the retired set and are preserved.
- Replaced the acceptance fixture's retired 17-scene list with the current 46
  declared scenarios. Bundle tests now use `finance.intercompany`,
  `contract.registration`, `cost.budgeting` and `contract.settlement` instead
  of retired scene identities.

## Verified so far

- `verify.frontend.state_dashboard.unit`: 86 passed.
- `verify.daily.published_face.target.unit`: 13 passed.
- `verify.admin_close_01.backend.unit`: 166 passed.
- `verify.nav01.native_authority.unit`: 66 passed.
- `verify.product.scenario.organization.unit`: 13 passed.
- `TestScenarioDirectInitialization` on managed fresh `sc_test`: 16 passed.
- `TestProductPolicyFactAuthority` on managed fresh `sc_test`: 23 passed.

## Final local verification

The acceptance database was found to contain 132 published product pages but
only 79 maintained bindings, followed by 63 scenario definitions. This proved
the old 17 process scenarios and current 46 business-result scenarios were
coexisting. The final migration retires only the exact known standard process
identities and re-imports the current groups.

Acceptance full-database reinstallation was not used as the local closure path.
The exact fixture preparation function is exercised on a fresh isolated
`sc_test` database with a fixture-owned company: all 46 current scenario keys
enable and all 46 company selections read back.

- `TestScenarioDirectInitialization`: 18 passed, including the legacy
  retirement transition and native-center fallback.
- `TestProductPolicyFactAuthority`: 23 passed.
- product-center policy ORM: 3 passed.
- bundle workspace journeys: 11 passed.
- fixture scenario identity ORM: 1 passed.
- `ci.local.iteration`: 15/15 planned affected targets passed; the planner
  reported no unmapped paths.

Remote managed ORM then exposed two additional stale test assumptions: the
fixture's explicit project Kanban binding still used `project.management`, and
maintenance tests tried to publish after deleting the only binding of a
published page or after making a normal business page temporarily direct.
The binding now uses `reporting.project_portfolio`; zero-binding scenario
definitions are omitted from the release composition, while published business
pages without a scenario/direct declaration remain blocking. The tests now
assert that blocking outcome instead of manufacturing an executable route.

Migration safety was tightened before another candidate:

- the complete 17-scenario legacy standard binding allow-list is frozen in
  `17.0.0.187`;
- any extra binding under a legacy standard scenario blocks the migration before
  deletion and identifies the retained scenario/entries;
- custom scenarios and custom entries outside the exact 17 codes are preserved;
- scenario-surface import is idempotent per scenario/menu rather than globally
  excluding a menu already used by another scenario;
- the migration verifies all 46 current scenario codes and 132 unique standard
  menu bindings after the transition.

The exact local acceptance fixture suite now runs on isolated `sc_test` with a
real release snapshot. It passed 28/28, including real 46-scenario enablement
and a Preview scene rejection. The migration safety class passed 20/20, and the
final pre-push `ci.local.iteration` passed all affected targets.

Owner rule added 2026-11-21: no schema/data/scenario/seed/release/fixture
migration may execute until the owner explicitly confirms both that a migration
is required and the exact execution target. This includes disposable copies,
test databases, dry-runs and fresh installation. Future migration verification
must stop after read-only analysis and the written migration plan unless that
confirmation is present.
