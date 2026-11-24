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
- The industry semantic is present, but its Descriptor componentKey remains the
  platform `sc.relation.table`; the frontend registry omits industry field types
  from its descriptor applicability map.

Monetary assembly also must not synthesize precision. The descriptor uses the
Odoo field's native `get_currency_field()` result and the current record's real
currency. If that currency fact is absent, the descriptor keeps the currency
binding but omits `digits`; no company-currency fallback is inserted by the
assembler.

## Fix boundary

- P0: align strict descriptor identity and resolve monetary precision from the
  authoritative currency.
- P1: publish declared field semantics through `semanticType` and declare the
  payment-request attachment role; publish the matching industry componentKey.
- Generated semantic carriers: expose declared field types for both platform and
  industry components without importing an industry renderer into the platform.
- Native embedded components are excluded from this batch and remain a separate
  future investigation.
- Frontend: consume canonical descriptor fields without payment-request
  special-casing or fallback values.

## Guard closure

- The shared Contract V2 assembler cache version is bumped to
  `ui-contract-v2-demand-driven-snapshot-v108` and its input digest is re-bound.
- Contract producer/consumer changes now select the bounded real payment-request
  diagnostic in the exact-head frontend release workflow, without turning the
  ordinary standard lane into the full release matrix.
- That diagnostic has its own `contract_diagnostic` frontend mode. It records
  its own outcome and frozen-resource cleanup instead of masquerading as
  `standard`; ordinary standard unit/build work is not implicitly attached.
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
- `make ci.local.iteration`: PASS, 25 required targets in the latest complete pass.

The captured pre-fix payment contract produced 138 strict decoder issues. The
consumer correction removes the 118 canonical identity/type mismatches; the
remaining 20 producer issues are covered by the monetary-precision, semantic-key
and attachment-role regressions above. A second exact-head browser run reduced
the contract to one industry-semantic mismatch, which is closed by publishing
and validating the declared industry component identity and field-type table.

Exact-head remote CI and the real payment-request runtime diagnostic remain
pending publication.
