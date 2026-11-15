# WORKBENCH-HOME-MERGE-20261115

## Candidate

- Baseline: `d019b7e9cab961259e42cdc3196cf58f052133c2`
- Branch: `fix/workbench-role-home-nav-20261115`
- Stage: implementation complete, verification pending

## Scope

- Move `workspace.home` from the synthetic `我的场景` center into the existing
  construction `工作台` center.
- Sort the workbench center before all other top-level navigation centers.
- Keep the platform-minimum navigation aligned with the same home group.

## Exclusions

- No route, action, permission, scene content, frontend business mapping,
  database migration, deployment or merge change.

## Verification

- `verify.nav01.native_authority.unit`: PASS, 92 tests.
- `verify.backend.navigation_delivery.unit`: PASS.
- `make ci.local.iteration`: PASS, including the affected navigation ORM test
  and the repository incremental gates.
- PR #888 CI repair: `verify_coverage` initially found seven changed ORM tests
  without execution evidence because
  `addons/smart_core/tests/test_scene_nav_contract_builder.py` was not imported
  by the test package.
- `addons/smart_core/tests/__init__.py`: now imports the builder test module so
  Odoo test discovery sees its exact selectors.
- Restored execution exposed one stale assertion: `/s/projects.dashboard` is a
  valid scene route and must remain in the delivery-ready scene set. The test
  expectation now matches the existing scene-route contract; product code was
  not changed.
- `make local.dev.test MODULE=smart_core
  TEST_TAGS=/smart_core:TestSceneNavContractBuilder`: PASS, 7 tests.
- Post-repair `make ci.local.iteration`: PASS, including nine affected targets
  and the 65-test ORM result guard.
- Local runtime readback for `demo_full`: PASS.
  - Top-level order starts with `工作台`, followed by the remaining business
    centers.
  - `我的场景` is absent.
  - `角色首页` is a direct child of `工作台`.
  - Existing entry identities and `workspace.home` route remain unchanged.

Runtime evidence:
`.runtime/agent-runs/WORKBENCH-HOME-MERGE-20261115/runtime-navigation.log`
SHA256: `263257722b14f539ef090254f6d39c2d7711dccb28edcda24984f603c2c0c648`
