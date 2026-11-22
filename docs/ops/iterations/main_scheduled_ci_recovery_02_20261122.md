# Main Scheduled CI Recovery 02

## Identity

- Repository: `lidefend/sce-backend-odoo`
- Base main: `fe635515dda270ed230d07a77ed4bcc9ab4fe5ac`
- Base tree: `f8ea68c2779f6bbcb8a5e6b3e52e9612b2d63561`
- Candidate branch: `fix/main-scheduled-ci-recovery-02-isolated-20261122`
- Worktree: `sce-backend-odoo-ci-recovery-20261120-main-scheduled-ci-recovery-02`
- Formal product layer: P4 delivery verification
- Exclusions: no product behavior, contract, ACL, frontend, customer data, database,
  deployment or runtime changes.

## Defect

`merge_policy_gate` run `44967480032` and `release_candidate_gate` run
`44967480359` were explicitly dispatched for current main
`fe635515dda270ed230d07a77ed4bcc9ab4fe5ac`. Their wait jobs searched producer
workflows with the aggregate run's own `workflow_dispatch` event. The exact-head
producer evidence was produced by the mainline Push event:

| Workflow | Push run | Result |
| --- | --- | --- |
| `public_guard` | `44967245791` | PASS |
| `professional_quality_gate` | `44967245820` | PASS |
| `frontend_release_gate` | `44967245805` | PASS |
| `merge_policy_gate` | `44967245836` | PASS |

The selector consequently returned no run and the unbounded same-event loop
remained pending. The repair preserves strict identity while making producer
event selection explicit.

## Event policy

| Aggregate event | Accepted producer |
| --- | --- |
| `schedule` | Same scheduled slot, exact main SHA, same workflow path |
| `push` | Exact main SHA, same workflow path, mainline Push |
| `pull_request` | Exact PR source branch and head SHA, same repository and path |
| `workflow_dispatch` | Policy-approved reuse of the exact main SHA's successful mainline Push evidence |

The repair does not remove event checks. It also bounds discovery of any missing
required producer and reports the concrete workflow set, exact SHA, aggregate
event, expected producer event and branch before failing.

The first iteration attempt correctly blocked because the new selector path was
not mapped by the incremental planner. That path now routes to the existing
`verify.ci.workflow.contract` and `verify.github_actions.security` owners, with
a regression assertion in `test_frontend_dev_incremental.py`.

## Validation

Results are recorded in `.agent/runs/MAIN-SCHEDULED-CI-RECOVERY-02/run.json`.

| Check | Result |
| --- | --- |
| `verify.ci.workflow.contract` | PASS, 482 tests |
| `verify.ci.scheduled_gates` | PASS, 98 tests |
| `verify.github_actions.security` | PASS, 18 tests |
| `verify.frontend.dev.incremental.unit` | PASS, 207 tests |
| `ci.local.iteration` | PASS |
| `ci.delivery.freeze.prepare` | PASS |
| Live GitHub dispatch selection | Four exact-main Push runs selected |
| Live release condition | `operator_full_audit`, producer event `push` |

The independent worktree required one managed `make fe.install.cached` recovery
before iteration; it restored 639 locked packages offline with zero downloads.
The original worktree retains only the four unrelated concurrent changes and
contains none of this batch's source, run metadata or runtime evidence.

The batch is complete only after the clean candidate's required remote gates
pass. The repair itself does not cancel the two observed runs, trigger
replacement producer workflows or authorize deployment.
