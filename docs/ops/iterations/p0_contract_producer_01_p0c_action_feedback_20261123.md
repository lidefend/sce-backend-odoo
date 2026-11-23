# P0-CONTRACT-PRODUCER-01 / P0-C

## Batch identity

- Base main: `122129513fce17e1d6bf3501fbaa13b4a9e74d84`
- Branch: `feature/p0-contract-producer-01-p0c-action-feedback-20261123`
- Result index: `.agent/runs/P0-CONTRACT-PRODUCER-01-P0C/run.json`

## Ownership

- Formal product layer: P0 platform contract runtime.
- Layer target: `page-block-action.v1` declarations and correlated execution feedback.
- Modules: `smart_core`, `smart_construction_core`, `frontend/apps/web`.
- Standard vs user-specific: platform standard.

## Objective

Produce Page Block action facts from existing authoritative structures:

- `ContractV2ActionRule` remains the single action rule identity and target carrier.
- published route authority supplies actor authorization for navigation actions;
- P1 scene builders only reference their generated action keys and native targets;
- visible unavailable actions carry a server reason;
- missing evaluation, missing target and client-supplied authorization identity fail closed;
- action result patches carry `actionId`, status, reason, message and trace identity.

## Exclusions

- No P0-B attachment fact production.
- No FCF-02-2 Page Block renderer consumption.
- No second target schema, registry, runtime, Bundle or authorization engine.
- No ACL, record rule, workflow, database or file-service policy change.
- No deployment and no claim of overall FCF readiness.

## Implementation progress

- Added the strict P0-C action carrier producer.
- Added action-only, data-only and combined capability negotiation.
- Added real action authority resolution through the shared intent permission
  action-group and target-model ACL/rule verdict.
- Added Page Block action/rule projection to workspace and company dashboard contracts.
- Added strict frontend decoding for the action carrier and action contract references.
- Added correlated action feedback to Contract V2 action patches.
- Added pure contract tests, real ORM authority tests and TypeScript decoder tests.

## Validation

- `verify.p0_contract_producer.p0c.unit`: PASS, 12 Python tests and the P0-C TypeScript decoder.
- `verify.p0_contract_producer.p0c.orm`: PASS, 6 real ORM tests.
- `verify.p0_contract_producer.p0a.unit`: PASS, 51 Python tests plus both TypeScript
  suites after adding action-only negotiation coverage.
- P0-A ORM regression: PASS, 10 tests.
- shared P0-A/P0-C browser lane: PASS at 1440 and 390; data-only, action-only,
  combined, legacy and rejection projections all behaved as declared.
- Each browser viewport produced 10 `page-block-action.v1` entries: 9 authorized and
  enabled, 1 authoritatively disabled with `ACTION_NOT_AUTHORIZED`.
- Chrome reported no Console/Page errors and no horizontal overflow.

## Remaining validation

- affected `ci.local.iteration`
- owning-module ORM baseline
- deterministic offline baseline
- lint, strict typecheck and production build
- generated evidence preparation
- exact-head independent review and remote required checks
