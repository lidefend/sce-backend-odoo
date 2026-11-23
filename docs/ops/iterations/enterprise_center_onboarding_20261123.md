# Enterprise Center-Level Onboarding

Status: committed candidate

## Product result

Enterprise initialization is organized around construction business centers.
The configuration administrator chooses the centers the enterprise operates,
and the backend enables the released scenarios owned by those centers in one
transactional action.

## Layer declaration

| Item | Declaration |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | `smart_construction_scene` enterprise scenario catalog and center activation |
| Module | `smart_construction_scene`, `frontend` |
| Standard vs User-Specific | Construction product standard |
| Why Here | Center membership and scenario ownership are construction product semantics |
| Why Not Elsewhere | The frontend must not hard-code center-to-scenario mappings; P0 remains generic |
| Blast Radius | Enterprise initialization workspace, scenario catalog contract, center activation, readiness scenario evidence |

## Design

- Workbench is the first of ten selectable business centers and owns the
  `work.my_queue` scenario.
- Selection before submit is a local recommendation only. The UI says
  "selected" until the atomic apply returns persisted enablement readback.
- Product Configuration remains configuration-admin-only and is not one of the
  ten business-center choices.
- Center cards expose the declared scenario count.
- One backend action enables all released scenarios owned by the selected
  centers and returns company-bound readback.
- Individual scenario controls remain available as advanced details.

## Validation responsibility

| Lane | State | Entry |
| --- | --- | --- |
| local_targeted | required | focused ORM, navigation consumer and frontend workspace tests |
| remote_integration | required | exact-head PR CI |
| scheduled_release | excluded | follows protected main integration |

## Local results

| Check | Result |
| --- | --- |
| Product scenario organization unit suite | 14 passed |
| Tenant scenario activation semantic suite | 103 passed |
| Frontend workspace scenario lifecycle | passed, including navigation consumers and controlled contract transport |
| Frontend component driver takeover | 18 passed; scenario detail disclosure uses `ScDisclosure`, not native `<details>` |
| Enterprise initialization ORM journey | 1 passed in the governed disposable `local.test` database; unknown center wrote nothing, `work.my_queue` persisted, and readiness count reached 1 |
| Frontend strict typecheck | passed |
| Frontend source lint | passed with zero errors |
| `ci.local.iteration` | passed; 11 affected targets executed |
| Frontend static build | not_run, `environment_defect`: the worktree has no registered `.env.dev` |

## Remaining work

- Amend the clean candidate with the governed disclosure fix and publish it
  through the GitHub PR lane.
- Wait for required checks on the exact source and current target, then merge
  only after they pass.

Deployment and persistent database synchronization remain excluded from this
batch until mainline integration and a separate deployment decision.
