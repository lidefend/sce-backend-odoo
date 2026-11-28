# Frontend contract consumption repair 2026-11-28

## Identity

- Base main: `d79dd2caa58f7e2aa7ab17a88fa80df2fc3e266c`
- Candidate branch: `fix/frontend-contract-consumption-20261128`
- Formal Product Layer: P0
- Scope: `smart_core` contract projection plus generic frontend presentation consumers

## Proven facts

The persisted `sc_dev_demo` environment runs the base main revision. Real
`ui.contract.v2` captures establish the following:

1. `project.profit.compare.gross_margin_rate` is a generic `float` with no
   `digits`. The field descriptor schema permits that shape, but
   `formatNumericFieldValue` treated it as an invalid contract.
2. `payment_execution.date_payment` already declares
   `temporal={kind:date, timezoneAuthority:not_applicable}`. The page assembler
   did not project temporal semantics into hierarchical worksheet columns or
   detail tabs, and the worksheet did not pass them to presentation.
3. Project Kanban declares `listProfile.primary_field=name` and does not publish
   the old nested `kanban_profile.title_field`. The frontend read only the old
   path and stopped.

These are product contract-consumption defects. They are not fixture,
authorization, business-data or initialization deficits.

## Why the previous fixes did not solve the runtime findings

The previous changes are present in main through PR #1019 and were not lost in
a later merge:

- `c46446b93` made missing generic-float `digits` a contract gap. That
  contradicts the already-existing strict field-descriptor rule, which makes
  `digits` optional for generic floats and requires it only for percentage and
  duration. The same change added a source-string guard requiring
  `field.(float).digits`, so the incorrect assumption was enforced rather than
  checked against the schema.
- `ca0f23588` repaired shared business-value temporal formatting, but did not
  include `page_assembler` worksheet projection or
  `HierarchicalWorksheet.vue`. Its tests supplied temporal metadata directly to
  the shared formatter and therefore bypassed the real worksheet producer and
  consumer path.
- `cac72b20b` added fail-closed handling after a Kanban title hint was already
  supplied. It did not update `extractKanbanProfile`, and its test called
  `resolveDeclaredKanbanTitleField('project_title', ...)` directly. The real
  declaration-to-consumer segment therefore remained unverified.
- The PR #1019 run repeatedly records that the 143-entry browser matrix,
  deployment and user acceptance remained `not_run`. Its environment readbacks
  proved build identity, not business-page behavior.

The ineffective result was therefore not caused by missing data, permissions,
or a later regression. It came from three validation-design defects: an
incorrect schema assumption encoded into a passing test, direct-input tests
that skipped the actual producer/consumer path, and absence of the affected
runtime journeys from the acceptance boundary.

The shared business-semantics guard had the same misalignment: it required the
string `field.(float).digits` to exist, so it enforced the incorrect mandatory
precision rule while claiming to protect contract consumption. This batch
replaces that source-string assertion with checks for the optional-vs-invalid
branch, absence of the fixed two-decimal fallback, worksheet temporal/digits
forwarding, and Kanban `listProfile.primary_field` consumption.

The first worksheet producer patch still failed the real page because the
legacy page field map never contained `temporal`; only the strict V2 assembler
added it later. The producer test had supplied `temporal` in its input and
therefore bypassed this missing derivation. Temporal projection now has one
shared P0 helper used by both the page field map and the strict V2 assembler,
and the worksheet test supplies only native field types.

The affected Kanban journey surfaced a separate P4 validation mismatch. The
runtime correctly opened `/s/project.management?project_id=…` from the declared
row scene target, but the matrix matcher required an extra `scene_key` query
that the product route does not publish. The matcher now treats the declared
route as authoritative and requires `scene_key` only when a route is absent.
The product route and query assertions remain exact.

The local impact planner also exposed an ownership gap: the shared temporal
projection file was a production P0 field-semantics input but had no path rule,
so `ci.local.iteration` stopped as unmapped. The field-semantics path family now
selects its cross-page executor and the planner test locks that mapping.

Publication preflight also found the contract-basis ledger still bound Kanban
titles to the superseded nested `kanban_profile.title_field` and temporal
authority to an old inline declaration. The ledger now points to
`listProfile.primary_field` and the shared temporal projection helper.

## Exclusions

- No permission, role, company or data-rule change.
- No fixture or business-data change.
- No acceptance matrix timeout change in this product batch.
- No direct main mutation.

## Verification record

`make ci.local.iteration` passed 42 required targets: 23 test targets with 1030
non-zero tests, 8 static checks and zero unmapped paths. The receipt is
`.runtime/frontend-dev-validation/executions/20261128T114730Z-2855543-81896435/receipt.json`.
Generated complexity and split-plan evidence was refreshed and the read-only
generated-evidence preflight is rerun after every refresh.

The real payment-execution contract now contains `temporal` for both
`date_payment` and `created_time` in worksheet columns and detail tabs. The
captured runtime contract has zero browser console errors.

The four affected worksheet entries (income contract, expense contract, income
settlement and payment execution) passed list, ready-state and detail
assertions in
`artifacts/frontend-business-entry-matrix/local-candidate/frontend-contract-consumption-20261128-r2`.
Profit analysis passed in an isolated run with record 45. Project Kanban passed
in an isolated run by opening the declared `project.management` scene for
project 24.

The six-key focused matrix command still exits nonzero because that subset did
not exercise a released denied-role capability closure. This is recorded as an
uncovered negative-authority check, not as a failure of the six selected
entries.

## Next

Commit this exact candidate, publish it through the governed PR entry, and bind
remote integration checks to the resulting exact head.
