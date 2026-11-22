# FE-EXPRESSION-03B P1-B Implementation / Batch 2 Diagnosis

## Identity and boundary

- Baseline: `c524ef6af025319e09a71e24db0549b2f903c4b5`
- Branch: `audit/fe-expression-03b-p1b-batch2-20261122`
- Formal Product Layer: P0 generic frontend contract consumption
- Product source modified: yes, limited to list aggregate presentation, transport
  typing and their tests
- Backend contract, ACL, workflow, database and runtime modified: no
- Evidence level: `SOURCE_VERIFIED`, `STATIC_VERIFIED`,
  `AFFECTED_COMPONENT_BROWSER_VERIFIED` and dirty-worktree `BUILD_VERIFIED`
- Full browser business acceptance claimed: no

This batch answers two questions only:

1. Can `ListPage` prove the currency identity of each server aggregate?
2. Are percentage identity and declared numeric precision preserved through
   collection projection and every shared value consumer?

P1-B implementation is included. Batch 2 remains read-only diagnosis for a later
batch.

## P1-B: List aggregate currency identity

### Producer and transport

The backend semantic aggregate currently has this effective response shape:

```json
{
  "visible_amount": {
    "aggregate": "sum",
    "data_type": "monetary",
    "value_field": "amount",
    "aggregation_field": "amount",
    "page_sum": 4790.0,
    "sum": 83272.5,
    "currency_field": "currency_id",
    "currency_id": 1,
    "precision": 2
  }
}
```

For a mixed-currency, missing, unreadable or unverifiable complete aggregate
scope the backend emits an unavailable aggregate:

```json
{
  "visible_amount": {
    "aggregate": "none",
    "data_type": "monetary",
    "currency_field": "currency_id",
    "reason_code": "MULTI_CURRENCY_AGGREGATION_PROHIBITED"
  }
}
```

Source:

- `addons/smart_core/handlers/api_data.py:835-913`
- `sum` is computed over the complete filtered `domain`.
- `page_sum` is computed by adding the current page record ids to that same
  filtered domain.
- Before monetary aggregation, the complete domain is grouped by the declared
  `currency_field`; multiple or unverifiable currency identities prohibit the
  aggregate.
- `grouped_rows[].aggregates` uses the same builder with the complete group
  domain.

The frontend list request adds `currency_field` dependencies before reading the
page:

- `frontend/apps/web/src/app/action_runtime/useActionViewLoadRequestRuntime.ts:102-107`
- `frontend/apps/web/src/app/action_runtime/useActionViewLoadRequestRuntime.ts:165-171`

The successful list result is stored unchanged in `listAggregates`:

- `frontend/apps/web/src/app/action_runtime/useActionViewLoadSuccessRuntime.ts:168-177`

### Consumer path

```text
Contract V2 list semantics
  -> request field_semantics + currency dependency field
  -> api.data list: page records, full-domain sum, page_sum, currency_id
  -> useActionViewLoadSuccessRuntime stores aggregates
  -> ListPage resolveCollectionAggregateEntry
  -> formatFooterNumber
  -> resolveCollectionAggregateCurrencyIdentity
  -> matching relation-id label in the same page/group scope, or fail closed
```

The baseline defect used the first row in `props.records` as the currency-label
authority. That inference has been removed from:

- `frontend/apps/web/src/pages/ListPage.vue:1999-2011`

Flat and grouped footers now pass the aggregate entry and the relevant rendered
scope rows into the shared formatter:

- `frontend/apps/web/src/pages/ListPage.vue:2065-2084`
- `frontend/apps/web/src/pages/ListPage.vue:2093-2132`

### Pre-implementation scenario matrix

| Scenario | Backend result | Current frontend behavior | Verdict |
| --- | --- | --- | --- |
| Same currency on complete flat domain | `sum`, `page_sum`, authoritative `currency_id` | Uses first page row's currency label | Happens to be correct only when the page contains a matching label |
| Mixed currency anywhere in complete domain | `aggregate: none` | No numeric sum, footer omitted | Safe |
| Current page currency differs from full-domain currency | Full-domain check detects multiple currencies and returns `none` | No sum, footer omitted | Safe, but not because frontend proved identity |
| Pagination changes the current page | Backend recomputes full-domain and page-scope values from the same response | Label still comes from the new page's first currency row | Correct only by coincidence |
| Filters change the complete domain | Backend recomputes currency identity over the filtered domain | Label still comes from page records | Correct only by coincidence |
| Numeric aggregate present but `currency_id` absent | Backend may return `sum` without a currency identity if the monetary semantic has no proven currency field/id | Frontend can display the bare number | Fail-open |
| Aggregate has `currency_id`, but no page row carries a matching label | Backend identity is valid | Frontend uses unrelated first page row or no label | Wrong label or unlabeled amount |
| Current page empty | Empty-state branch hides the flat footer | No amount rendered | Safe in the normal empty page |
| Group A and Group B each have one but different currency | Each group carries its own `currency_id` | Parent `props.records` first currency is reused for every group footer | Wrong |
| Group missing currency identity | Group aggregate becomes unavailable | Value is absent and footer omitted | Safe |

### Contract/schema closure

The baseline transport declaration omitted fields already emitted by the backend.
The consumer schema now declares `aggregates` at both list-result level and inside
`grouped_rows`, with the aggregate status, values, currency identity, precision and
reason code:

- `frontend/packages/schema/src/index.ts`
- `frontend/apps/web/src/pages/ListPage.vue`

This closes a consumer schema typing gap without changing the backend contract.

### Other currency inference paths

- Normal monetary cells use the row's declared `currency_field`; that is correct
  for row-level presentation.
- One2many aggregate presentation collects every participating row's currency
  record id and returns no aggregate on missing or mixed identity:
  `frontend/apps/web/src/components/professional-fields/professionalDetailCollectionModel.ts:156-176`.
- My Work consumes a backend-supplied money object and declared digit count.
- Page metric blocks do not currently consume currency identity; that belongs to
  Batch 3.

At the baseline, only `ListPage` applied a first-page-row currency label to a
server aggregate. The implementation removes that path.

### Implemented P1-B contract

The backend algorithm remains unchanged. The frontend now:

1. Add a typed aggregate entry/helper for the existing response fields, including
   `aggregate`, `page_sum`, `sum`, `currency_field`, `currency_id`,
   `digits`/`precision` and `reason_code`.
2. For a monetary footer, require `aggregate === "sum"`, a finite value, and a
   valid positive `currency_id`.
3. Compare that id with the relationship identity in page/group rows. Use the
   matching relation label only. A relation value may be `[id, label]` or an
   object carrying the same id and a non-empty label.
4. Do not infer whole-scope currency equality from page rows. The backend already
   proves that over the full domain or group domain.
5. Hide the aggregate when the id is absent, a matching label is absent, or the
   relation id disagrees. Do not render an unlabeled monetary total.
6. Use the same helper for flat page totals, flat filtered totals and grouped
   page/filtered totals.

Implemented regression coverage:

- same complete-domain currency, flat and grouped;
- mixed currency in the complete domain;
- page and out-of-page currency mismatch;
- monetary sum without `currency_id`;
- matching id with missing label;
- different group currency identities;
- filter and pagination changes;
- non-monetary aggregate unaffected.

The component fixture executes the real `ListPage` through Vite in Chromium. It
covers nine semantic scenarios with 19 checks at 1440 and 390 widths and performs
no backend or external requests.

## Batch 2: Percentage and precision

### F01 - Percentage identity is lost before rendering

Declared identity is already available:

- `contracts/registry/component.yaml:70` registers
  `sc.value.percentage`.
- Native percentage widgets are registered in
  `contracts/registry/semantic.yaml:127`.
- Contract V2 widgets carry `componentKey`.

Current loss points:

- `frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts:278-294`
  retains only `sc.value.duration` and drops
  `sc.value.percentage`.
- `frontend/apps/web/scripts/contract_shape_projection_test.ts:139-164`
  explicitly asserts the current loss.
- `frontend/apps/web/src/pages/listPage/listCellPresentation.ts:72-114`
  invokes the shared presenter only for duration. List percentages therefore
  fall through to numeric formatting.
- Kanban already calls `presentCollectionKanbanCell`, but receives no percentage
  component identity after collection projection.
- `frontend/apps/web/src/pages/contractForm/types.ts:168-190` has no
  `componentKey` on `One2ManyColumn`.
- `frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:946-964`
  sends generic integer/float through `formatNumericFieldValue` before the
  shared presenter.

Observed current interpretations for the same declared value `12.5%`:

| Surface | Current path | Current result |
| --- | --- | --- |
| Professional form | `ProfessionalBusinessValueControl` -> shared percentage formatter | `12.5%` |
| List | component identity dropped -> fixed numeric formatter | `12.50` |
| Kanban | component identity dropped -> shared plain-value fallback | `12.5` |
| One2many | no component identity -> fixed numeric formatter | `12.50` |

Responsibility: frontend consumer. The contract already declares the semantic
identity; no backend business-rule change is needed for F01.

Minimal repair direction:

- preserve declared percentage identity in collection options;
- add the same stable semantic carrier to One2many columns;
- route every typed semantic through the shared presenter before generic numeric
  fallback;
- keep density-specific presentation but not semantic fallback.

### F02 - Float/quantity precision is not fully projected or consumed

Backend declarations exist in the ORM. Examples:

- `addons/smart_construction_core/models/core/general_contract.py:119`:
  `tax_rate = Float(..., digits=(16, 4))`.
- `addons/smart_construction_core/models/core/cost_plan.py:582-595`:
  rates, quantities, unit prices and consumption with scales from 4 to 8.

Projection result:

- `addons/smart_core/utils/native_field_descriptor.py:9-48` projects `digits`
  only when the field type is `monetary`.
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:584-590`
  copies `digits` into list column occurrences only for `monetary`.
- Contract V2 can carry `digits` in widget config, but the producer does not
  expose float digits to complete the chain.

Frontend consumption remains partial:

- `frontend/apps/web/src/components/template/formSection.mapper.ts:109-116`
  maps `digits` only for monetary fields.
- `frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts:147-149`
  accepts `digits` only for monetary fields.
- `frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:94-110` extracts
  digits and currency only for monetary fields.
- `frontend/apps/web/src/utils/fieldSemantics.ts:129-140` formats every
  non-integer float with exactly two fraction digits.
- `frontend/apps/web/src/app/presentation/businessValuePresentation.ts:146-150`
  formats percentages with a fixed maximum of two fraction digits and accepts no
  declared `digits`.

Current surface behavior:

| Surface | Float path | Current precision rule |
| --- | --- | --- |
| Generic form/readonly | `formatDisplayValue` -> `formatNumericFieldValue` | fixed 2 decimals |
| List | `formatNumericCellValue` -> `formatNumericFieldValue` | fixed 2 decimals |
| Kanban | shared presenter plain branch | raw numeric string, no grouping/precision normalization |
| One2many | generic numeric branch -> `formatNumericFieldValue` | fixed 2 decimals |
| Percentage form | shared percentage formatter | maximum 2 decimals |

This is not one frontend constant. F02 spans:

1. P0 native field descriptor projection of float `digits`;
2. Contract V2 field/column projection of those digits;
3. shared numeric and percentage formatting that consumes them;
4. surface adapters that pass them without changing ORM write values.

The next implementation must start with the P0 projection. A frontend-only
guess would violate the contract boundary.

## Shared interpretation authority review

`businessValuePresentation.ts` is not yet the only active interpretation entry.

| Surface | Current authority path | Status |
| --- | --- | --- |
| Professional form business values | `ProfessionalBusinessValueControl` -> shared monetary/percentage/duration/status helpers | Shared, but numeric precision still incomplete |
| Generic form/readonly fields | `FormSection` / `ProfessionalBaseFieldControl` -> `formatDisplayValue` | Secondary interpreter |
| List | duration/status/money partial shared; float/percentage fixed numeric fallback | Mixed |
| Kanban | semantic cells -> `presentCollectionKanbanCell`; title fallback -> `formatDisplayValue` | Mostly shared, secondary title fallback |
| One2many | JSON/relations/local numeric custom; money/time/selection/boolean shared | Mixed |
| Record detail | `FieldValue` special-cases money, otherwise `formatDisplayValue` | Secondary interpreter |
| My Work | money via shared monetary formatter, datetime via shared temporal parser, plain text direct | Partial |
| Page metric blocks | direct `String(value)`; units dropped | Bypass |
| Hierarchy/worksheet | `formatDisplayValue`, with a monetary special case in worksheet | Secondary interpreter |

Important behavioral difference:

- `presentDeclaredBusinessValue` throws `ContractGapError` for an unknown declared
  selection.
- `formatDisplayValue` returns the raw storage key for the same unknown
  selection.
- Generic relation arrays may be interpreted as a tuple and expose the first id,
  while One2many suppresses bare relation ids.

That is F03 and belongs to the later contract-interpreter batch. Existing
`formatDisplayValue` also contains legitimate attachment and JSON handling, so it
must not be removed mechanically before contract-aware consumers are migrated.

The target is one semantic decision model with surface adapters, not one giant
formatting function and not a second Runtime.

## Validation evidence

Baseline diagnosis:

- `python3 addons/smart_core/tests/test_api_data_list_param_boundaries.py`:
  `38/38 PASS`.
- `make verify.frontend.contract_shape_projection.unit`: `14` cases `PASS`.
- `make verify.frontend.business_semantics.unit`: all static/unit families
  `PASS`.

P1-B implementation on dirty candidate
`5a0f9046ea498bc2a192696ff1c51d79fbe08a04` plus the scoped worktree changes:

- `make verify.frontend.collection_aggregate_footer.unit`: `PASS`; `19`
  presentation cases, `19` real-component checks across `9` scenarios and
  `1440/390`, and `12` guard tests.
- `make verify.frontend.collection_view_semantics.unit`: `PASS`; `79`
  collected tests plus the static semantics guard.
- `make verify.frontend.contract_basis.enforce`: `PASS`; `0` open defects.
- `make verify.frontend.lint.src`: `PASS`; `0` errors, `3` pre-existing warnings
  outside the changed files.
- `make verify.frontend.typecheck.strict`: `PASS`.
- `make ci.local.iteration`: `PASS`; ten affected targets executed, including
  the updated aggregate consumer, contract checks and the `210`-test incremental
  planner family.
- `make verify.frontend.dev.incremental.unit`: `PASS`; `210` tests.
- `make verify.frontend.build ENV=dev ENV_FILE=<existing workspace .env.dev> ...`:
  `PASS`; `5419` modules transformed and built in `23.60s`.
- `make ci.delivery.freeze.prepare`: `PASS`; generated evidence refreshed and
  validated before clean commit.

The build was written under `.runtime/FE-EXPRESSION-03B/P1B-BATCH2/dist-build-r2`
with authoritative artifact SHA256
`b9b47e2da3fcacb04b696169e87445f4d705a7de7a64e5ed6d107728aab9b3a7`.
Because the worktree was dirty, this is build validation and explicitly not
frozen-candidate or served-build evidence. The component browser fixture is also
affected-surface evidence, not a full backend business journey.

The first build attempt stopped before compilation because this independent
worktree has no `.env.dev`. That was an environment-input failure, not a product
build failure. The successful retry reused the existing workspace-managed
`.env.dev` read-only through `ENV_FILE`.

The freeze preparation updated only generated inventory, complexity and
component-driver evidence caused by this batch: the new component test entry,
the changed source line counts and the changed component-driver input digest.

## Recommended implementation order

1. P1-B List aggregate currency identity: implemented and verification pending
   independent review.
2. F02 P0 float `digits` projection and contract tests.
3. F01 percentage identity preservation plus List/One2many shared routing.
4. Batch 3 contract-interpreter convergence for F03/F04.
5. P2 timezone, My Work precision, relation identity and page-block value audit.

No Renderer, Registry, Bundle, page engine or second value runtime is justified by
these findings.
