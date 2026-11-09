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

Pending producer trace.

## Validation

Pending.

## Result

Planned.
