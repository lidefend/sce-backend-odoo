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

## Current blocker

The existing managed acceptance database contains 132 published product pages
but only 79 maintained scenario bindings. The release snapshot correctly
rejects the 40-page remainder as unassigned. The versioned add-only migration
must be applied incrementally; a full dependency reinstall was started by an
over-broad `db.frontend.acceptance.ensure` invocation and was stopped after the
first complete upgrade, before the redundant second transaction completed.
