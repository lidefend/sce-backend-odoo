# Daily payroll entry for the full-product principal

Date: 2026-11-13

Branch: `fix/daily-payroll-full-principal-20261113`

Baseline: `413e791d3c317808ef13fd2dd6a688405c66ecfe`

## Product result

The released `smart_construction_core.menu_sc_payroll_management` entry must be
available to the standard business-full principal, while the existing initiator
and business-configuration audiences keep access.

## Ownership

- Formal Product Layer: P1 construction industry standard product
- Layer Target: native administration-center payroll action authorization
- Module: `smart_construction_core`
- Standard vs User-Specific: construction product standard
- Why here: the native action is the source that decides whether the menu target
  may execute for a principal. The frontend consumes that decision and the demo
  account must not be special-cased in database data.
- Why not elsewhere: a frontend override would invent authorization semantics;
  a runtime-only grant would be lost on rebuild; broad role inheritance would
  change unrelated capabilities.
- Blast Radius: the payroll menu action and its focused release guard only.

The frontend incremental planner did not map the administration-center native
view or its focused guard. That made `ci.local.iteration` stop at an unmapped
path before executing the owning check. The same batch adds an explicit planner
route to the existing guard and a regression assertion for all three input
paths. This is P4 routing only; it does not add a second product assertion or
change the expected behavior.

## Runtime evidence

The governed daily published-face convergence on `413e791d` failed the standard
release gate with:

```text
construction.standard published native entries missing from delivery:
['smart_construction_core.menu_sc_payroll_management']
```

Read-only runtime observations on duty `demo`, database `sc_demo` established:

- `demo_full` is the unique active full-product principal, uid 42.
- Its resolved role surface is `business_full`, not `business_config_admin`.
- The payroll menu is natively visible under the entry visibility mapping.
- The payroll action still names only
  `group_sc_cap_business_initiator` and
  `group_sc_cap_business_config_admin`.
- The delivery projection therefore removes the action menu from the final
  business-full navigation.

The same observation returned zero navigation/authority mismatches for the
remaining visible entries, so the failure is isolated to this native action
group declaration.

## Validation

The first `ci.local.iteration` attempt stopped before executing the owning check
because the P4 incremental planner had no route for the administration-center
native view or guard. This was classified as a validation-tool routing defect.
The planner route and its regression test were added; the same failure was not
retried unchanged.

| Layer | Entry | Result |
| --- | --- | --- |
| L1/L2 | `make verify.product.administration_center.wave1.guard` | PASS, 3 tests plus executable guard |
| L1 | `make verify.frontend.dev.incremental.unit` | PASS, 130 tests |
| L1 | `make verify.agent.ledger.unit` | PASS, 18 tests |
| L1 | `make verify.agent.resume.unit` | PASS, 57 tests |
| L1/L2 | `make ci.local.iteration` | PASS after planner routing repair |
| L1/L5 prep | `make ci.delivery.freeze.prepare` | PASS; generated complexity reports refreshed |

The passing incremental receipt is:

```text
.runtime/frontend-dev-validation/executions/20261112T194118Z-1135636-353426758/receipt.json
```

It records four required targets, zero unmapped paths, zero blocked targets and
`status=passed`. The focused guard proves both positive and negative behavior:
the updated action passes, while omission of `group_sc_business_full` fails.

`ci.delivery.freeze.prepare` refreshed only the generated complexity report and
split-plan queue identities for the two changed verification tools; its
generated-evidence and contract-basis preflights both passed.

Still not run at this point: module upgrade on the daily duty, published-face
convergence, entry verification, independent exact-head review and browser
business acceptance. These remain required after the protected merge.

## Rollback

Revert the P1 action and guard commit. No business rows, user memberships, model
ACLs, or record rules are changed by this batch.
