# Menu upgrade cache visibility 2026-11-29

## Failure

Deploying main `b974839c` to persistent `sc-local-dev/sc_dev_demo` failed in
migration `17.0.0.189` release preflight. The transaction rolled back and the
database remained healthy on `smart_construction_core 17.0.0.188`.

The failing preflight reported nine product-configuration menus as unassigned
to the business-scene composition:

- business role
- role assignment
- role authority changes
- approval scope users
- business category
- data dictionary
- budget type
- stage requirements
- enterprise role assignment

## Responsibility

P1 `smart_construction_core` owns migration `17.0.0.189` and the product-policy
reconciliation it invokes. P0 release preflight remains fail-closed and must not
be weakened.

The active snapshot carries an older composition with 16 direct platform pages.
The current maintained surface has 25. Reconciliation must use the maintained
composition for the target policy before asking P0 to build and freeze it.

## Repair

The active snapshot carried an older scene composition with 16 direct platform
pages. The current maintained surface contains 25. Reconciliation now sets the
target policy's `business_scene_composition` from
`load_maintained_runtime_surface` immediately before the standard and preview
policies are frozen.

## Verification

- Locked-menu migration ORM: 9 tests passed.
- Navigation projection ORM: 44 tests passed.
- `make ci.local.iteration`: 6 affected targets and 101 non-zero tests passed.
- Persistent upgrade completed with `smart_construction_core 17.0.0.189`.
- standard and preview policies each contain 143 menu rows and one new active
  release snapshot.
- both active compositions contain 25 direct platform pages.
- wutao sees all restored configuration entries; the missing set is empty.
- persistent environment health, entry identity and demo authority checks pass.

Exact-head PR CI remains pending until the corrected source is committed and
published.

## Rollback

The pre-upgrade database and filestore snapshot is
`artifacts/local-dev/snapshots/20261128T181135Z`.
