# FIELD-ARCH-P0-03R result

## Result

`FIELD_ARCH_P0_03R_RESULT=PASS`

The eleven public `x_custom_field*` columns are not missing product fields.
Seven business-looking labels duplicate existing typed product fields, while
four are test/manual artifacts. No new formal product field is required.

Ten columns are empty and have zero runtime, view, business-logic, external
contract, index, constraint, trigger, installation, upgrade, or recreation
dependencies. The only non-empty column is `res.partner.x_custom_field`,
labelled as test configuration in the immutable audit evidence. Its single
value was preserved in the restricted unresolved-audit carrier during the
isolated rehearsal; it was not assigned to a company and was not published to
product or tenant-extension contracts.

## Baseline

- Branch: `fix/field-arch-p0-03r-legacy-column-provenance`
- Start SHA: `48ccae07aad82b91d8ebb9d6fd779591e900f954`
- Start tree: `1d264067b113e0bd07ee55dcc2bb5193d6d7ffc7`
- P0-03 commit is the direct task baseline.
- P0-02 and `b15535c851354519fdf19b0d3e2c44f1820785c4`
  remain ancestors.
- No push, merge, deployment, DAILY access, production access, or 18093
  modification was performed.

## Product-field decision

| Legacy meaning | Existing formal product identity | Decision |
|---|---|---|
| Contract document date | `construction.contract.date_contract` | Drop redundant empty column |
| Contract amount (Char and Float variants) | `amount_untaxed` / `amount_total` with `currency_id` | Drop both ambiguous/wrong-type empty columns |
| Start date | `construction.contract.date_start` | Drop wrong-type empty column |
| Contractor | `construction.contract.partner_id` | Drop wrong-type empty column |
| Completion date | `construction.contract.date_end` | Drop redundant empty column |
| Project document date | `project.project.initiation_date` | Drop redundant empty column |
| Test configuration | No product meaning | Restricted archive, then drop |
| Person-name-style/test labels | No product meaning | Drop empty test columns |

The old columns are not mapped into ordinary tenant extensions. Promoting them
would create duplicate identities and would regress Monetary, Date, and
Many2one semantics.

## Bootstrap and business-company boundary

- `base.main_company` is explicitly marked as the platform bootstrap company.
- The bootstrap company cannot be registered as a business tenant.
- An ordinary `res.company` is not a tenant until positively registered by the
  tenant/user-data import boundary.
- Tenant extension definitions require an active registration.
- `env.company`, the first company, the only active company, and “not the
  bootstrap company” are not accepted as tenant identity.

Permanent guard results:

```text
BOOTSTRAP_COMPANY_TENANT_REGISTRATION=0
BOOTSTRAP_COMPANY_EXTENSION_DEFINITIONS=0
UNREGISTERED_COMPANY_EXTENSION_DEFINITIONS=0
ENV_COMPANY_IMPLICIT_TENANT_FALLBACK=0
```

## Isolated rehearsal

The rehearsal used only `sc_field_arch_p0_03r_ci` with synthetic values.

1. Recreated all eleven legacy column shapes from immutable evidence.
2. Confirmed ten effective value counts were zero and one synthetic test value
   existed in `res.partner.x_custom_field`.
3. Confirmed all dependency/reference counts were zero.
4. Dropped the ten empty columns.
5. Successfully initialized the registry and upgraded `smart_core` and
   `smart_construction_core`; no column was recreated.
6. Archived the synthetic non-empty value into the restricted unresolved
   carrier and verified its checksum, invisibility, and non-publication.
7. Dropped the final column and repeated registry/module-upgrade validation.
8. Restored all eleven column shapes from `rollback-ddl.sql`.
9. Restored the synthetic value from the verified restricted archive.
10. Reconciled `11` column definitions, `1` non-empty legacy value, and `1`
    restricted archive record.

No real business database or business value was read or changed.

## Gates

```text
FIELD_ARCH_P0_02_REGRESSION=PASS
FIELD_ARCH_P0_03_REGRESSION=PASS
RETIREMENT_READINESS_GATE=PASS (11/11)
UNRESOLVED_VALUE_ISOLATION_GATE=PASS
FRESH_INSTALL_GATE=PASS
EXISTING_TENANT_UPGRADE_GATE=PASS
ODOO_TARGETED_TESTS=PASS (14/14)
RETIREMENT_UNIT_TESTS=PASS (6/6)
TENANT_EXTENSION_GUARD_TESTS=PASS (3/3)
FORM_HANDLER_TESTS=PASS (63/63)
PYTHON_COMPILE=PASS
XML_PARSE=PASS
FRONTEND_LINT=PASS
FRONTEND_STRICT_TYPECHECK=PASS
FRONTEND_PRODUCTION_BUILD=PASS
GIT_DIFF_CHECK=PASS
PERSONAL_DATA_SCAN=PASS
```

Repository-global `ci.local.quick` still stops at the pre-existing RH007
history finding for
`docs/audit/field_arch_p0_01/field-layer-inventory.csv@c44b5602ef97`.
No threshold or exemption was changed. The separately known
`session.ts` line-control debt also remains outside this task.

## Final judgement

```text
TENANT_EXTENSION_ARCHITECTURE_STABLE=PASS
EMPTY_COLUMNS_READY_FOR_P0_04=10
NONEMPTY_COLUMN_DISPOSITION_SAFE=PASS
ALL_OLD_COLUMNS_READY_FOR_DROP=true
SAFE_TO_START_CONTROLLED_CLEANUP=PASS
NEW_FORMAL_PRODUCT_FIELDS_REQUIRED=0
DESTRUCTIVE_REAL_DATABASE_CHANGES=0
PRODUCTION_FIELD_ARCHITECTURE_READY=CONDITIONAL_ON_CONTROLLED_DATABASE_CLEANUP
```

The next database action is mechanical: archive the one test value through the
restricted carrier, verify the same zero-dependency preconditions, drop the
eleven columns in a named controlled database, and run the recorded
registry/upgrade checks. It must not be combined with the separate cleanup of
151 historical metadata/view residues.
