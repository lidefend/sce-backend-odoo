# CI Contract-Only Scope

Status: implemented for owner review

## Purpose

The remote risk planner previously selected managed ORM and backend impact
shards for the `SCENE-CLOSE-02` candidate even though the owner explicitly
limited validation to repository contract logic.

## Controlled scope

`config/ci/contract_only_scopes.json` matches only:

- the exact topic branch;
- the exact base SHA;
- a changed-path set fully contained in an explicit file list.

Wildcards and unknown/outside paths fail closed. A match suppresses ORM
selection, but the registered pure-contract targets still run. The four
required remote checks and professional/static checks remain enabled.

## Boundaries

- This is not a general skip label.
- It cannot exempt unknown paths.
- It cannot turn failed, skipped or zero-test contract targets into success.
- ORM behavior is not claimed as verified; excluded targets remain explicit.

## Verification

- `verify.ci.workflow.contract`: passed.
- `verify.frontend.dev.incremental.unit`: 186 tests passed.
- Explicit classifier probe for the declared branch/base/path set:
  `contract_only_scope` matched, `orm_required=false`,
  `managed_orm_required=false`.
- Registered pure targets execute through `contract_only_checks`. A candidate
  outside the exact path list still selects ORM.
