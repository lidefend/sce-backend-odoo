# VERIFICATION-LANE-ROUTING-20261124

## Identity

- Previous integration base: `8a22a9cc8142d98bbf3813d3e6d85eaa77c58df9`
- Current base after mainline sync: `9365a773d5541ac9fb9923a84536bafb396ba22d`
- Branch: `feature/verification-lane-routing-20261124`
- Formal product layer: P4 verification tooling

## Finding

`audit.verification.lane_coverage.check` is unrelated to demo configuration
data, but all local iteration entries run it unconditionally. The guard scans
10,236 text files and was measured at 5.48 seconds, about 64% of the fixed
local iteration overhead.

## Objective

Route the lane coverage audit by verification-surface impact:

- demo and ordinary product-data changes do not run it;
- Make, workflow, guard registry and verification-lane files do run it;
- unknown paths retain existing fail-closed behavior;
- the audit itself and its policy remain enforced.

No demo data, product contract, Odoo model, ACL, workflow, database or remote
required gate is changed.

## Execution-path audit

| Path | Finding | Resolution |
| --- | --- | --- |
| Fixed local prelude | `audit.verification.lane_coverage.check` ran for every change | Move it behind verification-surface impact selection |
| Planner-selected subcheck | A reusable `verify.verification.lane_coverage` still caused the internal audit check to run again | Add explicit covering-receipt reuse |
| Planner ownership | Planner edits also ran unrelated `verify.agent.resume.unit` (about 7 seconds) | Split planner and run-context path rules |
| `make/ci.mk` local owner | Local iteration ran the full 13-second CI workflow contract, while remote CI still owns that integration check | Route local changes to policy + planner tests; retain full remote workflow contract |
| Backend/frontend channels | Both inherit shared verification/governance targets correctly | No change |
| Demo configuration | Selected only demo lifecycle and scenario-step checks | No lane coverage audit |
| Unknown paths | Remain fail-closed through the existing planner behavior | No change |
| Receipt reuse | Covered subchecks still appeared as unregistered | Exclude reused covered targets from registration-missing output |
| Remote projection | Demo data remains one exact `smart_construction_demo` module integration obligation | No widening; no local remote-suite execution |

## Measurements

- Before: demo-path fixed chain `8.60s`, of which lane coverage was `5.48s`.
- After: demo-path fixed chain `3.07s`; demo tests remain independently timed.
- Before: this P4 candidate's complete local iteration was `32.75s`, including
  duplicate lane audit, unrelated run-context tests and the over-broad local CI
  workflow contract.
- After: `4.89s`. Backend and frontend channel entries measured `5.05s` and
  `4.94s`; only the affected agent ledger target executed in the final pass.

The profiled lane audit scans 10,236 text files and performs about 47,000 regex
passes. It remains fully enforced when the verification surface changes.

## Focused validation

- `verify.frontend.dev.incremental.unit`: 236 tests PASS.
- `verify.baseline.iteration.execution.policy`: 22 tests PASS.
- `verify.agent.resume.unit`: 70 tests PASS.
- `verify.verification.lane_coverage`: 74 tests PASS.

## Documentation sync

The same routing contract is recorded in:

- `iteration_validation_responsibility_v1.md` for local/remote/release duties;
- `dual_lane_fast_iteration_v1.md` for daily operation;
- `validation_delivery_protocol.md` and
  `codex_delivery_collaboration_protocol_v1.md` for protected integration;
- `codex_workspace_execution_rules.md` for the local execution hard lock.
