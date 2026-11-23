# FE-EXPRESSION-03B Cross-page Semantic Consistency Audit

## Identity and scope

- Baseline: `a408177cde91a6435d5e57a63c50dc35c2e5ce14`
- Formal Product Layer: P0 generic frontend contract consumption
- Layer Target: Form, List, Kanban, One2many, readonly detail, My Work and
  page-block presentation
- Product source modified: no
- Backend contract, ACL, workflow, database and runtime modified: no
- Evidence level: `SOURCE_VERIFIED` plus focused `STATIC_VERIFIED` checks
- Browser acceptance claimed: no

The requested `frontend-convergence-plan-v1.md` is not present in this
repository at the audit baseline. Existing frontend design-system, contract
basis and convergence documents were used instead.

## Executive finding

The shared presentation layer is strong on money, status tone, duration and
primitive temporal parsing, but it is not yet the only active interpretation
path. Two general interpreters remain:

1. `app/presentation/businessValuePresentation.ts`
2. `utils/display.ts::formatDisplayValue`

Most contract-aware collection surfaces consume the first. Several readonly
detail, hierarchy and compatibility surfaces consume the second. Their
selection-failure and relation behavior differ.

There are also four narrower bypasses with direct user impact:

- collection projection discards declared percentage identity;
- float/quantity precision is not consumed end to end;
- page-block metric rendering discards declared units;
- payment settlement introduction converts a missing amount into zero.

### Finding summary

| ID | Priority | Finding | Evidence | Owner |
| --- | --- | --- | --- | --- |
| F01 | P1 | Declared percentage identity is dropped before List, Kanban and One2many rendering | `SOURCE_VERIFIED`, `STATIC_VERIFIED` | Frontend consumer |
| F02 | P1 | Float/quantity precision is hardcoded to two decimals | `SOURCE_VERIFIED` | P0 contract projection + frontend consumer |
| F03 | P1 | Contract-aware and generic value interpreters fail differently | `SOURCE_VERIFIED` | Frontend convergence |
| F04 | P1 | Page-block metric renderer ignores declared `unit` | `SOURCE_VERIFIED` | Frontend page block |
| F05 | P1 | Payment settlement introduction treats missing or zero amounts as another value | `SOURCE_VERIFIED` | Frontend professional component |
| F06 | P1 | List footer uses one row's currency for an all-row aggregate | `SOURCE_VERIFIED` | Frontend collection |
| F07 | P2 | Audit/collaboration timestamps use a local timezone formatter while other dates use shared string parsing | `SOURCE_VERIFIED` | Frontend convergence |
| F08 | P2 | My Work silently defaults or clamps missing money precision | `SOURCE_VERIFIED` | Frontend consumer + contract shape |
| F09 | P2 | Bare relation IDs have inconsistent display/fail-closed behavior | `SOURCE_VERIFIED` | P0 relation projection + frontend |
| F10 | P2 | Page-block tables/records/analysis stringify raw values without field semantics | `SOURCE_VERIFIED` | Frontend page blocks |

No P0 finding was identified in this source-only batch.

## Shared authority graph

```text
Contract V2 field/column metadata
  |
  +-- fieldSemantics.ts
  |     type normalization | empty tests | numeric | compact/full temporal
  |
  +-- collectionStatusPresentation.ts
  |     authoritative status value -> business label + frontend tone
  |
  +-- businessValuePresentation.ts
  |     money | percentage | duration | status | date/datetime |
  |     selection | boolean | plain/empty
  |       |
  |       +-- List duration branch
  |       +-- Kanban
  |       +-- One2many readonly
  |       +-- Professional form business values
  |
  +-- display.ts::formatDisplayValue
        boolean | selection | temporal | numeric | scalar relation |
        arrays | objects | attachments
          |
          +-- FieldValue / native readonly form
          +-- FormSection fallback
          +-- hierarchy browsers/worksheet
          +-- ProfessionalBaseFieldControl
```

This is one dependency family, but not one interpretation authority:
`presentDeclaredBusinessValue` throws for an unknown declared selection,
while `formatDisplayValue` returns the raw storage value.

## Cross-page consumption matrix

| Business semantic | Form | List | Kanban | One2many | Readonly detail / workbench |
| --- | --- | --- | --- | --- | --- |
| Money / currency / precision | Professional control and normal readonly form consume declared digits/currency | Cell money consumes declared digits/currency; footer mixed-currency behavior is unsafe | Shared declared presenter | 03A consumes row currency ID and fails closed on mixed aggregate currency | `FieldValue` consumes currency; My Work uses shared money formatter; page metrics discard units |
| Percentage | Professional form displays `%` | Declared percentage identity is dropped; renders ordinary float | Same identity drop | Float branch renders ordinary number | Project progress blocks use local percent/count formatting; metric rows discard `%` |
| Quantity / float precision | Generic float uses fixed two decimals | Generic float uses fixed two decimals | Generic float uses fixed two decimals | Generic float uses fixed two decimals | Detail generic float uses fixed two decimals |
| Duration / `float_time` | Shared duration presenter | Duration identity is preserved | Duration identity is preserved | Widget is preserved | Activity uses temporal parser; page blocks use local progress/count formatting |
| Status label / tone | Declared status presenter | Status selection label plus central tone; unknown label behavior is not fully fail-closed | Shared presenter fails closed for missing declared selection | Selection presenter retains labels | My Work uses backend label plus central tone |
| Date / datetime | Full readonly presentation | Compact | Compact | Compact | Detail full; audit/collaboration use independent `Intl.DateTimeFormat` |
| Selection / boolean | Mixed: professional paths fail closed, generic detail fallback leaks raw selection values | Selection fallback can expose storage key; boolean labels are shared | Declared selection/boolean presenter | Declared selection/boolean presenter | Generic detail leaks unknown selection; boolean branches are consistent |
| Empty / zero | Shared empty text; monetary input uses empty string | Zero remains zero; missing and false differ | Shared presenter | Shared readonly presenter maps empty to collection empty text | Payment introduction maps missing amount to zero; some blocks stringify `false` |
| Relation fields | Many2one/Many2many controls retain record identity | Many2one tuple label and explicit `__display_values`; bare ID fallback differs | Generic array fallback can expose first ID | Dedicated relation display suppresses bare IDs | `FieldValue` scalar fallback can expose ID; many2many shapes can be misread as one tuple |

Legitimate visual differences retained:

- compact list/Kanban dates versus full readonly form dates;
- money emphasis in the form versus compact table density;
- tags for relation collections versus plain many2one labels;
- badges for status values versus plain text for ordinary selections.

These are presentation differences over the same semantic rule. The findings
below are semantic conflicts, not density differences.

## Detailed findings

### F01 - Percentage identity is dropped after contract decoding

**Priority:** P1

**Declaration:**

- Native views declare percentage semantics:
  - `addons/smart_construction_core/views/core/cost_domain_views.xml:600`
  - `addons/smart_construction_core/views/core/contract_execution_position_views.xml:46-48`
- Contract runtime resolves the percentage widget to `sc.value.percentage`.

**Consumption chain:**

```text
native widget=percentage
  -> Contract V2 widget componentKey=sc.value.percentage
  -> useActionViewContractShapeRuntime.resolveListColumnOptions
  -> only sc.value.duration is retained
  -> List/Kanban receive no percentage identity
```

Evidence:

- `frontend/apps/web/src/app/action_runtime/useActionViewContractShapeRuntime.ts:278-294`
- `frontend/apps/web/scripts/contract_shape_projection_test.ts:139-164`

The test currently asserts this gap:

```text
percentage componentKey -> undefined
Kanban 12.5 -> "12.5"
```

Form uses `ProfessionalBusinessValueControl` and renders `12.5%`. List,
Kanban and One2many render `12.5`.

**Business impact:** A completion, tax, settlement or payment rate loses its
unit after leaving the form. This changes interpretation of the value.

**Ownership:** Frontend collection projection. Preserve the already-declared
component identity; do not add a field-name heuristic.

**Minimal repair:** Pass `sc.value.percentage` through the existing column
option and shared presenter. Add Form/List/Kanban/One2many parity tests.

### F02 - Float precision is fixed at two decimals

**Priority:** P1

Real model declarations include precision-bearing float fields, for example:

- `addons/smart_construction_core/models/core/general_contract.py:119`,
  `tax_rate` with `digits=(16, 4)`;
- `addons/smart_construction_core/models/core/cost_plan.py:582-595`,
  rates, unit consumption and quantities with up to eight decimal places.

Current behavior:

- `frontend/apps/web/src/utils/fieldSemantics.ts:129-140` uses exactly two
  fraction digits for every non-integer type.
- `frontend/apps/web/src/pages/ListPage.vue:1983-1997` passes only the type.
- `frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:946-948` passes
  only the type.
- `addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:584-590`
  copies `digits` only for monetary occurrences.
- `resolveListColumnOptions` normalizes an intermediate `precision` but the
  final column DTO does not expose it.

Counterexample:

```text
1.234567 float -> "1.23"
```

**Business impact:** quantities, tax rates, unit consumption and ratios can
look rounded or indistinguishable when contract precision is needed for
comparison or audit.

**Ownership:** P0 contract projection must expose usable float digits/scale;
frontend formatter must consume them. Frontend must not keep a hidden
precision constant for product fields.

### F03 - Two general interpreters have different fail-closed behavior

**Priority:** P1

Contract-aware path:

- `frontend/apps/web/src/app/presentation/businessValuePresentation.ts:339-350`
  throws `ContractGapError` for an unknown declared selection.

Generic detail path:

- `frontend/apps/web/src/components/FieldValue.vue:41-51`
- `frontend/apps/web/src/utils/display.ts:243-246`
- `formatDisplayValue` returns the raw storage key for a missing selection
  label.

Verified counterexample:

```text
declared presenter: ContractGapError
FieldValue:         "unknown"
List fallback:      "unknown"
Kanban:             ContractGapError
```

Relation behavior also differs:

- generic `[1, 2]` many2many-like input is interpreted as a relation tuple and
  renders `"2"`;
- One2many recognizes only an explicit relation display carrier and returns
  empty for bare IDs.

**Business impact:** the same broken or incomplete contract can fail safely on
one page and expose an internal key or wrong relation element on another.

**Ownership:** Frontend convergence. One contract-aware value projection should
be consumed by FieldValue, FormSection fallback and hierarchy surfaces.

### F04 - Page metric rows ignore declared units

**Priority:** P1

Backend project metrics declare values and units:

- `addons/smart_construction_core/services/project_dashboard_builders/project_metrics_builder.py:67-80`
  emits `元`, `%`, `项`, `份`, `行`, `笔`.

Frontend:

- `frontend/apps/web/src/components/page/blocks/BlockMetricRow.vue:62-75`
  maps only `String(row.value)` and drops `unit`, `value_type`, precision and
  currency identity.

Examples:

```text
1000000 + unit=元 -> "1000000"
12.5 + unit=%    -> "12.5"
0 + unit=元      -> "0"
```

**Business impact:** dashboard users cannot distinguish money, percentage and
count values without relying on labels. This affects business comparison.

**Ownership:** Frontend page-block renderer for already-declared units. Currency
symbol/precision needs a backend value-type declaration if the current `unit`
is insufficient.

### F05 - Payment settlement introduction confuses missing, zero and fallback

**Priority:** P1

Evidence:

- `frontend/apps/web/src/components/professional-fields/PaymentSettlementIntroduceDialog.vue:122`
  uses `req.applied_to_settlement || req.amount`; a legitimate zero falls back
  to the full request amount.
- `:47` hides the settlement total when the value is zero.
- `:272-280` converts `null`, `undefined` or an empty string to
  `Number(value || 0)` before formatting.

**Business impact:** missing can look like zero; zero can look non-zero; a
zero applied amount can display the request amount. These are materially wrong
amount semantics in a payment workflow.

**Ownership:** Frontend professional component. Empty must remain empty and
zero must remain zero.

### F06 - List footer applies one row's currency to an aggregate

**Priority:** P1

Evidence:

- `frontend/apps/web/src/pages/ListPage.vue:1999-2011` resolves the currency
  from the first record that has a currency field, then formats an
  authoritative all-record aggregate with that label.

This is the same class of issue repaired for One2many in FE-EXPRESSION-03A.
The List path still does not prove a unique currency identity for the aggregate
set.

**Business impact:** a mixed-currency list can present an all-row sum under one
row's currency.

**Ownership:** Frontend collection should fail closed when aggregate currency
identity is not proven. The aggregate rule itself may require backend
declaration.

### F07 - Audit and collaboration times use a separate timezone interpretation

**Priority:** P2

Shared temporal fields parse the declared Odoo string in compact or full mode.
Independent formatters instead parse it into browser-local time:

- `frontend/apps/web/src/pages/contractForm/professionalAuditModel.ts:28-35`
- `frontend/apps/web/src/pages/contractForm/professionalCollaborationModel.ts:106-118`
- `frontend/apps/web/src/app/presentation/boqImportPreview.ts:91-96`

Verified counterexample under `Asia/Shanghai`:

```text
shared field formatter: 2026-11-22 08:30
audit formatter:        2026/11/22 16:30
```

**Business impact:** an event can show two different times depending on which
surface renders the same timestamp. The correct timezone rule remains a
contract gap.

**Ownership:** Frontend should converge on the declared temporal policy once
P0 declares timezone handling. Until then this must remain explicitly
unsynchronized, not called complete.

### F08 - My Work locally defaults and clamps money precision

**Priority:** P2

Evidence:

- `frontend/apps/web/src/app/presentation/productMyWorkPresentation.ts:11-26`
  defaults missing digits to `2` and clamps any number to `0..20`.
- `frontend/apps/web/src/api/myWork.ts:110-115` makes `digits` optional.

Current backend payment work-item service supplies digits, so the positive path
is correct. Missing or malformed declaration, however, silently becomes a
frontend-selected precision.

**Ownership:** Contract shape should make money digits required; frontend should
fail closed when absent.

### F09 - Bare relation IDs have no single product-facing policy

**Priority:** P2

Examples:

- One2many suppresses a many2one bare ID:
  `frontend/apps/web/src/pages/contractForm/one2manyUtils.ts:924-932`.
- Generic FieldValue returns the first ID when no display label exists:
  `frontend/apps/web/src/utils/display.ts:253-259`.
- Generic arrays can be misread as one relation tuple:
  `frontend/apps/web/src/utils/display.ts:262-272`.

Current valid reads normally carry display labels, so this is a negative-path
contract/consumer mismatch rather than a demonstrated current-data defect.

**Ownership:** P0 should declare the required relation display carrier;
frontend should reject bare IDs consistently.

### F10 - Page blocks and analysis surfaces stringify raw values

**Priority:** P2

Evidence:

- `frontend/apps/web/src/components/page/blocks/BlockRecordSummary.vue:51-62`
  turns objects into empty text and scalars into `String(value)`.
- `frontend/apps/web/src/components/page/blocks/BlockRecordTable.vue:60-72`
  JSON-stringifies objects and otherwise uses `String(value)`.
- `frontend/apps/web/src/app/contracts/actionViewAnalysisContract.ts:56-64`
  similarly stringifies values without numeric, temporal or relation semantics.

These surfaces lack enough field metadata today. The safe next step is to
declare value kind/unit/currency/relation identity in their carrying contract,
then consume the existing presentation rules.

## Bypass and duplication inventory

| Consumer | Current behavior | Classification |
| --- | --- | --- |
| `ListPage.formatNumericCellValue` / footer | Money is shared; float precision fixed; footer currency from first row | Partial convergence + P1 footer risk |
| `FieldValue` | Money shared; other values use `formatDisplayValue` | Duplicate general interpreter |
| `FormSection.readonlyText` | Money shared; other values use `formatDisplayValue` | Duplicate general interpreter |
| `ProfessionalBaseFieldControl` | Uses `formatDisplayValue` | Compatibility consumer |
| `HierarchyPlanner` / `HierarchyBrowser` | Use `formatDisplayValue` | Compatibility consumer |
| `HierarchicalWorksheet` | Money shared; float local number format; other values generic | Partial convergence |
| `PaymentSettlementIntroduceDialog` | Shared money formatter with local empty/zero coercion | P1 local policy |
| `productMyWorkPresentation` | Shared money/time primitives with local precision fallback | P2 |
| `professionalAuditModel` | Local `Date` + `Intl` | Duplicate temporal interpretation |
| `professionalCollaborationModel` | Local regex + `Date` + `Intl` | Duplicate temporal interpretation |
| `boqImportPreview` | Local number/date formatting | Contract gap + duplicate presentation |
| `BlockMetricRow` | Raw stringification; ignores unit | P1 page block |
| `BlockRecordSummary/Table` | Raw scalar/object stringification | P2 page block |
| `actionViewAnalysisContract` | Raw scalar/relation stringification | P2 analysis |

Unreferenced or thin code:

- `formatDecimalDisplayValue` in `businessValuePresentation.ts` has no
  production consumer at this baseline.
- `professionalBusinessValueModel.formatPercentage` is a thin wrapper around
  the shared percentage formatter; it is not a separate semantic policy.
- `statusBadgeSemantic` is correctly centralised and should remain.

## Legitimate differences to preserve

- Compact list/Kanban dates versus full record dates.
- Readonly record values versus editable input shapes.
- Status badges versus plain selection text.
- Relation tags versus scalar relation labels.
- Money emphasis in a summary versus compact table typography.

These differences change density and interaction, not the underlying value
interpretation.

## Separate contract gaps

These are excluded from FE-EXPRESSION-03B implementation:

| Gap | Current frontend rule | Required owner |
| --- | --- | --- |
| Attachment count has no stable `cellRole/componentKey` | Do not infer attachment behavior | P0 contract declaration |
| Mixed-currency aggregate semantics are not declared | Fail closed | Backend business/contract declaration |
| Float digits/precision are not available consistently to collection and One2many consumers | Current shared numeric display uses two decimals | P0 contract projection |
| Relation display carriers are not uniformly declared as requiring record identity plus label | Current paths differ on bare IDs | P0 relation contract |
| User timezone/display profile is not declared | Shared fields preserve string time; local Intl paths use browser timezone | P0 temporal contract |
| Page-block values have `unit` but not a uniform value type/currency/relation declaration | Renderers stringify raw values | Owning page contract layer |

## Focused verification

Read-only registered checks at the audit baseline:

| Check | Result | What it proves / does not prove |
| --- | --- | --- |
| `verify.frontend.contract_shape_projection.unit` | PASS, 14 cases | Duration identity is consumed; the same test explicitly locks the current percentage omission |
| `verify.frontend.business_semantics.unit` | PASS | Positive shared money/status/time/duration/empty paths remain healthy |
| `verify.frontend.state_dashboard.unit` | PASS | My Work positive presentation and state surfaces remain healthy; missing precision is not covered |
| `verify.frontend.localized_display.unit` | PASS | Existing formatter-authority inventory is green |

Source-counterexample probe:

```json
{
  "declared_unknown_selection": "ContractGapError",
  "field_value_unknown_selection": "unknown",
  "list_unknown_selection": "unknown",
  "kanban_unknown_selection": "ContractGapError",
  "float_precision": "1.23",
  "my_work_missing_digits": "¥50.00",
  "shared_utc_datetime": "2026-11-22 08:30",
  "audit_local_datetime": "2026/11/22 16:30",
  "bare_many2many_ids": "2"
}
```

No browser result is claimed in this phase.

## Recommended minimal implementation order

### Batch A - Collection semantic identity and precision

1. Preserve declared `sc.value.percentage` through the existing collection
   column projection and presenter.
2. Provide declared float digits/precision to List, Kanban and One2many display
   without applying them to ORM write values.
3. Add cross-surface tests for `12.5 -> 12.5%` and
   `1.234567 -> declared precision`.

### Batch B - Empty, zero and relation fail-closed behavior

1. Remove payment introduction `|| 0` and `|| req.amount` coercions.
2. Make generic readonly/form detail use the contract-aware value presenter for
   selection and relation failures.
3. Add missing/zero/negative and bare relation identity counterexamples.

### Batch C - Page blocks and aggregate authority

1. Consume declared metric `unit` and value kind in page blocks.
2. Add mixed-currency fail-closed behavior to List aggregate footers.
3. Declare currency/value-type metadata where `unit` alone is insufficient.

### Batch D - Temporal presentation

1. Declare timezone/display policy.
2. Replace audit/collaboration/BOQ local date interpreters with the declared
   shared temporal profile.

No 03C component consolidation or Renderer expansion should start before these
semantic batches are reviewed.
