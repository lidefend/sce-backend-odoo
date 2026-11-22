# FE-EXPRESSION-03A Read-Only Diagnosis

## Identity and scope

- Baseline: `d8ce851a7222a07491518749faf9cf7e8f2f53ed`
- Layer: P0 generic frontend contract consumption and business-value presentation
- Module: `frontend/apps/web`
- Evidence level: `SOURCE_VERIFIED`
- Product code modified by this diagnostic: no
- Backend, ACL, workflow, database and customer data: unchanged

## One2many field semantics

| Declared field/value | Current implementation | Current gap | Required shared authority |
| --- | --- | --- | --- |
| `monetary` | `formatDecimalDisplayValue(value, 6, '')` | Drops contract `digits` and `currency_field`; invents six decimal places; no currency | `presentDeclaredBusinessValue()` plus row currency value |
| `date` | `toDateInputValue(value)` | Reuses an edit-input helper as the display path | shared temporal presentation |
| `datetime` | local `Intl.DateTimeFormat('zh-CN', ...)` | A second datetime policy; differs from normal fields | shared temporal presentation |
| `float` with `widget=float_time` | generic six-decimal float display | Declared duration semantics are ignored | shared duration presentation |
| `selection` | selection label, otherwise raw storage key | Unknown values leak into product text | shared selection presentation and fail-closed unknown handling |
| `boolean` | shared true/false text | Semantics are correct but branch remains local | shared declared-value presentation |
| `many2one` | tuple/object display name; bare id is empty | Correct fail-closed relation behavior | retain specialized relation rendering |
| `many2many` | tuple/object names joined by `、`; bare ids are empty | Correct fail-closed relation behavior | retain specialized relation rendering |
| `json` | `formatDisplayValue()` | Distinct readable JSON carrier | retain |
| `integer` | grouped truncation | No current semantic conflict; keep until a shared numeric rule is required | existing numeric formatter |
| empty | branch-specific empty strings | Empty handling is duplicated across branches | shared declared-value empty result |

### Discovery path

1. Odoo tree parser writes `field_type`, `currency_field` and `digits` into
   `tree.column_occurrences`
   (`addons/smart_core/app_config_engine/services/view_Parser/parsers Tree Form.py:563-590`).
2. Contract V2 carries that subview through
   `frontend/apps/web/src/pages/contractForm/canonicalFormRenderer.ts:84`.
3. `useRecordRelationshipFields.ts:122-132` selects the subview and builds
   `One2ManyColumn`.
4. `one2manyUtils.ts:one2manyColumnsFromSubview()` does not copy `digits` or
   `currency_field`, and `One2ManyColumn` does not declare them.
5. `one2manyColumnDisplayValue()` therefore cannot honor the backend declaration.

The display metadata exists upstream. This is a frontend consumption gap, not a
missing backend contract for One2many amounts.

## Edit/display bypass

`one2manyColumnDisplayValue()` currently feeds both:

- readonly table/mobile display; and
- `One2ManyCellEditor.vue` editable `model-value`.

The repository has already registered this as a known exception in
`scripts/verify/frontend_localized_display_contract_test.ts:289-295`.
Display formatting must be split from input formatting:

- display: grouped, contract-aware money/date/time/duration;
- input: native mutation shape with no display-only decoration.

This split is presentation-only. `normalizeOne2manyColumnValue()`,
`dirtyFields`, onchange, row identity, save commands and ORM write values remain
unchanged.

## Public authority reuse

The existing shared authorities are sufficient:

- `presentDeclaredBusinessValue()` for money, date, datetime, duration,
  selection, boolean and empty values;
- `resolveCurrencyDisplayLabel()` for a declared currency field value;
- `normalizeMonetaryDigits()` for `[precision, scale]`;
- `formatMonetaryInputValue()` for editable monetary input;
- `formatNumericFieldValue()` for generic integer/float presentation.

No new registry, renderer or business-value runtime is required.

## Attachment count audit

The unsafe path is:

- `ListPage.vue:795-799` requires the visible label to equal `附件` and the
  rendered value to match `附件(n)`;
- `ListPage.vue:856-859` turns that textual coincidence into an executable
  attachment-preview cell;
- `previewRecordAttachmentCount()` opens the existing authorized attachment
  viewer using the current record identity.

This is label/text inference, not contract identity.

### Contract evidence

- List contracts support `cell_role`, but the backend allow-list currently
  contains `money`, `status`, `relation`, `identity`, `date`, `description`,
  `actions`, `favorite` and `text`; it has no attachment-count role
  (`addons/smart_core/handlers/ui_contract_v2.py:3317-3336`).
- Current generated contract snapshots contain no attachment `cell_role` or
  attachment value component.
- `attachment_count` appears in native structures as an ordinary `integer`;
  the attachment display copies are `char` fields containing localizable
  `附件(n)` text.
- The semantic registry has no platform attachment-count value component.

### Backend declaration gap

The backend must declare attachment-count behavior, for example a P0
`cell_role=attachment-count` or an equivalent `componentKey`, and publish it in
`columns_schema`. Until that exists, the frontend cannot identify an attachment
count without guessing from field name, localized label or text format.

03A will remove the current label/text heuristic. It will not add model-name,
field-name or Chinese-label compensation. A future contract role can be wired
to the existing `CollectionRowCell` attachment action without a second runtime.

## Implemented convergence

1. Extended One2many/relation column metadata with declared `digits` and
   `currencyField` only.
2. Projected those fields from `column_occurrences`.
3. Resolved row `currencyLabel` from the declared currency dependency.
4. Used `presentDeclaredBusinessValue()` for readonly money, date, datetime,
   duration, selection, boolean and empty presentation.
5. Introduced a separate input-value projection for editable cells.
6. Kept many2one/many2many record identity and JSON handling specialized.
7. Removed the registered local-format exception after the split.
8. Deleted Chinese-label/count-text attachment inference and recorded the backend
   semantic gap.
9. Updated the cross-page business-semantics authority audit so its completion
   ledger no longer reports the resolved One2many formatter bypass as open.

### Autosave retention rule

The current 24-hour period is a P1 `smart_construction_core` standard policy
constant, not a user or administrator setting. It is published as
`runtimeContract.intakeAutosave.retention.seconds`; the frontend consumes that
value and has no 24-hour fallback. Tests now cover a 60-second declared policy,
the 60-second boundary, and missing-retention fail-closed behavior.

## Validation plan

- One2many money: digits, currency, empty, zero and negative values.
- Date/datetime/float_time: compact display and edit values.
- Selection, boolean, many2one and many2many boundaries.
- Editable input differs from readonly display while persisted values remain raw.
- Attachment behavior is independent of Chinese/English labels and ordinary
  integer columns.
- `verify.frontend.collection_view_semantics.unit`
- `verify.frontend.business_semantics.unit`
- `verify.frontend.localized_display.unit`
- `verify.frontend.collection_row_cell.unit`
- `verify.frontend.professional_detail_collection.unit`
- lint, strict typecheck, production build and affected browser journeys.
