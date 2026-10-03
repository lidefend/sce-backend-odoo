# FE-TPL render evidence reconciliation (2026-10-03)

Status: in progress. This record is the human-readable log for run
`FE-TPL-RENDER-EVIDENCE-RECONCILIATION`; the run JSON is the single result index.

## Why this run exists

Run `FE-TPL-OFFICIAL-TEMPLATE-ADOPTION` closed with its code-capability
milestone and merged PR #527, but it left one invariant broken on main.

`docs/frontend_productization/rendering-detail/page-pattern-reference-detail-ledger-v1.json`
states its own completion rule: no `needs_work` item may remain. The ledger on
main still holds four `needs_work` entries:

- `collection.header-actions`
- `collection.toolbar-surface`
- `detail.container`
- `detail.description-grid`

`scripts/verify/page_pattern_reference_ledger_guard.py` therefore fails on main,
and with it the local frontend quick gate
`verify.frontend.page_pattern_reference_parity.unit`.

Bounded scope note: the remote-required check `frontend_release_gate` runs
`verify.frontend.release.audit`, which does not include this guard, so main is
green in CI. The failure is a local governed gate and a broken ledger invariant,
not a red mainline CI.

## Adjudication basis under review

The four entries were reopened by PR #525 on report
`artifacts/frontend-web-fix-20260928/tpl07-1790835439881/report.json` (44
assertions, 2026-10-01). That report has no detail-geometry assertion at all.

A later report, `artifacts/frontend-web-fix-20260928/tpl07-1790874271309/report.json`
(139 assertions, 2026-10-02), asserts
`detail-{light,dark}-{1440,390}: official independent cards and horizontal facts`
through `detailGeometryFailures()` and passes.

Neither report was produced with the current main harness: the browser harness
changed after both (`frontend/apps/web/scripts/standard_page_type_browser.mjs`,
card-body selection narrowed from `.t-card` to the declared
`[data-detail-card="native-section"]` owner), so neither could be reused. All
re-adjudication below therefore uses reports captured on this candidate's own
build.

## Result

Batch acceptance: passed on branch `fix/fe-tpl-render-evidence-reconciliation`
at candidate `99872d500` (clean tree). Mainline integration, deployment and
product delivery are separate statuses and are not claimed here.

## Reconciliation round (2026-10-03, candidate `99872d500`)

The first pass left two acceptance items open: the run scope did not cover two
delivered paths, so `ci.local.iteration` reported `outside_scope`, and the list
lane receipt had been recorded from a run whose contract prerequisite was stale.
Both are closed without touching product behaviour:

- `ci.local.iteration` scope: `.agent/runs/FE-TPL-RENDER-EVIDENCE-RECONCILIATION/run.json`
  now declares the superseded predecessor run record and the refreshed
  complexity budget report. The `checks` block stays declaration-only
  (`target`/`kind`/`inputs`), so recorded results live in the run receipts and
  editing the declaration can no longer invalidate them.
- Governed runtime refresh for this candidate: `make backend.acceptance.replace-stale
  SC_ACCEPTANCE_RUNTIME_PROFILE=local` rebuilt `sc-backend-odoo-acceptance`
  (`SC_SOURCE_REVISION=99872d500`, port 18082, db `sc_frontend_acceptance`),
  `make verify.dev.acceptance.record_identity.resolve COMPOSE_PROJECT_NAME=sc-fe-r2-p1-01`
  re-resolved the fixture record against that revision, and
  `make verify.dev.acceptance.contract ACCEPTANCE_BASE_URL=http://127.0.0.1:5180`
  returned PASS with all eleven declared checks true. The sealed semantic digest
  `640490e029012e43bc1e93b6e3d24881f7c99d8769ba21a684b882bc0506e727` is unchanged
  from the earlier receipt, so the backend behaviour this evidence covers is the
  same one. `frontend.standard.preview.build`/`.up` both reported
  `REUSED unchanged build` / `REUSED current 5180 listener`.
- Recorded identity for the accepted list lane: stable identifier
  `smart_construction_acceptance_fixture.fe_delivery_hardening_payment_request_a`,
  model `payment.request`, record `1849`, companies 8/9, one matching resolved
  target, no competing identifier. The record id is resolved by the governed
  producer, never hard-coded.

Closed root causes in this batch:

- R3 contract seal: `contract_semantic_payload` strips request-transport
  identity (`trace_id`/`request_id`) before sealing, so the sealed digest is
  stable across requests while the delivered payload keeps every field.
- R4 canonical example drift: the four `docs/architecture/unified_page_contract_v2/examples/*.json`
  files still carried the pre-`publishedVersionRef` `schemaSha256`; they now
  match the current v2 schema digest, so
  `verify.frontend.acceptance.environment.guard` is green again.
- R5 replay context: the acceptance declaration and receipt now carry
  `request.context` (lang/tz), so the approved request replays under the same
  language projection and the sealed digest is reproducible.
- 521-760px breakpoint gap (P0 frontend rendering mechanism): the list-surface
  narrow layout is declared at `max-width: 760px`, but the column-settings
  control's icon-only label hiding and 44x44 touch size were declared at
  `max-width: 520px`. At 521px the mobile record presentation is already active
  while the control still carried its desktop label and 36px height, so it
  exceeded the reserved 60px auxiliary track and wrapped onto its own row.
  Both declarations now use the same 760px narrow-layout breakpoint. No
  assertion, audit or negative fixture was relaxed.

Ledger adjudication: all four `needs_work` entries are now `aligned`
(58 aligned / 9 not-applicable / 0 needs-work; guard PASS entries=67
owned_gaps=0).

| Entry | Verdict | Binding evidence |
| --- | --- | --- |
| `collection.header-actions` | aligned | `.runtime/final-acceptance/list-surface-structure.json` 316/316 gated over 1440/1024/768/521/520/390 x normal/batch/empty; negative fixtures 5/5 detected with clean baselines; runtime errors 0 |
| `collection.toolbar-surface` | aligned | same report: one action bar, search inside the single action bar, one column control, `column_settings_standalone`, `desktop_actions_query_aligned`, `empty_clear_semantics_unique`, one direct formatting child |
| `detail.container` | aligned | `artifacts/frontend-web-fix-20260928/tpl07-1791023346277/report.json` (139/139) on this build; run receipt `detail_style_scope` |
| `detail.description-grid` | aligned | same report: `style-detail-{light,dark}-{1440,390}` render 9 readonly-fact sections plus one relation extension each, and the relation lane proves click-open then exact return context in all four theme/viewport combinations |

Run receipts recorded on a clean tree at HEAD `99872d500`
(`.runtime/agent-runs/FE-TPL-RENDER-EVIDENCE-RECONCILIATION/`, raw logs under
`logs/`): `list_surface_structure` 316 (316/316 gated, negative fixtures 5/5
detected with clean baselines, runtime errors 0), `detail_style_scope` 139
(`style-detail-{light,dark}-{1440,390}` each render 9 readonly-fact sections plus
one relation extension, and `detail-{light,dark}-{1440,390}` each prove relation
click-open followed by the exact return context), `page_pattern_parity` 28,
`standard_preview_tool` 147, `primitive_adapter` 39, `collection_action_toolbar`
42. Offline counts sum every runner in the target that prints a case count
(`node --test` and `python unittest`); a target whose node script prints only a
PASS coverage metric is counted by its unittest count. The run declares a
runtime environment, so the local evaluator reports every receipt as `stale`
("runtime evidence requires authoritative environment readback") rather than
`reusable`; they are recorded results, not auto-reusable ones, and were re-run
rather than assumed.

Also recorded: the predecessor run `.agent/runs/FE-TPL-OFFICIAL-TEMPLATE-ADOPTION/run.json`
is `superseded` instead of `completed`, because its goal declared
`overall_goal: incomplete`. That correction changes no commit, product file or
historical evidence.
