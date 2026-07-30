# Tenant extension architecture

## Decision

The governed carrier is:

```text
ui.tenant.extension.field
  (database + company + model + stable extension key + explicit page slot)
        ↓
ui.tenant.extension.value
  (definition + business record + typed value + schema version)
```

Extensions are not `ir.model.fields`, do not create columns on product business
tables, and are not merged into the standard product field directory. A page
receives them only through the separate `tenant_extension_fields` contract
slot after database, active company, user groups, model, action/view, extension
schema version, and product contract version have been resolved.

## Options considered

| Option | Type safety | Isolation/discovery | Schema growth | Search/index | Decision |
|---|---|---|---|---|---|
| Add columns to business tables | Native | Global definition leak | Per customer field | Native | Rejected |
| Dynamic `ir.model.fields` | Native | Global registry leak in a shared DB | Registry/schema growth | Native | Rejected |
| Untyped JSON strings | Poor | Can be scoped | Constant | Weak/ambiguous | Rejected |
| Pure typed EAV | Strong | Strong | Constant | Shared typed indexes | Viable |
| One extension table per tenant/model | Strong | Strong | Table proliferation | Native-ish | Rejected |
| Definition + typed value carrier | Strong | Strong | Constant product schema | Shared controlled indexes | Selected |

The selected carrier explicitly distinguishes unset, false, zero and negative
values. Monetary values retain a currency strategy; selections validate stable
keys; references retain model identity and repeat ORM access and company checks.

## Growth and lifecycle

```text
TENANT_EXTENSION_STORAGE_MODEL=COMPANY_SCOPED_DEFINITION_PLUS_TYPED_VALUE_TABLE
SCHEMA_GROWTH_MODEL=CONSTANT
METADATA_GROWTH_MODEL=LINEAR_IN_CARRIER_ROWS_NOT_IR_MODEL_FIELDS
INDEX_GROWTH_MODEL=CONSTANT_SHARED_TYPED_INDEX_SET
VIEW_GROWTH_MODEL=CONSTANT
CACHE_GROWTH_MODEL=BOUNDED_SCOPED_KEYS
MULTI_TENANT_SCALE_ASSESSMENT=PASS
```

Definition and value rows can grow linearly with actual tenant usage; public
business columns, product model fields, standard views and registry models do
not. Definition mutations invalidate the contract cache. Reads remain cached
and partitioned by database, company, user/group projection, model, page scope,
extension schema version and product contract version.

Active or retired definitions cannot be silently deleted. Company deletion and
field retirement therefore require an explicit archive/audit flow before
physical cleanup; this is intentional protection against losing historical
extension values.

## Migration boundary

The product repository contains only:

- the neutral carrier;
- typed validation and access services;
- a default-dry-run plan validator;
- an idempotent, isolated-context ORM migration service;
- synthetic fixtures and guards.

Customer ownership maps, old-column meanings and real values belong to a
private user-data package. The 11 known columns have no proven owner in the
available evidence. Ten are empty; one has one non-empty value. No owner,
extension key or business meaning is guessed, and no old column is dropped.

## Rollback

For an isolated migration:

1. validate the private plan in dry-run mode;
2. create a company-scoped definition in draft state;
3. validate typed rows and their SHA-256 reconciliation digest;
4. execute only with `tenant_extension_isolated_migration=True`;
5. compare row counts and digest;
6. activate the definition and its explicit page slot;
7. on failure, roll back the transaction or retire the draft definition;
8. keep the old column untouched until a separate cleanup task proves zero
   dependencies and a complete rollback rehearsal.

No rollback step writes product formal fields or deletes old columns.
