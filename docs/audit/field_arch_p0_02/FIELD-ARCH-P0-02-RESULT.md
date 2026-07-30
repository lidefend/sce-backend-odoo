# FIELD-ARCH-P0-02 Result

## Decision

`FIELD_ARCH_P0_02_RESULT=PASS`

The product is a new product and has no historical product users. Customer
history is owned by the separate private user-data carrier. The public product
therefore does not retain an optional compatibility add-on: obsolete
`p1_visible_*` and `uc_formal_*` aliases have been removed from product model
registration, views, contracts, search policy, export identity, frontend
formatting and product-side customer-data audit entrypoints.

The upgrade migration removes only obsolete non-stored alias metadata and
views. It does not update business records, remove physical business columns,
or touch the separately scoped `x_custom_field*` work.

## Baseline

- Branch: `fix/field-arch-p0-02-formal-contracts`
- Start SHA: `48e4f359c22f3d6ebdca1b4704a429bd8514712c`
- Start tree: `2b3536f02694d843cc12dd90beb18ba5fc3406ca`
- FIELD-ARCH-P0-01 baseline inventory: 910 runtime aliases
- Resolved formal sources: 747
- Stale runtime aliases: 151
- Unresolved aliases: 12, all unpublished and classified as private audit metadata
- Unclassified unresolved fields: 0

## Product publication result

- Product-source legacy alias declarations: 0
- Formal source view legacy references: 0
- Formal runtime view legacy references on clean install: 0
- Formal contract legacy aliases: 0
- Formal export legacy aliases: 0
- Standard product bootstrap legacy fields: 0
- Product routes with legacy fields: 0
- Product install requires legacy compatibility: false
- Page-specific patches: 0

The 12 aliases without an authoritative product-field source were not guessed
or converted into new product fields. They are unpublished from the product
and documented in `unresolved-field-decisions.csv`; any retained source value
belongs to the private user-data carrier.

## Runtime evidence

An isolated fresh installation of `smart_construction_core` version
`17.0.0.76` reported:

```text
alias_fields=0
alias_views=0
```

The isolated database and Docker resources were task-scoped. No DAILY,
production, `sc_demo`, or port 18093 runtime was read or modified.

## Semantic regression

- Numeric semantics: PASS
- Monetary/currency semantics: PASS
- Sort/filter/group/export semantics: PASS
- Approval and workflow behavior: unchanged
- Product UI historical-alias independence: PASS
- Fresh-install purity: PASS
- Migration metadata-only boundary test: PASS
- Historical customer traceability: responsibility of the private user-data carrier

## Permanent controls

`verify.formal_product_field_purity` fails closed if either obsolete prefix
re-enters:

- public product Python or XML;
- public frontend source;
- product operational scripts.

It also verifies the metadata-only cleanup migration boundary. The existing
list semantic guard now enforces formal product field identity directly rather
than rebuilding an inventory from customer aliases.

## Repository-wide gate note

Change-scoped gates pass. `ci.local.quick` still reports the pre-existing
repository-history debt `RH007`: the earlier commit
`c44b560...` contains an oversized historical audit CSV. This task neither
created that history nor relaxed or bypassed the guard. The generated reports
were refreshed once after the obsolete customer-specific validation assets
were removed.

## Boundaries

- Business record values modified: false
- Physical database columns removed: false
- `x_custom_field*` columns modified: false
- ACL/record rules/workflows modified: false
- 18093 modified: false
- DAILY/production database accessed: false
- Compatibility add-on retained in product: false

## Evidence files

- `formal-contract-migration-matrix.csv`
- `unresolved-field-decisions.csv`
- `view-reference-remediation.csv`
- `new-tenant-bootstrap-evidence.json`
- `runtime-contract-evidence.json`

## Next work

The public product alias cleanup is complete. Any later customer-history
import, reconciliation, or source-value audit must be implemented and tested
inside the private user-data module. The separate `x_custom_field*` physical
column audit remains out of scope and should not be mixed into this change.
