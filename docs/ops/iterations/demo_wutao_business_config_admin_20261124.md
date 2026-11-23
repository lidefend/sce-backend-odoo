# Demo Wutao Business Configuration Administrator

Status: local validation

## Product result

The canonical demo principal `wutao` resolves as `business_config_admin`
everywhere the product demo chain is installed. The role is defined in the
demo carrier so full rebuilds and targeted demo-user refreshes produce the same
identity.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | `smart_construction_demo` user declaration and seed |
| Module | `smart_construction_demo` |
| Standard vs User-Specific | Construction product standard demo identity |
| Why Here | The demo carrier owns demo principals and their canonical roles |
| Why Not Elsewhere | P0 and the frontend must not encode a demo login's authority |
| Blast Radius | `demo_full` user roles, wutao startup role, demo readiness |

## Validation responsibility

| Lane | State | Entry |
| --- | --- | --- |
| local_targeted | required | demo supplemental unit and local demo baseline ORM |
| remote_integration | required | exact-head PR CI |
| scheduled_release | excluded | follows protected main integration |

## Runtime application

- Local target: `sc-local-dev` / `sc_dev_demo`
- Daily target: duty `demo` / `sc_demo`
- Excluded: production and `platform_control`

## Implementation

- Demo XML and the `demo_10_users` seed assign
  `group_sc_cap_business_config_admin`.
- The lightweight `demo_users` refresh also canonically restores `wutao`.
- Pure static regression checks both seed chains and the full-product XML.
- The demo role-scope manifest now expects `business_config_admin` for
  `wutao`; its previous `business_full` expectation was stale.
- The incremental planner maps the role-scope declaration and probe to the
  existing non-zero role-scope unit instead of treating them as unmapped.
- The now-wired role-scope unit no longer carries the stale zero-reference
  disposition.
- The existing G0-G4 runtime probe remains unchanged and is run only against
  its governed, fully seeded local demo database.

## Local results

- `make local.dev.demo_users.sync`: PASS on `sc-local-dev` / `sc_dev_demo`.
- `make verify.demo.supplemental.unit`: 87 tests passed, including the two
  static `wutao` declaration tests.
- `make verify.demo.usage_foundation_role_scope.unit`: 16 tests passed with
  `wutao` declared as `business_config_admin`.
- `make verify.local.dev.baseline_readiness.orm`: 1 test passed on the fully
  seeded local demo.
- `make verify.frontend.dev.incremental.unit`: 232 tests passed.
- `make verify.verification.lane.coverage`: 74 tests passed with the
  verification surface inside the frozen baseline.
- `make ci.local.iteration`: PASS at `34e0f290889adb015686de4d005a077243fa27da`;
  all 7 affected targets executed, with 0 unmapped paths.
- Read-only startup readback on `sc_dev_demo`: `wutao` resolved to
  `role_code=business_config_admin` with company scope `[1]`.

## Remaining runtime application

- Merge the P1 declaration through the protected mainline.
- Deploy the merged SHA to local and daily development.
- Reapply the demo user/XML declaration in both demo databases and read back
  `wutao` as `business_config_admin`.
