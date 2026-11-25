# P0 Contract Descriptor Conformance

## Scope

- Formal product layer: P0 platform kernel product.
- Layer target: strict field descriptor production and Contract V2 decoding.
- Module: `smart_core`, with a P0 producer regression test carried by
  `smart_construction_core`.
- Exclusions: no P1 project view change, frontend fallback, fixture reset,
  database migration, deployment or production-data change.

## Confirmed defect

The project ledger list contract is correct and its row action contains a
complete `record_entry`. Opening record `4` requests the correct form contract,
but the frontend stops with:

`FIELD_DESCRIPTOR_CONDITIONAL_REQUIRED` for
`layoutContract.field.date_start.occ.d0045fc59594374c.fieldDescriptor`.

The emitted descriptor combines:

- native field fact: `fieldType=date`;
- native expression: `widgetType=daterange`,
  `options.end_date_field=date`, `always_range=1`;
- incorrect contract semantic: `semanticType=readable_value`,
  `componentKey=sc.display.text`;
- correct temporal enhancement: `temporal.kind=date`.

## Boundary

Native expression is preserved as occurrence facts:

- `widget=daterange`;
- raw options, required modifier and native locator;
- `widgetType=daterange`.

Contract meaning is platform normalization:

- a `date` model field has `semanticType=date`;
- it resolves to `sc.input.date`;
- it declares date semantics with `temporal.kind=date` and
  `timezoneAuthority=not_applicable`;
- field-type semantics that are structurally fixed by Contract V2 cannot be
  replaced by an unrecognized native widget token.

We do not mount or execute embedded Odoo components. The P0 bridge consumes
only the parsed semantic facts:

- field widgets enter `fieldDescriptor` with a platform `componentKey`;
- embedded `<widget>` nodes enter node contracts with a platform node
  component and declared support state;
- native token names remain provenance/expression evidence;
- payload providers may supply contract data by occurrence identity, but they
  never supply ACL, field-read or component authority.

## Why the previous closeout was incomplete

The previous strict-descriptor chain added monetary precision and aligned date
decoding, but its real-contract decoder evidence covered only the project list.
The failing occurrence exists only on the project form. The focused tests also
did not cover a canonical `date` field carrying an explicit native
`daterange` token. Therefore both the producer bug and its consumer failure
remained outside the tested slice.

## Required mechanism

1. Route both field widgets and embedded `<widget>` nodes through one P0
   contract bridge.
2. Preserve native expression separately from semantic derivation.
3. Derive semantics from declared semantic rules first, native widget rules
   second only when they are explicit, and canonical field type when the native
   token is only a presentation variant.
4. Force fixed Contract V2 semantics for temporal and other identity-critical
   field types.
5. Exercise the project form, not only the project list, with the production
   frontend decoder.
6. Keep row `record_entry` assertions so a form-contract pass cannot hide a
   broken navigation declaration.

## Verification

- `make verify.p0_contract_producer.p0a.descriptor_conformance`: PASS.
  The isolated ORM fixture produced the real project ledger form contract and
  the production TypeScript decoder accepted all 45 strict descriptors.
- `date_start` remains `widgetType=daterange`, while contract meaning is
  `semanticType=date`, `componentKey=sc.input.date`, and
  `temporal.kind=date`.
- `make verify.p0_contract_producer.p0a.backend_unit`: PASS, including the
  native field-widget matrix and the embedded `<widget>` node bridge.
- `make verify.p0_contract_producer.p0a.unit`: PASS.
- `make verify.semantic.registry.lint`: PASS.
- `make ci.local.iteration`: PASS, 19 required targets with the form contract
  decoder included.

The first fixture attempts exposed two fixture-only mistakes: the collector
did not traverse `widgetList`, and `op=model` used a different projection from
the product's `action_open` form entry. The fixture was corrected to consume
the actual product contract tree and entry path.

`make verify.docs.all` reached the documentation link/temp checks successfully
but its bundled identity-architecture audit rejects any dirty product source;
that historical clean-tree assertion is not evidence about this candidate and
is not counted as a product failure.
