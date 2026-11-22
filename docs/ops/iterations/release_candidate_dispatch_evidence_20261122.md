# Release Candidate Dispatch Evidence 2026-11-22

## Identity

- Repository: `lidefend/sce-backend-odoo`
- Base main: `9b0d16f21b0fe3316c3640dada48a7eb307ff499`
- Base tree: `dc033f27a54020d9938520ea0d636803d48cb378`
- Candidate branch: `fix/release-candidate-dispatch-evidence-20261122`
- Formal product layer: P4 delivery verification

## Observed defect

PR #957 correctly stopped the aggregate waiters from searching for impossible
`workflow_dispatch` producers when only Push evidence existed. However, the
same reuse policy was applied to `release_candidate_gate`.

On main `9b0d16f2`, five scheduled workflows were manually dispatched together:

- `public_guard` `44978479983`
- `professional_quality_gate` `44978482928`
- `frontend_release_gate` `44978485463`
- `merge_policy_gate` `44978490232`
- `release_candidate_gate` `44978493634`

`release_candidate_gate` passed while the newly dispatched professional and
frontend full runs were still in progress because the selector had consumed
the earlier Push runs on the same SHA. That is sufficient for merge eligibility
but not for an `operator_full_audit` release condition.

## Corrected policy

| Aggregate workflow | `workflow_dispatch` producer |
| --- | --- |
| `merge_policy_gate` | Exact-SHA mainline Push evidence |
| `release_candidate_gate` | Exact-SHA `workflow_dispatch` full-audit producers |

The release gate must wait for the manually triggered `public_guard`,
`professional_quality_gate`, `frontend_release_gate` and `merge_policy_gate`
runs on the same SHA. Missing manual producers remain visible through the
bounded missing-dependency summary and do not silently fall back to Push.

## Validation

| Check | Result |
| --- | --- |
| `verify.ci.workflow.contract` | PASS, 484 tests |
| `verify.ci.scheduled_gates` | PASS, 98 tests |
| `verify.github_actions.security` | PASS, 18 tests |
| `verify.frontend.dev.incremental.unit` | PASS, 207 tests |
| `ci.local.iteration` | PASS |
| `ci.delivery.freeze.prepare` | PASS |

## Boundary

- No product, contract, permission, frontend, database or deployment changes.
- Current in-flight manual runs are not cancelled.
- No automatic dependency dispatch is introduced.
