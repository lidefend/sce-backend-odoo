# System Product Release Bootstrap

Status: implementation

## Product result

The shipped construction product is materialized automatically whenever
`smart_construction_core` is installed or upgraded. Administrators receive an
active system release and enable business centers; they do not publish the
product itself.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | `smart_construction_bundle` product release finalization |
| Module | `smart_construction_core`, `smart_construction_bundle` |
| Standard vs User-Specific | Construction product standard |
| Why Here | Core owns the locked policy and composition; the bundle is the complete product assembly point |
| Why Not Elsewhere | P0 already owns snapshot mechanics; P4 verifies deployments; the frontend must not synthesize product releases |
| Blast Radius | install/upgrade hooks, active release snapshots, scene catalog |

## Implementation

- The `smart_construction_bundle` post-install hook synchronizes the locked
  product policy and materializes its active release snapshots after every P1
  dependency is loaded.
- `ensure_system_product_release_snapshots` reuses a valid active snapshot and
  freezes the shipped policy when the snapshot is absent, legacy or empty.
- Bundle migration `0.1.2` applies the same idempotent initialization to
  existing databases.
- The incremental planner routes bundle migration and release tests to their
  owning checks without manual target selection.
- Fresh-install tests assert one active snapshot per shipped product key, the
  46-scene composition, frozen integrity and runtime publication scope.

## Validation responsibility

| Lane | State | Entry |
| --- | --- | --- |
| local_targeted | required | `make verify.smart_construction_bundle.system_product_baseline.orm` |
| remote_integration | required | exact-head required PR CI |
| scheduled_release | excluded | follows protected main integration |

## Local results

- `make verify.smart_construction_bundle.system_product_baseline.orm`:
  3 tests passed on a fresh disposable bundle installation.
- Verified standard and preview active snapshots, 46-scene composition,
  frozen integrity, runtime publication scope, idempotency and upgrade repair.

## Boundaries

- No P0 snapshot algorithm change.
- No frontend change.
- No administrator publication step.
- Production deployment is not part of this candidate.
