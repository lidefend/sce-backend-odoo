# Navigation contract compiler (2026-11-11)

## Boundary

This P0 batch extracts the final navigation assembly currently embedded in
`system.init`.

The compiler consumes already-produced authority:

- canonical navigation from delivery;
- role surface;
- platform release gate;
- platform-duty and scene-internal route authority;
- the P1 scenario-surface projection.

It does not select menus, grant roles, enable tenants, publish products or
define scenario composition. It seals the supplied stages into one final
navigation contract and derives route and final product-policy projections from
that same scenarioized tree.

## Exclusions

- No frontend change.
- No menu/action/view/group/ACL fact change.
- No tenant enablement or scenario composition data change.
- No replacement of the existing native-center scenario adapter in this slice.
- No schema or business-data migration. The existing persistent local database was
  module-upgraded only to execute the same candidate code.
- No deployment, PR or remote mutation.

## Result index

The final compiler pipeline is:

1. build the candidate route authority once;
2. apply release qualification;
3. merge platform duty and scene-internal authority;
4. filter the navigation once;
5. project canonical identity once;
6. apply the scenario provider once;
7. derive final routes and product policy once;
8. verify that scenarioization added no authority.

This removes the previous filter-after-publication / filter-after-scene-internal
sequence and gives later capability and scenario-composition refactors one seam.

## Validation

- `make verify.navigation_contract_compiler.unit`: 3 tests passed.
- `make verify.backend.navigation_delivery.unit`: 68 tests passed.
- `make verify.system_init.menu_boundary.guard`: 7 tests passed.
- `make verify.frontend.dev.incremental.unit`: 114 tests passed.
- `make verify.navigation.publication_consumers.unit`: 169 tests passed.
- `make verify.frontend.scene_entry_contract.unit`: frontend contract cases passed.
- `make ci.local.iteration`: passed.

## Persistent runtime comparison

The local persistent database `sc_dev_demo` was upgraded with the candidate
`smart_core` implementation and read through the same inventory tool.

- audit artifact:
  `artifacts/backend/navigation_contract_compiler_inventory_v1.json`
- artifact SHA-256:
  `06dd16ba66a1cd8a8349d7d10ed69ce8dd03fa9bed8e30ca710f9071ff6bbe09`

For all seven measured principals, the old and new implementations produced
identical:

- native visibility;
- final scenarioized navigation;
- route authority;
- final product policy;
- My Work and enterprise-initialization observations;
- tenant configuration observations.
