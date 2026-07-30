# FIELD-ARCH-P0-03 result

```text
FIELD_ARCH_P0_03_RESULT=CONDITIONAL
```

## Baseline and scope

- Start: `a3bff0fb3b4ee02f58b845045436b68434948f67`
- P0-02 commit is the exact start commit.
- `b15535c851354519fdf19b0d3e2c44f1820785c4` is an ancestor.
- Work ran only against the isolated database `sc_field_arch_p0_03_ci`.
- No 18093, DAILY, production or real business database was accessed.
- No old column or business record was changed.

P0-01 runtime evidence was read from its immutable Git commit. Labels were
redacted in the new evidence rather than copying customer/person-like text into
the product branch.

## Inventory

```text
PUBLIC_CUSTOM_PHYSICAL_COLUMNS=11
PUBLIC_CUSTOM_COLUMNS_WITH_SOURCE_DECLARATION=0
PUBLIC_CUSTOM_COLUMNS_WITH_GLOBAL_METADATA=11
PUBLIC_CUSTOM_COLUMNS_WITH_NONEMPTY_VALUES=1
PUBLIC_CUSTOM_COLUMNS_REFERENCED_BY_FORMAL_UI=0
PUBLIC_CUSTOM_COLUMNS_USED_IN_BUSINESS_LOGIC=0
PUBLIC_CUSTOM_COLUMNS_WITH_TENANT_OWNERSHIP=0
UNINVENTORIED_CUSTOM_COLUMNS=0
```

The prior count of 12 `x_custom_field*` metadata entries included one
non-stored registry field on `res.users`; it is not a public physical column.

## Implementation

The product now provides a company-scoped definition model and a typed value
model. It supports char/text, boolean, integer, float, monetary, date, datetime,
selection and controlled many2one semantics. Extensions:

- require a stable, tenant-neutral key;
- cannot override formal product fields;
- require an explicit action/view slot;
- do not register global `ir.model.fields`;
- do not add public business-table columns;
- are projected separately from standard fields;
- repeat record access, company and relation access checks for read/write/export;
- use scoped contract caching and invalidate it on definition mutation.

The former “create custom field” path now creates this tenant definition
instead of a manual global Odoo field and public table column.

## Isolation and type evidence

Eleven isolated Odoo transaction tests pass. They prove:

- company/action/role contract isolation;
- direct model ACL and record-rule isolation for definitions and values;
- standard fields and tenant extension contract slots remain structurally separate;
- active-company value isolation;
- export isolation;
- cache partition and invalidation;
- constant `res_partner` column count and `ir.model.fields` count;
- false vs unset, zero, negative values and precision;
- monetary currency, selection and relation semantics;
- default-dry-run, isolated-only, idempotent migration behavior.
- company cleanup requires retirement, a dry-run preview and an explicit
  platform-admin purge context.

The permanent static guard rejects public `x_custom_field*` declarations,
dynamic global-field creation, missing company/cache dimensions, missing typed
storage, merged standard/extension contracts, and non-dry-run migration tools.

## Migration judgment

```text
CUSTOM_COLUMNS_TOTAL=11
COLUMNS_WITH_CONFIRMED_OWNER=0
COLUMNS_WITH_TARGET_DEFINITION=0
COLUMNS_MIGRATED_IN_ISOLATED_ENVIRONMENT=0
VALUE_RECONCILIATION=PASS_FOR_SYNTHETIC_TYPED_FIXTURE
TYPE_SEMANTICS=PASS
CURRENCY_SEMANTICS=PASS
RELATION_SEMANTICS=PASS
UNRESOLVED_OWNER_DECISIONS=11
DESTRUCTIVE_PRODUCTION_CHANGES=0
```

Ten columns are empty and are candidates for retirement after ownership and
dependency confirmation. `res.partner.x_custom_field` has one non-empty value;
it remains `BLOCKED_UNSAFE_TO_MIGRATE` until a private user-data package proves
its owner and meaning. The product repository contains no mapping for it.

## Final judgment

```text
PRODUCT_FORMAL_FIELDS_STABLE=PASS
TENANT_EXTENSION_STORAGE_READY=PASS
TENANT_EXTENSION_DEFINITION_ISOLATED=PASS
TENANT_EXTENSION_VALUES_ISOLATED=PASS
PRODUCT_SCHEMA_TENANT_INDEPENDENT=PASS_FOR_NEW_EXTENSIONS
SAFE_TO_SCHEDULE_OLD_COLUMN_CLEANUP=BLOCKED_OWNER_DECISIONS
PRODUCTION_FIELD_ARCHITECTURE_READY=CONDITIONAL
```

The carrier and permanent prevention mechanism are ready. P0-03 is
`CONDITIONAL`, not `PASS`, because available evidence cannot legitimately
assign the 11 old columns to a company or give them stable extension identities.
This is the required fail-closed outcome and does not justify keeping dynamic
global fields enabled.

## Recommended next tasks

1. In the private user-data module, confirm or reject ownership and meaning for
   each old column, especially the one non-empty value.
2. Re-run the generic dry-run migration and checksum reconciliation in an
   isolated copy.
3. Only then schedule P0-04 to retire the 11 columns and residual metadata.
4. Keep the existing `c44b560` RH007 debt separate from field architecture.
