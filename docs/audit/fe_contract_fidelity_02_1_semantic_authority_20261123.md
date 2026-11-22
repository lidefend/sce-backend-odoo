# FE-CONTRACT-FIDELITY-02-1

## Unified Business Semantic Authority

Status: completed. Independent review approved; mainline integration completed.

Architecture approval:

- Planning PR: #970
- Approved planning head: `c47eec3c88f52f9e0dd971548b6f888590ce84f8`
- Planning merge / implementation base: `08ce19985aadd7f91b11c42f650b32893638b4c9`
- Authorized batch: FCF-02-1 only

Scope:

- FCF-01 unknown List selection key exposure
- FCF-06 Kanban title fallback without field descriptor
- FCF-07 divergent contract-aware and generic interpreters
- FCF-08 readonly controls dropping componentKey
- CFG-001, CFG-002, CFG-004 and CFG-009 guard coverage

Explicit exclusions:

- FCF-02-2 Readonly Collection and Page Block semantic transport
- FCF-02-3 Progress Summary and My Work invented defaults
- backend contracts, ACL, workflow, ORM commands and persisted values
- visual redesign or local interaction polish

The diagnostic call-chain map, implementation decisions, validation evidence and
remaining limitations are recorded here as the batch progresses.

## Mainline closure

- Reviewed PR: #971
- Reviewed candidate head: `29029ddd339130426b255b55badf1fceacecdd44`
- Required exact-head remote checks: all passed
- Merge commit / new mainline baseline:
  `5f032c1729e37ae7ac4642f51a5018ef3f78b02c`
- Batch acceptance: completed
- Mainline integration: completed
- Deployment and user acceptance: not applicable to this P0 presentation batch

The earlier `verification_pending` state is closed. This result does not claim that
the complete frontend has reached contract-fidelity readiness. FCF-02-2 remains
gated by the separately recorded CFG-GAP-02, CFG-GAP-04 and CFG-GAP-05 probes.

## Review R1 · localized relation labels

The independent review found that `formatDisplayValue()` localized relation
labels while direct readonly consumers called `presentDeclaredBusinessValue()`
without the same transport.

Resolution:

- locale normalization moved from `utils/display.ts` into
  `utils/localizedDisplay.ts`;
- relation tuple and object labels are resolved inside the shared semantic
  authority through `relationLabel(..., locale)`;
- `formatDisplayValue()` no longer pre-localizes relation values;
- `FieldValue`, `ProfessionalBaseFieldControl` and `FormSection` therefore use
  the same relation-label path as the generic adapter;
- raw relation IDs remain the source of record identity and are never replaced
  by a label;
- selection storage keys are not localized or otherwise rewritten.

Browser evidence now covers both `zh_CN` and `en_US` for:

- `[id, localizedLabel]`;
- `{id, display_name: localizedLabel}`;
- actual `FieldValue`;
- actual `ProfessionalBaseFieldControl`;
- actual `FormSection`;
- List and Kanban duration/percentage consumers;
- 1440 and 390 viewports.

## Call-chain diagnosis

| Finding | Confirmed bypass | Resolution |
| --- | --- | --- |
| FCF-07 | `formatDisplayValue()` selected temporal, selection, numeric and relation branches independently of `presentDeclaredBusinessValue()` | Declared fields now delegate to the shared authority; the remaining function without a field descriptor is an explicitly undeclared legacy fallback |
| FCF-08 | `FieldValue.vue` monetary special-case and `ProfessionalBaseFieldControl.vue` generic readonly path discarded `componentKey`, `widget`, `cellRole`, `dataType`, currency metadata and declared digits | Both controls now pass a complete declared field object to the authority |
| FCF-01 | `ListPage.selectionLabel()` returned an empty string for an unknown selection; `presentListCell()` then rendered `String(displayRaw)` | List cells call the authority directly; an unknown declared selection raises `ContractGapError` |
| FCF-06 | `KanbanPage.formatValue()` called `formatDisplayValue(value, undefined)` for the title and fallbacks | Title formatting resolves the declared `columnOptions` descriptor before formatting |

Additional consumers updated for the same boundary:

- `FormSection.vue` monetary and generic readonly branches now delegate to the authority.
- `ContractFormNativeCanvas.vue` passes `componentKey`, `widget` and `currencyField` to `FieldValue`.
- Hierarchy column types preserve declared semantic metadata; their existing
  `formatDisplayValue` calls now delegate through the authority.

## Authority behavior

`presentDeclaredBusinessValue()` now owns:

- status and selection fail-closed behavior;
- monetary, percentage and duration presentation;
- temporal and JSON identity;
- boolean and numeric behavior;
- many2one relation identity and label validation;
- many2many/one2many member identity and label validation.

Bare relation IDs, missing relation labels and unknown selection values fail with
`ContractGapError`. Original relation identity is never replaced by a display
string or raw numeric ID in the shared authority.

`formatDisplayValue()` retains only:

- localization normalization for undeclared text;
- legacy untyped tuple/text handling when no field is supplied;
- attachment-reference presentation;
- internal migration metadata stripping.

It no longer decides selection, relation, status, money, percentage, duration,
numeric precision, boolean, temporal or JSON semantics for a declared field.

## CFG guard implementation

The existing `verify.frontend.business_semantics.unit` lane now enforces:

- `CFG-001`: generic display consumes the shared authority;
- `CFG-002`: List has no selection-label or raw-value fallback;
- `CFG-004`: FieldValue, ProfessionalBaseFieldControl, FormSection and Kanban
  preserve the required descriptor fields;
- `CFG-009`: generic display retains no independent selection, relation, numeric
  or temporal semantic branch.

## Validation

All of the following passed with non-zero execution and are recorded through
`agent.run.record`:

- planning consistency guard: 12 tests;
- business semantics plus CFG guard: 16 tests;
- localized display and field semantics authority;
- professional base field: 16 tests;
- List row cell: 9 tests;
- collection view semantics: 51 tests;
- Kanban record card: 11 tests;
- professional business value: 31 tests and real Chromium authority checks;
- standard collection composition: 222 checks across List and Kanban;
- canonical form presenter: 177 cases;
- Hierarchy command authority: 10 cases;
- professional detail collection: 46 tests plus actual One2many scenarios;
- form runtime state: 80 checks;
- onchange roundtrip: 4 race cases;
- X2Many command semantics;
- frontend lint: 0 errors;
- strict TypeScript: PASS.

Real Chromium evidence covers actual `FieldValue`,
`ProfessionalBaseFieldControl`, `ListPage` and `KanbanPage` components at 1440
and 390. It verifies Chinese selection labels, relation labels, money,
percentage, duration and boolean values, with zero console/page errors and no
document horizontal overflow.

The locale-specific authority run also covers actual `FormSection`; it executes
94 browser assertions across `zh_CN` and `en_US`, both viewports, tuple and
object relation transport. Form and readonly components now produce the same
relation label for the same contract value.

The registered `frontend.standard.preview.build` completed successfully with
5,419 modules. Direct `verify.frontend.build` stops before compilation because
this worktree has no `.env.dev`; no credential file was copied or invented.

## Known limitation and exclusions

- `verify.frontend.onchange_line_patch.guard` fails on the approved main
  baseline because its text marker expects
  `context.onchangeLinePatches.value=linePatches`; the owning implementation is
  unchanged in this batch and was not edited to satisfy a stale marker.
- FCF-02-2 Readonly Collection and Page Block transport was not changed.
- FCF-02-3 Progress Summary and My Work rules were not changed.
- No backend contract, ACL, workflow, persisted value, fixture or database was
  modified.
