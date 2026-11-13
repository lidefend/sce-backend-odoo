# Delivered entry coverage and project-profile save

Date: 2026-11-13

Branch: `codex/entry-coverage-project-save-20261113`

Baseline: `5cdeb969f7e0181df0d0540e3c7e58eca0649b5d`

## Product result

Use the existing acceptance tools to prove the currently delivered Business Full
entry surface through its final scene/direct routes, and prove one ordinary
project-profile save journey on the isolated `local.dev` carrier.

## Ownership

- Formal Product Layer: P4 operations delivery tooling
- Layer Target: delivered-entry routing, role-scoped coverage and isolated write evidence
- Module: repository acceptance tooling
- Standard vs User-Specific: governed validation tooling
- Why here: product contracts are already delivered; the remaining defects are
  synthetic `/a` routing, one global denominator for every role, and a legacy
  project-profile probe blocked before namespace-aware execution.
- Why not elsewhere: changing product code or CSV labels would hide tooling gaps
  and turn unexecuted entries into apparent coverage.
- Blast Radius: acceptance scripts, their focused tests, coverage declarations and
  generated evidence only. Product runtime semantics, ACLs and business rows are
  excluded.

## Current evidence

- Current main and deployed daily demo revision:
  `5cdeb969f7e0181df0d0540e3c7e58eca0649b5d`.
- Daily runtime carries `demo_full`, company 1, database `sc_demo`, and served frontend
  bundle `b05cd70ef91555155d0383f6a9f9467c280bc1df4fd400a0075045f3dbdc709c`.
- Payroll entry and persisted detail were already accepted under #879; its final route
  remains `/s/entry.smart_construction_core.menu_sc_payroll_management`.
- `workspace.home` is delivered through `role_surface.landing_entry_target`
  `/s/workspace.home`; it is not an action-bearing navigation leaf.
- The refreshed negative-closure input
  `artifacts/frontend-business-entry-matrix/negative_closures-20261113.json` contains
  the Business Full acting identity and 10 eligible daily role identities.
- Scope declaration produced 92 units: 91 action entries plus one no-action scene.
  Business Full released 72 leaves (71 action, one scene).

### Entry reconciliation

The full Business Full incremental run
`.runtime/final-acceptance/entry-coverage-20261113/business-full-r4/summary.json`
executed all 92 declarations:

| Result | Count |
|---|---:|
| Entry navigation passed | 72 |
| Entry not reachable for this acting role | 20 |
| Recognized presentation passed | 70 |
| No recognized presentation (isolated as scene error) | 2 |
| Collection state `ok` | 38 |
| Collection state `empty` | 25 |
| Collection/workspace ready | 7 |
| Detail `ui.contract.v2` read-back passed | 42 |
| Detail skipped because declared empty | 24 |
| Detail not executable on workspace/aggregate | 2 |
| Navigation denial passed | 52 |
| No legal negative identity available | 18 |
| Direct-access denial executed | 0 |
| Business writes executed | 0 |

This run was collected before the final terminal-error detector was added. The
targeted rerun
`.runtime/final-acceptance/entry-coverage-20261113/defect-r3/summary.json`
therefore reclassifies three items with the current detector:

- message notification: `SceneView(data-state=error)`;
- organization department: `SceneView(data-state=error)`;
- project initiation: visible `ProductFormErrorSummary(state=error)`.

Project documents passed the isolated rerun without a reproduced console error. The
earlier full run observed two 403 console entries on that entry; they are retained as
unexplained non-blocking console evidence.

### Role-specific pending entries

`项目预算` is absent from released navigation for all checked applicable identities:
`demo_full` (72 leaves), `sc_demo_business_config` (87 leaves), `demo_cost` (2 leaves),
and `sc_cost_mgr` (2 leaves). The cost-role ledger recorded the entry as
`not_reachable_for_acting_role`.

`菜单配置` is reachable as `sc_demo_business_config`, but the runtime scene route
`/s/entry.smart_construction_core.menu_ui_menu_config_policy_business_config`
activated `core.table` with an empty collection. The CSV declares the dedicated
admin menu-config panel. The entry ledger records the presentation mismatch.

`我的工作` resolves through `/s/my_work.workspace` and reached workspace ready. It has
no legal internal-user navigation denial, so the data-isolation boundary remains
`not_run` rather than being replaced by another internal role.

### Isolated project-profile save

The governed `local.dev` batch `entry-save-20261113` used project record 1053 after
exact-batch reconstruction. The passing run is
`.runtime/final-acceptance/entry-coverage-20261113/browser-r19/summary.json`:

- one real browser save produced exactly one write;
- record identity remained 1053;
- authoritative readback and refresh both returned `initiation_date=2026-11-10`,
  the updated name, description and responsibility relation changes;
- cleanup removed project 1053, carrier 1054, responsibility rows `8,9`, and tag rows
  `7,8,9`;
- post-cleanup inspect returned `existing_batch=false`, no project, no carrier, no tags.

A separate date-range diagnostic found that selecting the end date leaves the visible
end control empty and omits the companion field from the save payload. The final save
uses the declared single date field `initiation_date`; the range-control behavior is
recorded as a product frontend defect below.

## Validation

- `node --check` passed for the modified matrix/tool modules.
- `python3 -m unittest scripts.verify.test_dev_acceptance_release_identity`:
  62 tests passed.
- `python3 -m unittest scripts.verify.test_business_entry_matrix_incremental`:
  41 tests passed.
- `python3 -m unittest scripts.verify.test_local_dev_project_profile_write_fixture`:
  44 tests passed.
- `frontend_probe_toolchain_guard`: passed with 14 tests.
- `make verify.frontend.business_entry.evidence_scope.unit`: passed with 69 tests;
  runtime route suite passed 15 cases and reuse/binding suites passed non-zero cases.
- `make verify.frontend.acceptance.environment.guard`: passed with 62 tests.
- `make ci.local.iteration`: passed with seven affected targets and
  `unmappedPathCount=0`; receipt:
  `.runtime/frontend-dev-validation/executions/20261113T020141Z-3139630-69037117/receipt.json`.
- `make ci.delivery.freeze.prepare`: passed; generated evidence is current.
- The daily role-scoped release probe was `not_run`: the governed daily credential
  confirmation declaration does not include the `daily-release-probe` tool for this
  identity. The role-scoped parser/report semantics are covered by focused tests.

## Findings by responsibility

| Finding | Evidence | Owner / next scope |
|---|---|---|
| Menu configuration opens generic empty table instead of admin panel | config-admin scene route, `core.table`, 0 records | P1 scene publication plus P0 entry-target consumption; inspect route contract before UI change |
| Project budget absent for all four applicable identities | released leaves 72/87/2/2, target absent | P1 navigation publishing / scene composition |
| Notification and department scenes render `SceneView(state=error)` | targeted defect run | P0 scene load error contract and P1 scene configuration |
| Project initiation returns `ONCHANGE_SPEC_INVALID` | API 422 on `api.onchange`; visible error summary | backend onchange specification / P0 contract projection |
| Date-range end selection does not enter draft | end input remains empty after calendar selection | frontend public date-range field consumption |
| 18 project-read entries lack a legal denied-role identity | daily principal closures all contain project read | P4 evidence gap, not a product denial failure |
| Direct-access denial and write surfaces not executed | assertion summary | subsequent targeted security/write journeys |

## Remaining journey gaps

- New record creation, activity-page switching, draft retention and post-create migration
  were not rerun in this batch.
- Contract status progression was not executed.
- The complete payment request chain was not executed.
- Mobile and independent mobile-client acceptance remain separate.

## Rollback

Revert the P4 acceptance-tool commit. The local.dev fixture has already been removed
through `local.dev.project_profile_write_fixture` cleanup; no non-batch business data
was changed. Runtime evidence under `.runtime/` and acceptance closure files under
`artifacts/` are preserved for audit.
