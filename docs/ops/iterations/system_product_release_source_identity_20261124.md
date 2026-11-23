# System Product Release Source Identity

Status: local runtime validated

## Product result

System product release materialization is bound to the database performing the
installation. A historical database named `sc_demo` in the same cluster can no
longer change the menu identities used by a fresh `sc_dev_demo` installation.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | construction product release source binding |
| Module | `smart_construction_core`, `smart_construction_bundle` |
| Standard vs User-Specific | Construction product standard |
| Why Here | Product release materialization owns its source database identity |
| Why Not Elsewhere | P0 already validates source targets; P4 must not repair product initialization |
| Blast Radius | fresh bundle install, system release snapshot, local/daily demo rebuild |

## Implementation

- An empty catalog source parameter is initialized to the current installation
  database before release preflight and freeze.
- The release environment explicitly carries
  `sc_release_catalog_source_db=<current database>`.
- The test asserts the parameter is the current database and all system release
  invariants still pass.

## Runtime result

- Local `sc_dev_demo` rebuild: PASS.
- Scenario catalog: `ready`, 132 published pages, 46 actionable scenarios,
  10 business centers.
- Active system release created from
  `system-baseline-97092f2d9f0e`.
- `make ci.local.iteration`: PASS at `5d272a481`; two affected backend targets
  executed after rebasing onto main `0412d80ee`.
