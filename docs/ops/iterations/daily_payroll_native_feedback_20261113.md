# Persisted payroll native feedback

Date: 2026-11-13

Branch: `fix/daily-payroll-native-feedback-20261113`

Baseline: `8c2cb2c463fbb6890335936e16e75d8c7b84fb11`

## Product result

The released payroll detail must open for the standard business-full principal
and render its reviewed native processing advisory.

## Ownership

- Formal Product Layer: P0 platform kernel product
- Layer Target: controlled native feedback fact validation
- Module: `smart_core`
- Standard vs User-Specific: platform mechanism
- Why here: the compiled view and P1 declaration are valid, but the generic
  final-node validator still recursively requires every compute dependency to
  be a scalar. That validator owns the reviewed-dependency and actor-permission
  proof for persisted native feedback.
- Why not elsewhere: a frontend fallback would hide a contract rejection; a
  P1 locator change would not address the actual failure; removing the native
  declaration would erase product semantics.
- Blast Radius: persisted form contracts using a declared native advisory with
  reviewed relation-presence inputs. Unreviewed and malformed declarations keep
  the existing strict rejection path.

## Confirmed failure

The governed daily duty `demo`, database `sc_demo`, view
`smart_construction_core.view_sc_hr_payroll_document_form` (ID 1708) compiled
the declared source at:

```text
/form[1]/sheet[1]/div[1]/field[1]
```

The parser emitted the same field identity under the alert host. Replaying the
exact browser request through `UiContractV2Handler` reproduced:

```text
FEEDBACK_SOURCE_INVALID
target=layoutContract.feedback
```

Instrumented validation located the failure in
`read_facts`, where the computed field's reviewed relation dependencies were
still recursively checked against the old scalar-only rule.

## Validation

The platform validator now treats a declared native advisory with reviewed
compute inputs as one exact proof:

- the field must still have `sc_feedback_usage`;
- the compute implementation must be non-stored, non-related, non-sudo and
  reviewed through `_sc_feedback_evaluation_review`;
- the reviewed dependencies must pass the existing native field schema checks;
- the actor must hold read permission for the output field and every reviewed
  dependency;
- only the output field is read to evaluate visibility.

Unreviewed computations retain the previous recursive scalar-only rule.

| Layer | Entry | Result |
| --- | --- | --- |
| L1 | `make verify.native_advisory.unit` | PASS, 60 tests |
| L1 | `make verify.node_component_validation.unit` | PASS, 246 tests |
| L2/ORM | `make verify.local.dev.conditioned.feedback.orm` | PASS, 26 tests |
| L1 | `make verify.frontend.dev.incremental.unit` | PASS, 131 tests |
| L2 | `make ci.local.iteration` | PASS, 6 executed targets, 0 unmapped, 0 blocked |
| L5 prep | `make ci.delivery.freeze.prepare` | PASS, generated evidence current |

The consolidated receipt is:

```text
.runtime/frontend-dev-validation/executions/20261112T230226Z-2245146-286839489/receipt.json
```

The ORM regression creates its own rollback-only non-customer data space and
operator, then a same-company synthetic project and payroll record. It keeps the
real project-manager payroll record rule active, calls the actual
`UiContractV2Handler`, and asserts that the persisted form now contains one
native feedback host. A first failed run without the project relation was
correctly denied by that record rule; the second run relied on ambient local
registration, so independent review required the final self-contained test-space
setup. A platform test also denies read access to the reviewed relation and
verifies that the result still fails closed with
`FEEDBACK_SOURCE_FORBIDDEN`.

The repo's run evaluator reports these receipts as `stale` because this run
declares `environment.kind=runtime`; that pre-existing evaluator behaviour marks
even check-level offline receipts non-reusable. The original logs are retained,
and `ci.local.iteration` actually re-executed every required target.

Freeze preparation refreshed only the complexity report and split-plan queue for
the two changed verification-tool files; generated-evidence and contract-basis
preflights passed.

## Rollback

Revert the P0 validator and regression-test commit. The implementation and
tests do not change business rows.
