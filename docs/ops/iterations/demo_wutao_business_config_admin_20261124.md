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
- The baseline readiness hard check requires the configuration administrator
  group, not only `group_sc_business_full`.

## Local results

- `make local.dev.demo_users.sync`: PASS on `sc-local-dev` / `sc_dev_demo`.
- `make verify.demo.supplemental.unit`: 85 tests passed.
- `make verify.local.dev.baseline_readiness.orm`: 1 test passed; the updated
  hard check requires both `group_sc_business_full` and
  `group_sc_cap_business_config_admin` for `wutao`.
- `make ci.local.iteration`: passed; 3 affected governance targets executed.

## Remaining runtime application

- Merge the P1 declaration through the protected mainline.
- Deploy the merged SHA to local and daily development.
- Reapply the demo user/XML declaration in both demo databases and read back
  `wutao` as `business_config_admin`.
