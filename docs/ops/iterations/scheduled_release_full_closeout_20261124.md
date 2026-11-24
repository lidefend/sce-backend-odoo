# SCHEDULED-RELEASE-FULL-CLOSEOUT-20261124

## Layer and scope

- Formal product layer: P4 verification and release delivery tooling.
- Branch: `fix/scheduled-release-full-closeout-main-20261124`
- Objective: make scheduled release qualification cover every test owned by
  every selected product module and reject evidence from a head that is no
  longer the current remote main.
- Product source, ACL, Record Rules, database, business workflow and deployment
  are excluded.

## Root identity

- Base main: `193d382c61b12e66a2974bada6fb334f5b9d6417`
- Base tree: `eccd8d9111dbb11419e1fd3ad5a1982f85623581`

## Defects closed

1. The backend full lane enumerated all 14 runnable modules but selected only
   `sc_smoke/<module>` and `sc_gate/<module>` inside each ORM module. The latest
   successful scheduled evidence executed 549 tests in
   `smart_construction_core` and 23 in `smart_core`, omitting release-relevant
   methods outside those tags. Full mode now uses `/<module>` for each ORM
   module, which selects the complete test set owned by that module.
2. `release_candidate_gate` validated an exact head and branch name but did not
   prove that head was still current `refs/heads/main`. The assembler now reads
   the authoritative main ref, records it in `sce.release_condition.v1` and
   fails with `STALE_MAIN` when main has advanced.
3. `release_candidate_gate` previously started for every ordinary PR
   open/synchronize event and then completed as a no-op. Its pull-request
   trigger is now the explicit `labeled` event only; ordinary PR lifecycle
   events no longer create the candidate workflow or its skipped child checks.

## Boundaries

- `candidate_build_eligible` remains distinct from deployment authorization.
- `deployment_ready` remains false.
- No historical evidence is relabelled as current.
- The ordinary PR focused lane and explicit changed-test selection are unchanged.

## Local validation

- `verify.ci.scheduled_gates`: PASS.
- `verify.ci.workflow.contract`: PASS, including the executed stale-main negative.
- `verify.test.coverage.registry`: PASS for all 229 declared Odoo groups and
  23 CI unit scripts.
- `verify.test.baseline`: PASS, 379 cases in forward, reverse and fixed-random
  orders with an empty quarantine.
- `make ci.local.iteration`: PASS, 6 affected governance targets executed.

Current receipt:
`.runtime/frontend-dev-validation/executions/20261124T044453Z-517236-370196936/receipt.json`.

Remote exact-head checks and the post-merge scheduled qualification are not yet
run and are not claimed by the local results.
