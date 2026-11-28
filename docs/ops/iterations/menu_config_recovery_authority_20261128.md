# Menu configuration recovery authority 2026-11-28

## Proven facts

The persisted `construction.standard` product policy contains 7 product
configuration menus, while the shipped locked policy contains 18. The
`business_config_admin` system-init surface therefore releases 133 leaves
instead of the 143 formally declared units.

Five entries remain below an inactive legacy parent:

- business category
- data dictionary
- budget type
- stage requirements
- approval scope users

Five more are absent from the business configuration admin surface:

- enterprise business roles
- enterprise role assignment
- role authority changes
- role authority events
- business scenarios

The menu configuration page itself loads successfully and exposes 160 menus,
but none of the ten absent entries is configurable. Direct native writes to
`ir.ui.menu` and `res.groups` are denied to the business configuration admin.

## Responsibility

P0 `smart_core` owns the generic menu-configuration panel and consumes the
product-owned recovery catalog. P1 `smart_construction_core` owns the locked
product menu policy, persisted policy synchronization, release snapshot
publication, menu parent facts, recovery catalog facts and the business
configuration admin role surface.

The repair must add new shipped rows without replacing operator-maintained rows
and must publish all missing formal rows in one active release snapshot.

The menu configuration panel must also consume the formal product-configuration
recovery catalog independently of the persisted policy and released navigation.
Otherwise a stale policy hides the very entries the configuration administrator
needs to repair, leaving the administrator dependent on direct native writes.

## Persistent database boundary

Source and disposable-database validation may proceed immediately. Applying the
migration to `sc_dev_demo` requires an explicit persistent migration authorization
because it writes product policy, release snapshot and menu parent facts.

## Source repair

P0 `smart_core` now consumes a product-owned menu-config recovery catalog from
the extension hook. The catalog is part of the formal product-configuration
surface, not the persisted navigation result, so a stale policy cannot remove
the administrator's recovery candidates.

P1 `core_extension_hook_facts.py` declares the complete formal product
configuration recovery catalog. The P1 policy synchronization merges newly
shipped locked rows into the existing maintained policy, preserves maintained
labels, and publishes one active release snapshot for the complete delta.

Migration `17.0.0.189` restores the five menus below the active product
configuration center and reconciles both `construction.standard` and
`construction.preview`. It does not modify groups, users, record rules or
business data.

## Verification

- `verify.business_config.unit`: 199 tests passed.
- `verify.role_surface.landing.contract.unit`: 35 tests passed.
- `verify.extension.hook_contracts.unit`: 9 tests passed.
- `verify.frontend.dev.incremental.unit`: 300 tests passed.
- `TestLockedMenuPolicyInitialization` disposable ORM: 9 tests passed.
- `verify.navigation.projection.orm`: 44 tests passed.
- `make ci.local.iteration`: 23 affected targets, 399 non-zero tests and zero
  unmapped paths passed.

The first ORM attempt exposed a duplicate-row defect in the new bulk merge path:
when no active snapshot existed, the complete target policy was built first and
then the requested row was appended again. The merge now checks the target
policy before inserting and the focused retry plus the full class both passed.

The owning-module baselines for `smart_construction_core`, `smart_core` and
`smart_construction_scene` remain deferred to exact-head remote PR CI as required
by the repository iteration policy.

## Remaining boundary

No persistent database or runtime deployment was changed in this local batch.
The `sc_dev_demo` migration and role-surface readback require the separately
stated owner confirmation for module `smart_construction_core` version
`17.0.0.189`.
