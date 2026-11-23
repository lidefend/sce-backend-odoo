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
- `make ci.local.iteration`: PASS on the implementation candidate; 10 required
  targets executed, 0 failed or not-run.
- `make verify.test.baseline`: PASS, 366 cases x 3 independent orders, quarantine 0.
- `make local.test.baseline`: PASS, 6 cases x 3 fresh orders.
- Frontend lint: PASS, 0 errors and 3 pre-existing warnings outside scope.
- Strict typecheck and production-mode Vite build: PASS.
- `make ci.delivery.freeze.prepare`: PASS; decision-authority inventory now records
  carrier negotiation `status=current` as protocol state, not business state.

## Finalization

- Exact-head independent review: pending.
- Exact-head remote required checks: pending.
- Merge, deployment and FCF-02-2 remain unauthorized.

## Independent review remediation

Review of `5c3e2da902fb6fe1f458ad8b5eafaed96839c031` requested three P1
corrections. The fixes remain inside the P0-C producer and consumer boundary.

### P1-A · Real action-feedback chain

- `execute_button` is now the reachable producer. Every response carrying a
  contract action ID includes the versioned `runtimePatch.actionFeedback`.
- The same feedback is copied to `error.details.runtimePatch` for denied or
  failed envelopes so the existing intent error path does not discard it.
- `actionId` comes from the declared button identity and `traceId` comes from
  the request/handler trace context. Content hashes are not used as trace
  identity.
- `success`, `denied` and `failed` are classified from the authoritative result,
  including `PERMISSION_DENIED`, `ACTION_NOT_AUTHORIZED` and HTTP 401/403.
- Stable contract reason codes raised by the action-rule authority are retained
  in feedback even when the intent gateway also records the generic
  `PERMISSION_DENIED` transport reason.
- The frontend strictly decodes the feedback, preserves it on `ApiError.details`,
  and `useActionViewActionRuntime` presents the server message through the
  existing batch feedback surface.

### P1-B · Action authorization facts

- P0-C's action verdict now checks the action record's read ACL and record rule
  as well as action groups and target-model read ACL.
- Target model Record Rules remain execution-time authority; the preflight
  carrier does not claim that individual business records were evaluated.
- The ordinary intent permission gate explicitly retains its historical
  group-only action boundary through `include_action_record_acl=False` and
  `include_target_acl=False`. The producer-default verdict owns the fuller
  preflight facts.
- Unit negatives cover unreadable action records, unreadable target models and
  the unchanged ordinary intent boundary.

### P1-C · Rule/carrier semantic reconciliation

- The Page Block decoder now builds one unique `actionId -> ContractV2ActionRule`
  map and rejects duplicate or unmatched identities.
- Each carrier is checked against the referenced rule for `actionRuleRef`,
  `actionKey`, `label`, `intent`, complete `target`, `entitlementEvaluated`,
  authorization, business availability, aggregate permission and final state.
- Target comparison uses a recursive canonical value rather than assumed object
  key order.
- Negative cases cover target, enabled, reason and identity mismatches.

### Remediation verification

- `verify.p0_contract_producer.p0c.unit`: PASS, 14 Python carrier tests, 29
  authorization/action-boundary tests and the P0-C TypeScript/feedback/runtime
  consumer suite.
- `verify.p0_contract_producer.p0c.orm`: PASS, 9 real ORM tests including real
  success, denied and failed action execution with correlated feedback.
- `verify.p0_contract_producer.p0a.unit`: PASS, 42 Python contract tests plus
  the P0-A descriptor and Page Block TypeScript suite.
- `verify.frontend.lint.src`: PASS, 0 errors and 3 pre-existing warnings outside
  this batch.
- `verify.frontend.typecheck.strict`: PASS.
- Production-mode Vite build: PASS with the registered build script and an empty
  non-authority environment file for build-only variables.
- `verify.p0_contract_producer.p0a.browser`: PASS at 1440 and 390; no Console,
  page error or horizontal overflow.
- `make ci.local.iteration`: PASS, 18 affected targets executed with zero failed
  or unexecuted targets.
- `verify.test.baseline`: PASS, 366 cases in three independent orders,
  quarantine 0.
- `local.test.baseline`: PASS, 6 cases across three fresh ORM attempts.

The candidate still awaits a new clean HEAD, exact-head remote checks and
independent review. Merge, deployment, P0-B and FCF-02-2 remain unauthorized.
