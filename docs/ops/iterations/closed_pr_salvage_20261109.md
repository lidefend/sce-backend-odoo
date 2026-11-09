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
- Integrate the final branch on top of merged PR #850 and rely on its general
  evidence-scope policy instead of retaining a payment-specific classifier.

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
uses a focused automatic-approval backend test. Evidence selection is owned by
merged PR #850. Browser L4 is not applicable because no contract shape, render
model, frontend consumer, permission or runtime state transition changes.

## Results

The rebased candidate has the following actual results:

| Check | Result | Evidence |
| --- | --- | --- |
| Governance archive links | PASS, 337 links checked, 0 missing | `.runtime/closed-pr-salvage-20261109/docs-links-post850.log` |
| Acceptance evidence policy inherited from #850 | PASS, 71 tests | `.runtime/closed-pr-salvage-20261109/acceptance-evolution-post850.log` |
| Agent ledger consistency | PASS, 18 tests | `.runtime/frontend-dev-validation/executions/20261109T092807Z-3872695-244143135/verify.agent.ledger.unit.log` |
| Agent resume mechanics | PASS, 56 tests | `.runtime/frontend-dev-validation/executions/20261109T092807Z-3872695-244143135/verify.agent.resume.unit.log` |
| Contract header/action consumer | PASS, real browser and action-presentation suites | `.runtime/frontend-dev-validation/executions/20261109T092807Z-3872695-244143135/verify.frontend.contract_header_action.unit.log` |
| Frontend incremental planner | PASS, 94 tests | `.runtime/frontend-dev-validation/executions/20261109T092807Z-3872695-244143135/verify.frontend.dev.incremental.unit.log` |
| Automatic approval real path | PASS, 1/1 ORM test | `.runtime/closed-pr-salvage-20261109/payment-auto-approval-copy-post850.log` |
| `ci.local.iteration` | PASS, 4/4 required targets executed | `.runtime/closed-pr-salvage-20261109/ci-local-iteration-post850.log` |

The pre-integration payment-specific evidence classifier was removed after
PR #850 because the general policy now sends ordinary construction backend
changes to `backend_contract` and reserves list/relation runtime suites for
their real consumers.

## Stage status

- Batch validation: passed for the rebased candidate.
- Integration base: merged PR #850 at `346c194e765808727584466d69ab0d2b0605b7b8`.
- Mainline: PR #851 not integrated.
- PR: [#851](https://github.com/lidefend/sce-backend-odoo/pull/851) created.
- PR creation HEAD: `21b4e2f0c9ec7ece153dc7d6d10a464b70628066`.
- Rebased product HEAD before final ledger publication: `1f61ce390b1cd9fdcc7c8139d7fabdcfe93b6be8`.
- Remote CI must be read from the resulting exact PR HEAD, not from either
  earlier head.
- Deployment: not performed.
- L4 browser matrix: not applicable because no contract structure or frontend
  consumer changed.

The run index is authoritative for check receipts and later PR/remote identity.
