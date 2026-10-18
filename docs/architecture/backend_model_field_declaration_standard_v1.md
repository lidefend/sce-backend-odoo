# Backend Model Field Declaration Standard v1

Status: active
Scope: P0 `smart_core`, P1 `smart_construction_core`, P2 product extension modules
Guard: `make verify.backend.model_declaration.guard`
CI: prerequisite of `verify.contract.architecture.suite`

## 1. Why This Is a Standard

Odoo does not treat a second same-name field definition as an override. At registry
setup it merges every class-block definition on the same model **attribute by
attribute**. The surviving field is the union of all declarations:

- the owning class supplies `compute`, `store`, `tracking`, `currency_field`, and the column;
- a later extension may add `string`, `help`, `index`, or `readonly`;
- neither file alone shows the effective field.

That makes a second declaration a hidden second source for one product fact. It is
not a harmless label change, and it cannot be reviewed by reading one file. The
2026-10-18 cleanup found nine such unions in the product backend: one on
`account.move.line.project_id`, one on `construction.contract.amount_untaxed`,
and seven on `sc.labor.usage`. All nine are now consolidated into one declaration
each; the strict guard reports 0 duplicates across 5,774 field declarations.

## 2. Rules

### 2.1 One field, one declaration site

A field name may be declared exactly once per model across all product modules.
This applies to owned models and to models inherited from Odoo/OCA.

Prohibited shapes:

- declaring the same field in the owning class and again in an `_inherit` class;
- declaring the same field in two different `_inherit` classes;
- declaring the same field twice in one class body;
- adding only `string`, `help`, `index`, `readonly`, `tracking`, or `store` in a
  second class to "improve" the first declaration.

Correct shape: put the complete effective declaration at the single owning site.
If the effective field needs a label, help text, index, or readonly change, edit
that one declaration. Do not create a second one.

### 2.2 Inherited core models: extend, do not replace

When extending an Odoo/OCA model (`_inherit` without a new `_name`):

- add new fields and methods; do not re-declare an existing native field;
- preserve the native model as the system of record for identity, access,
  accounting, stock, project lifecycle, chatter, and approval;
- if a native field must be changed, make the change once, with the full effective
  definition, and document why the native semantic is insufficient;
- never copy a native field just to give it a Chinese label. The label belongs to
  the one declaration or to the view/contract layer.

### 2.3 Owned models: the owning class owns the field

For a model with `_name`, the owning class is the only declaration site.
Extension classes may add new fields that do not exist on the model. They may not
re-declare an existing field to attach presentation attributes.

### 2.4 Model layer and family must be declared

Every model class must resolve to a product layer and a business model family:

- P0 `smart_core`: cross-industry platform mechanisms only;
- P1 `smart_construction_core`: construction-industry standard semantics;
- P2 customer modules: confirmed customer preferences and data baselines;
- P3 low-code runtime configuration: editing surface, not a second code authority;
- P4 ops scripts: migration, repair, replay, verification only.

`make verify.backend_business_fact.model_standard` fails when a model is
unclassified, a formal fact is missing its standard fields without a registered
exception, or a registry entry no longer matches source.

### 2.5 Field type and relation must not drift

A consolidation must preserve the effective field type, comodel, relation table,
`compute`, `store`, `related`, `readonly`, and `tracking` semantics. If the
consolidation changes any of them, that is a product change requiring its own
verification, not a cleanup.

## 3. Gates

| Gate | Command | What it proves |
| --- | --- | --- |
| Strict declaration guard | `make verify.backend.model_declaration.guard` | No field is declared by more than one class block; no same-class duplicate. |
| Money-fact source guard | `make verify.fact_source.coverage` | Currency/company facts and duplicate declarations have one declared source. |
| Business fact model standard | `make verify.backend_business_fact.model_standard` | Every model is classified in a family and formal facts meet the standard registry. |
| Backend boundary guard | `make verify.boundary.guard` | Controllers, hooks, and layer imports stay within their responsibility. |
| Industry/product boundary | `make verify.industry_module_product_boundary` | P1/P2 assets, manifests, demo isolation, and module boundaries hold. |
| Database strategy | `make verify.database.strategy.guard verify.platform.database.governance.guard verify.data_space.provisioning.guard` | Platform DB and tenant DB boundaries remain separate and declared. |
| Tenant data boundary | `make verify.tenant.data_responsibility_boundary` and related tenant targets | Tenant data responsibilities, module sets, payloads, and legacy XMLIDs remain isolated. |
| ACL minimum set | `make verify.role.acl.minimum_set.guard` | Required business models keep readable and non-write-without-read ACL rows. |

The strict declaration guard is wired into `verify.contract.architecture.suite`,
which is a prerequisite of both the remote required backend gate
(`ci.professional.backend.shard-verify`) and the local exact-head lane
(`ci.local.quick.run`). A guard cannot pass on only one side.

## 4. No Registration Escape Hatch

Earlier registries in `scripts/verify/fact_source_declarations.json` recorded
duplicate field declarations and `company_id`/`currency_id` overrides as accepted
decisions. That mechanism is retired for product modules:

- duplicate declarations now fail closed and cannot be registered away;
- an extension-class `company_id`/`currency_id` declaration now fails closed;
- the declaration file contains no duplicate or override registry.

The only correct resolution is consolidation into one declaration. If a future
cross-module requirement genuinely needs two declarations, it requires an
architecture decision and a guard change, not a silent registry entry.

## 5. Maintenance Workflow

Before changing a backend model:

1. Identify whether the model is owned (`_name`) or inherited (`_inherit` only).
2. Read the single owning declaration and the effective attributes.
3. Change that declaration, or add a new field with a distinct name.
4. Run `make verify.backend.model_declaration.guard`.
5. Run the affected business fact and boundary gates.
6. Record the exact head and gate results in the run record.

Do not use `help=` or `string=` in a second class as a shortcut. That is the exact
shape this standard exists to prevent.
