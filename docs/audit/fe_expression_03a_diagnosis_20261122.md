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
10. Made One2many monetary footer aggregation fail closed when the participating
    rows do not expose one unique, non-empty currency identity. A mixed currency
    set no longer inherits the first row currency.

### Autosave retention rule

The current 24-hour period is a P1 `smart_construction_core` standard policy
constant, not a user or administrator setting. It is published as
`runtimeContract.intakeAutosave.retention.seconds`; the frontend consumes that
value and has no 24-hour fallback. Tests now cover a 60-second declared policy,
the 60-second boundary, and missing-retention fail-closed behavior.

## Verification result

Source and test candidate:

- HEAD: `9acc0c2c82828ced37b7d771171e5824cd9f9527`
- tree: `2a22c8d412c9f09c1fd728c7a492c1f616d4aa6c`
- `ci.local.iteration`: PASS; 22 required targets resolved, one executed and
  21 content-identical targets reused through the registered local evidence
  authority.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261122T072014Z-2986497-291281420/receipt.json`
- Receipt SHA256:
  `6eca7d46170aa823884c81f78ae97a11e1fbdbb2908be978b9c263e915df6f6f`

Focused outcomes:

- One2many collection semantics: 50 Python guard tests plus the Node semantic
  assertion harness PASS.
- Business semantics: 12 guard tests plus the model assertion harness PASS;
  money, temporal, duration, status and empty-value consumers remain on the
  shared authorities.
- Localized display: PASS with `registered_formatter_allowances=0`.
- Collection row cell: 9 tests PASS.
- Professional detail collection: 23 + 46 tests PASS.
- Professional detail collection model also covers homogeneous currency,
  mixed currency and missing currency for aggregate presentation.
- Intake autosave: 33 cases PASS, including a declared 60-second policy,
  60-second boundary and missing-retention fail-closed case.
- Contract basis: PASS, `open_defects=0`.
- Strict typecheck: PASS.
- Lint: PASS, zero errors; three pre-existing warnings remain.

Exact runtime identity:

- Production frontend build source: `9acc0c2c8`
- Served `build-info.sha`: `9acc0c2c8`
- Runtime source/database: `9acc0c2c8` /
  `sc_frontend_acceptance`
- Authoritative frontend artifact fingerprint:
  `d11035630664d775f81ee7816610a2dea1e6abeb8b132ebcc7dcf1ac11b35a71`
- `/api/runtime-version` returned the same source, database and frontend
  fingerprint.

The browser sample used a one-time probe, not a reusable test framework or a
future acceptance entry. It was bound to the exact build above and read all
record/action/menu identities from the managed
`acceptance.record_identity_resolution.v1` envelope. No database record ID is a
stable input to this batch.

Browser result:

- 8/8 page/viewport cases PASS: project ledger, income contract, payment request
  and My Work at 1440 and 390.
- Every sampled page had exactly one visible H1 and zero document-level
  horizontal overflow.
- The declared payment-request carrier rendered a populated One2many row.
  Desktop readonly values used currency and declared scale (`¥200.00`); mobile
  editable inputs stayed raw two-decimal business values (`200.00`) and did not
  use display decoration as write values.
- Console errors, page errors and persistence intents were all zero. The probe
  did not save or execute any business action.
- Report:
  `.runtime/FE-EXPRESSION-03A/evidence/browser-exact-9acc0c2c8/report.json`
- Report SHA256:
  `10b7124d8ab6c63ff5dd4a3d6f1be568db3985049330d91bd0d9a58c99b59e64`

These one-time browser artifacts are evidence for this candidate only. They are
not a cross-environment replay mechanism; future environments must resolve
their own runtime identity and fixture records through the managed tools.

The read-only sample did not exercise a mixed-currency footer. That case is
covered by the pure model test instead: mixed or missing row currencies produce
no aggregate currency authority, so the footer cell is omitted rather than
mislabeling a sum with the first row currency.
