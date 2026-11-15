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
- Independent review repair: the first candidate produced two top-level
  `工作台` centers because the role-home leaf used `catalog.工作台` while the
  existing workspace entries used `construction.工作台`.
- `resolve_horizontal_work_center()` now emits the existing
  `construction.<center-name>` identity, so the home leaf joins the native
  workspace center instead of creating a parallel center.
- `merge_authenticated_safe_landing()` now enforces the ordering invariant even
  when the home leaf is already present, and defensively coalesces duplicate
  workbench groups.
- Added regressions for existing-home reordering and duplicate workbench
  coalescing; `test_platform_minimum_nav_contract.py`: PASS, 8 tests.
- Scenario projection guard and native authority checks: PASS.
- Odoo ORM `TestSceneNavContractBuilder` in both the development database and
  a fresh isolated test database: PASS, 7 tests each.
- Exact `system.init` readback across `demo_full`, PM, finance, owner and
  executive roles: each returns exactly one `工作台` at top-level index 0,
  `角色首页` is a direct child, and `我的场景` is absent.

The earlier runtime summary from the pre-repair candidate is retained only as
historical iteration evidence and is not evidence for the final candidate.
