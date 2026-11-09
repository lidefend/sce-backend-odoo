# NAV-AUTHORITY-LEAK-01：费用动作导航授权泄漏

## Boundary

- Formal Product Layer: P1 construction industry standard product
- Layer Target: role-surface released navigation action authorization
- Module: construction menu exposure and role-surface projection

## Finding

Observed on `sc-local-dev/sc_dev_demo`, acting through the managed demo principals:

- candidate `demo_role_pm`
- capability closure disjoint from finance action groups
- received in released navigation:
  - `smart_construction_core.action_sc_expense_claim_reimbursement_request`
  - `smart_construction_core.action_sc_expense_claim_advance_fund`

Evidence:
`.runtime/m7-matrix-1440-v2/summary.json`, SHA-256
`18941d7b0ffcfa039f048b3578de1f09ff675a0813f21ccc31a58cc595dc911c`.

## Investigation

Root cause:

- `ir.ui.menu.groups_id` on both entries contains the SC entry visibility mode
  (`...02` for reimbursement, `...04` for advance fund).
- `ir.actions.act_window.groups_id` contains the finance capability groups.
- `demo_role_pm` owns both entry-mode groups but no finance action group.
- The released navigation producer checked menu groups and model ACL, but did
  not intersect action groups before publishing an action-backed node.

Fix:

- `smart_core.delivery.menu_service` now removes action-backed native nodes
  whose action groups do not intersect the request user, while retaining
  actionless containers/scene carriers.
- Route publication applies the same action-group predicate.
- Regression tests cover both native-tree filtering and route publication.

## Validation

- `make verify.backend.navigation_delivery.unit`: PASS.
  - 51 menu delivery tests.
  - 10 ACL carrier authorization tests.
  - 3 static route-authority tests.
- `make ci.local.iteration`: PASS, 4 targets.
- Runtime matrix:
  - `sc_test_admin`: both entries remain visible and readable.
  - `demo_role_pm`: `leaked_entries=[]`.
  - `uncovered_entries=0`.
  - Console errors: 0.
- Evidence:
  `.runtime/m9-authority-fix/summary.json`, SHA-256
  `e71420bb576c7ae15bff1ce7af3e6006f05a6052236fb7d6700524b5f26d7d23`.

## Result

Pending clean candidate commit, clean iteration and same-matrix runtime repeat.
