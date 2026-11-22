# Main Scheduled CI Recovery 2026-11-22

## Identity

- Repository: `lidefend/sce-backend-odoo`
- Base main: `5a42601a75e85da7ec536f515d4a64c795cc3a43`
- Candidate branch: `fix/main-scheduled-ci-recovery-20261122`
- Formal product layer: P4 delivery verification
- Exclusions: no product behavior, contract, ACL, scenario, customer data or database migration changes.

## Observed failure

Scheduled run `44957831997` at obsolete SHA
`4be80e9f65e0c1602a5a0765393f435a41b89105` failed
`verify.test.coverage.registry` because four declared groups were not dispositioned:

- `enterprise_initialization_journey`
- `extension_hook_authority`
- `extension_lifecycle`
- `extension_runtime_context`

The other scheduled failures were downstream or historical:

- `frontend_release_gate` `44958909279` reached payment request 41 and displayed load failure;
  current main already contains PR #955, whose exact-SHA push gates all passed.
- `merge_policy_gate` `44958663413` and `release_candidate_gate` `44958902922`
  consumed that obsolete candidate state and are not current-main evidence.

## Repair

Three extension groups bind to their existing governed ORM selections. The
enterprise initialization group receives an explicit governed target instead
of a `wire-pending` bookkeeping disposition:

```text
make verify.enterprise.initialization.journey.orm
```

The target selects the real `TestEnterpriseInitializationJourney` class through
the registered template-backed `local.test` lane. The generated coverage
inventory is refreshed after the source binding changes.

## Validation and closure

Validation states are recorded in `.agent/runs/MAIN-SCHEDULED-CI-20261122/run.json`.
The repair is complete only after local affected checks pass, the clean candidate
passes all required GitHub gates at its exact head, protected integration is
read back, and fresh scheduled workflows are verified on the resulting main.

Observed local results:

| Check | Result | Original evidence |
| --- | --- | --- |
| `verify.test.coverage.registry` | 19 tests PASS; all declared groups gated or dispositioned | `.runtime/ci-recovery/main-scheduled-coverage-20261122-2.log` |
| `verify.enterprise.initialization.journey.orm` | 1 test PASS; template reused | `.runtime/ci-recovery/main-scheduled-enterprise-initialization-20261122.log` |
| `ci.local.iteration` | PASS; 3 required incremental targets exited zero | `.runtime/ci-recovery/main-scheduled-iteration-20261122.log` |
| `ci.delivery.freeze.prepare` | PASS; generated reports current | `.runtime/ci-recovery/main-scheduled-freeze-prepare-20261122.log` |

The current base main's PR #955 push runs also passed all four required gates on
`5a42601a75e85da7ec536f515d4a64c795cc3a43`. Those results are source evidence for
the old frontend failure only; they are not reused as exact-head evidence for
this repair candidate.
