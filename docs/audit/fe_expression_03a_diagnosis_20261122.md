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

- HEAD: `ec0ac73f05b9370fdad7bece856b966080f05a5c`
- tree: `82c70fb1e70d3d2a4788ad79208cf9319464aeb9`
- `ci.local.iteration`: PASS; 13 required targets resolved, one executed and
  12 content-identical targets reused through the registered local evidence
  authority.
- Receipt:
  `.runtime/frontend-dev-validation/executions/20261122T074640Z-3130925-157950073/receipt.json`
- Receipt SHA256:
  `9212a6d572fed910a6d820b4f3d3f55e4068f734110d2e816317698f27402a53`

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

- Production frontend build source: `ec0ac73f0`
- Served `build-info.sha`: `ec0ac73f0`
- Runtime source/database: `ec0ac73f0` /
  `sc_frontend_acceptance`
- Authoritative frontend artifact fingerprint:
  `b93c589e3cec3a8c2e015d6deabb0b942b69815bfc99bac5e6953e9912f369e0`
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
  `.runtime/FE-EXPRESSION-03A/evidence/browser-exact-ec0ac73f0/report.json`
- Report SHA256:
  `d6d12cf2d6893a6010b177cd245ba58001909f995ae94bf9f89441852ce3da03`

These one-time browser artifacts are evidence for this candidate only. They are
not a cross-environment replay mechanism; future environments must resolve
their own runtime identity and fixture records through the managed tools.

The read-only sample did not exercise a mixed-currency footer. That case is
covered by the pure model test instead: mixed or missing row currencies produce
no aggregate currency authority, so the footer cell is omitted rather than
mislabeling a sum with the first row currency.
