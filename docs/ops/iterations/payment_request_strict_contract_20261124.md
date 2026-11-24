# Payment Request Contract V2 Strict Closure

## Candidate

- Base main: `5b41af7be62846da7378951a00c2c5f8bcbb25e7`
- Branch: `fix/payment-contract-strict-decode-20261124`
- Predecessor P4 merge: PR #992, candidate
  `fc2cb4f8ca659bf644f5f14fdc215f978c6abc0a`

## Root cause

The real `payment.request` form returns a Contract V2 2.6.0 envelope with HTTP
200, but the strict frontend decoder rejects it before rendering:

- 59 form occurrences compare `name/type` while the producer emits canonical
  `fieldCode/fieldType`.
- 18 monetary occurrences lose their descriptor when currency precision cannot
  be resolved.
- P1 product semantics write the non-schema `fieldDescriptor.semantic` key.
- The `attachment_ids` relation lacks the required P1 `attachmentRole`.

## Fix boundary

- P0: align strict descriptor identity and resolve monetary precision from the
  authoritative currency.
- P1: publish declared field semantics through `semanticType` and declare the
  payment-request attachment role.
- Frontend: consume canonical descriptor fields without payment-request
  special-casing or fallback values.

## Guard closure

- The shared Contract V2 assembler cache version is bumped to
  `ui-contract-v2-demand-driven-snapshot-v106` and its input digest is re-bound.
- Contract producer/consumer changes now select the bounded real payment-request
  diagnostic in the exact-head frontend release workflow, without turning the
  ordinary standard lane into the full release matrix.
- The P1 semantic declaration paths now route to
  `verify.semantic.registry.lint`; unknown local paths continue to fail closed.

## Exclusions

- No database, ACL, Record Rule, workflow or deployment change.
- No weakening of Contract V2 strict validation.
- No complete P0-B attachment-fact delivery in this branch.

## Validation

- `verify.p0_contract_producer.p0a.unit`: PASS.
- `verify.frontend.contract_v2_occurrence_authority.unit`: PASS.
- `verify.semantic.registry.lint`: PASS.
- `verify.unified_page_contract.v2.assembler`: PASS after cache identity bump.
- `scripts/ci/test_ci_risk_classifier.py`: PASS, 47 tests.
- `scripts/ci/test_ci_risk_workflow_contract.py`: PASS, 31 tests.
- `make ci.local.iteration`: PASS, 23 required targets.

The captured pre-fix payment contract produced 138 strict decoder issues. The
consumer correction removes the 118 canonical identity/type mismatches; the
remaining 20 producer issues are covered by the monetary-precision, semantic-key
and attachment-role regressions above.

Exact-head remote CI and the real payment-request runtime diagnostic remain
pending publication.
