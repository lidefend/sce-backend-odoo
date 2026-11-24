# User Barrierless Closure

## Identity

- Baseline: `f07f65967df5b42eabf9d752ee7a439d91f27a1e`
- Branch: `release/daily-main-mode-20261124`
- Run: `.agent/runs/USER-BARRIERLESS-CLOSURE-20261125/run.json`

## Objective

Continue from the Contract V2 2.6 closure candidate and exercise the released
formal product through the navigation and business surfaces a real user sees.
Repair user-blocking defects only in their owning layer.

## First Finding

The web-contract architecture guard still required the retired industry-module
statusbar projection token. Contract V2 statusbar production already resides in
the P0 `smart_core.workflow.contract` owner and the industry service delegates to
it. This is a P4 validation-tool defect, not a second statusbar authority.

## Confirmed User Blockers

### Native row open was suppressed by row buttons

The native tree parser emitted the default `open_form` row action only when a
tree had no row buttons. A report such as `项目盈亏分析` has four object-method
buttons, so the platform omitted the implicit record-open action. Clicking a row
then had no declared navigation target.

The parser now appends the default open action unless native
`open_form_view="0"` explicitly disables it. The Contract V2 assembler omits it
when the Action has no form View. The frontend selects only declared navigation
actions for row activation; object-method row buttons are no longer mistaken for
row-open actions.

### Empty selection values were reported as invalid enum values

Odoo represents an empty selection as boolean `false`. The list path converted
that native empty value to the string `"false"` and failed closed as if it were
an unknown enum key. This blocked the entire `日常合同` list with
`field.pricing_mode.selection`.

Selection and status presentation now treats native `false` as an empty value,
while an actually unknown truthy key still fails closed.

## Validation-tool Corrections

- The workflow statusbar guard now checks the actual P0 producer.
- Matrix shards default to two workers to match the local Odoo connection pool.
- Denied-role observations use bounded per-shard concurrency.
- A transient dialog left by one entry is dismissed before the next entry; this
  prevents one failed interaction from blocking unrelated navigation.
- `account.menu_action_account_moves_all` declares no detail assertion because
  its native Action publishes tree/pivot/graph/kanban Views and no form View.
- The menu-configuration business entry declares its explicit admin surface.

## Verified User Paths

- `智能工作台`: ready.
- `My Work`: ready.
- `质量中心`: list and record detail passed.
- `施工日志`: list and record detail passed.
- `日常合同`: selection empty values render; record form passed.
- `项目盈亏分析`: default row open is restored; record form passed.
- The 15 previously identified detail blockers were rechecked after the fixes;
  fourteen passed directly. The remaining `日记账项目` item was a false detail
  expectation because its Action has no form View; it now passes with detail
  explicitly not applicable.

The first four-shard full run filled the local Odoo connection pool and produced
secondary 500 responses. Those observations are classified as an environment /
validation-tool defect and were not counted as product failures. Per owner
instruction, already-correct surfaces were not re-walked.

## Exclusions

No database migration, fixture rebuild, demo-data rewrite, mainline integration,
deployment or production change is included.

## Current Status

- Local targeted validation: passed.
  - Entry: `make ci.local.iteration`
  - Result: 24/24 required targets passed across frontend, backend,
    contract and governance layers.
  - Receipt:
    `.runtime/frontend-dev-validation/executions/20261124T202409Z-1765932-879590440/receipt.json`
  - Coverage includes native tree parsing, Contract V2 action/assembler/runtime
    guards, strict frontend typecheck, lint, business semantics, semantic
    registry, P0 contract production and the affected backend unit/ORM checks.
- Already-correct user surfaces: not re-walked, by explicit owner direction.
- The earlier full-matrix attempt did not produce product evidence: it failed
  before opening entries because the served revision
  `a5aff5c2684ef015a9462d836e29d82d970a4971` did not match the requested
  candidate `f07f65967df5b42eabf9d752ee7a439d91f27a1e`. This is recorded as a
  validation/environment identity failure, not a product pass.
- Mainline integration: not started.
- Deployment: the candidate is running only in the governed local development
  environment.
- User acceptance: affected blocker paths passed; the complete 132-entry release
  acceptance is not being rerun while already-correct surfaces are frozen by
  owner instruction.
