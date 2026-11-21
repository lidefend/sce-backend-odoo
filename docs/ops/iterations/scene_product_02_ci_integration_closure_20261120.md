# SCENE-PRODUCT-02 CI Integration Closure

Candidate under repair: `77bad6caf94e3ab01d18b8d45d4614bd2730b6ad`

Pull request: #951

## Product result

Keep the approved workbench plus ten-center skeleton, 46 scenario groups and
132 organized handling surfaces unchanged while closing the integration
failures between product scenario organization, platform direct-entry
initialization, enterprise scene publication/enablement and release composition.

## Fresh-install baseline

The owner confirmed on 2026-11-21 that the former 17 process scenarios and
existing development data have no retained value.

- Fresh installation is the only scenario identity baseline for this batch.
- The former `17.0.0.186` and `17.0.0.187` compatibility migrations are removed.
- No old scenario or scene data is preserved, migrated or protected.
- No database, scenario, seed, release snapshot or fixture migration is part
  of this candidate.
- The module version remains `17.0.0.185`.
- Existing unrelated migrations and their tests are not changed.

The owner-confirmed migration rule in `AGENTS.md` remains authoritative for
future work: any proposed migration still requires separately confirmed
necessity, exact target and execution authority.

## Fixed boundaries

- `sc.product.scenario` owns business organization.
- `sc.scene` owns scene content and publication state.
- `sc.scene.company.enablement` owns enterprise selection of a genuinely
  published scene.
- `sc_scenario_exempt` only controls scene-enablement filtering; it does not
  grant native ACL or company scope.
- Preview, ACL, company scope and release composition remain fail-closed.

## Work log

- Registered the closure run and bound it to the reviewed candidate
  `77bad6caf94e3ab01d18b8d45d4614bd2730b6ad`.
- Corrected the frontend state guard so the contract-gap and product-state
  containers are checked separately and each mutation removes its own
  declaration.
- Made direct platform/workbench entry declarations independent of business
  scenario organization while preserving native ACL and company scope.
- Distinguished scenario-bound pages, explicit direct platform pages and
  unassigned pages in release composition validation.
- Allowed zero-binding scenario definitions to be omitted from runtime
  composition while keeping any published page without ownership blocking.
- Aligned acceptance fixtures and bundle tests with the current 46 scenario
  identities.
- Removed the old-data compatibility migrations, their safety tests, stale
  planner mappings and PR/record claims. The fresh-install seed initializer no
  longer exposes a migration-only `force` path.

## Validation status

The latest edits remove migration code and alter the fresh-install seed
initializer, so earlier migration-related receipts are deliberately not reused.

Passed on the current working tree:

- `verify.frontend.state_dashboard.unit`: 27 Python tests plus the frontend
  state cases; guard PASS.
- `verify.product.scenario.organization.unit`: 14 tests.
- `verify.daily.published_face.target.unit`: 13 tests.
- `verify.frontend.dev.incremental.unit`: 190 tests.
- `verify.navigation.publication_consumers.unit`: non-zero suites PASS.
- `verify.scenario.center_projection.guard`: 11 tests.
- `verify.nav01.native_authority.unit`: non-zero suites PASS.
- `verify.admin_close_01.backend.unit`: 166 tests.
- `verify.daily_dev.acceptance_fixture.unit`: 40 tests.
- `verify.frontend.lint.src`: zero errors, three unrelated warnings.
- `verify.frontend.typecheck.strict`: PASS.
- `verify.frontend.release.unit`: PASS.
- `verify.workspace.branch.sync-main`: 51 tests PASS.

The owner authorized only the policy-owned disposable
`sc-local-test / sc_test` fresh-install target. `local.test.prepare` confirmed
that identity before any runtime write. The affected ORM tests then passed:

- `TestScenarioDirectInitialization`: 17 tests.
- product-center policy suite: 3 tests.
- product-center policy additions: 8 tests.
- capability identity boundary: 30 tests.
- scene routing and activation: 80 tests.
- acceptance fixture lifecycle, navigation and identity: 28 tests.
- bundle workspace entry authority: 11 tests.

`ci.local.iteration` passed after every required target was actually executed:
14/14 affected targets, unmatched paths 0, outside-scope paths 0.
`ci.delivery.freeze.prepare` also passed and refreshed generated evidence; the
module dependency map now reports `17.0.0.185`.

The first exact-head remote run passed all four backend shards and Managed ORM.
Its only failure was `verify_coverage`, which reported the newly added
`TestFixtureScenarioIdentity` method as pending. The method already passed in
the local targeted fixture suite, but the managed acceptance selector did not
include its class tag. The test now carries the existing
`acceptance_business_scene_lifecycle` managed tag; no new selector family or
broader test matrix is introduced.

Clean candidate freeze and exact-head remote gates remain pending.

## Exclusions

- No redesign of the ten centers, 46 groups or 132 handling surfaces.
- No legacy-data compatibility path.
- No Preview-to-GA batch promotion.
- No ACL, company-scope or role grant expansion.
- No full ORM suite, complete browser matrix, deployment or product-delivery
  claim.
