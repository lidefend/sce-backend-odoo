# Closed PR governance archive and payment audit-copy salvage

Run: `.agent/runs/CLOSED-PR-SALVAGE-20261109/run.json`

## Scope

This batch salvages only the still-valid material from closed pull requests:

- PR #801: restore `ARCH-DECISION-011` as the approved capability-release and
  product-release separation decision.
- PR #802: restore the B0 capability ontology as the upstream definition used by
  the current capability identity specification.
- PR #814: correct the automatic approval chatter copy so an explicitly
  no-approval effective rule is not described as an absent approval policy.

No closed branch is restored wholesale. PR #846 and PR #848 remain superseded,
and the other closed operational or historical candidates remain archived.

## Authority and boundaries

- Formal Product Layer: P0 platform governance documentation and P1 payment
  request audit text.
- The recovered decision retains its recorded owner approval and identifies the
  source PR/head.
- The B0 ontology is a definition baseline, not a capability-release action.
- Contract V2, ACL, approval policy, payment state transitions, frontend
  components and business data remain unchanged.

## Validation policy

Documentation changes use link and ledger checks. The payment audit-copy change
uses a focused automatic-approval backend test and the affected acceptance
evidence classifier. Browser L4 is not applicable because no contract shape,
render model, frontend consumer, permission or runtime state transition changes.

## Results

The current dirty candidate has the following actual results:

| Check | Result | Evidence |
| --- | --- | --- |
| Governance archive links | PASS, 337 links checked, 0 missing | `.runtime/closed-pr-salvage-20261109/docs-links-recorded.log` |
| Acceptance evidence classifier | PASS, 71 tests | `.runtime/frontend-dev-validation/executions/20261109T090536Z-3709075-596433559/verify.acceptance.evolution.binding.log` |
| Agent ledger consistency | PASS, 18 tests | `.runtime/frontend-dev-validation/executions/20261109T090536Z-3709075-596433559/verify.agent.ledger.unit.log` |
| Agent resume mechanics | PASS, 56 tests | `.runtime/frontend-dev-validation/executions/20261109T090536Z-3709075-596433559/verify.agent.resume.unit.log` |
| Contract header/action consumer | PASS, real browser and action-presentation suites | `.runtime/frontend-dev-validation/executions/20261109T090536Z-3709075-596433559/verify.frontend.contract_header_action.unit.log` |
| Frontend incremental planner | PASS, 93 tests | `.runtime/frontend-dev-validation/executions/20261109T090536Z-3709075-596433559/verify.frontend.dev.incremental.unit.log` |
| Automatic approval real path | PASS, 1/1 ORM test | `.runtime/closed-pr-salvage-20261109/payment-auto-approval-copy.log` |
| `ci.local.iteration` | PASS, 5/5 required targets executed | `.runtime/closed-pr-salvage-20261109/ci-local-iteration-recorded.log` |

An initial classifier test failed because its compact fixture represented the
message call without the real `IfExp` shape. The fixture was corrected to the
actual production AST; no classifier rule, product assertion or gate was
weakened.

## Stage status

- Batch validation: passed for the declared dirty candidate.
- Mainline: not integrated.
- PR: not yet created at the time of this record.
- Deployment: not performed.
- L4 browser matrix: not applicable because no contract structure or frontend
  consumer changed.

The run index is authoritative for check receipts and later PR/remote identity.
