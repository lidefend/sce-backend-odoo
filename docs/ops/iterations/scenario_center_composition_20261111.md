# Scenario center composition (2026-11-11)

## Boundary

This P1 batch moves center-menu organization out of the native
`ir.ui.menu` ancestor chain and into scenario-entry composition metadata.

The native menu remains the capability carrier. The scenario entry now records
the delivered center identity, label and sequence. Existing data receives a
one-time seed from the current native center layout; runtime grouping never
reads that native ancestry again.

Authorized entries without a scenario binding use their delivery-policy group
as an explicit fallback center.

## Exclusions

- No menu/action/view/group/ACL fact change.
- No route persistence.
- No frontend change.
- No multi-scenario reuse change in this slice.
- No deployment, PR or remote mutation.

## Runtime migration result

The persistent `sc_dev_demo` database upgraded through
`smart_construction_core 17.0.0.179`:

- 79 scenario entries;
- zero entries without a center identity;
- eight composed centers;
- all seven measured principals retained identical final navigation, route
  authority, product policy and targeted-capability observations.

Runtime evidence:

- artifact:
  `artifacts/backend/scenario_center_composition_inventory_current.json`
- artifact SHA-256:
  `d99dfa4d93f4759b274434abfdb88ec3a451320357f1664584fbca5edae93efe`

## Validation

- `make verify.scenario.center_projection.guard`: 6 tests passed.
- `make verify.backend.navigation_delivery.unit`: 73 tests passed.
- `make verify.navigation.publication_consumers.unit`: 175 tests passed.
- `make verify.frontend.dev.incremental.unit`: 117 tests passed.
- `make verify.daily.permission_truth.capability.orm`: 13 tests passed.
