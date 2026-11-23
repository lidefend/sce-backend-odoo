# P0-C-FIX-01 · Real action identity chain

## Batch identity

- Base main: `8b46984d2b896eb104c26348788883993d260beb`
- Branch: `feature/p0-c-fix-01-action-id-chain-20261123`
- Result index: `.agent/runs/P0-C-FIX-01-ACTION-ID-CHAIN/run.json`

## Ownership

- Formal product layer: P0 platform contract runtime.
- Layer target: canonical ContractV2ActionRule identity through the real Action
  View `execute_button` request and feedback response.
- Modules: `smart_core`, `frontend/apps/web`.
- Standard vs user-specific: platform standard.

## Objective

Close the remaining P0-C identity gap:

```text
ContractV2ActionRule
  -> Action View contract action
  -> runContractAction
  -> buildContractActionButtonRequest
  -> executeButton
  -> ExecuteButtonHandler canonical current-rule validation
  -> feedback using the validated actionId and real traceId
```

The backend must not echo an unvalidated client actionId. Missing or mismatched
contract identity fails closed.

## Exclusions

- No ACL, Record Rule or workflow change.
- No database, migration or fixture change.
- No Action Target Schema change.
- No P0-A, P0-B, FCF-02-2 or FCF-02-3 work.
- No deployment.

## Acceptance

- Frontend request-builder output includes canonical `action_id`,
  `backend_identity`, `source_widget_id`, button name and button type.
- Real Odoo success, denied and failed paths correlate feedback to the current
  rule's canonical actionId and the request trace.
- Missing actionId, actionId mismatch, backendIdentity mismatch and button
  mismatch fail closed.
- Existing Action View and execute_button behavior does not regress.

## Implementation

- `normalizeV2ActionRows()` carries the current ContractV2ActionRule's
  `actionId`, `backendIdentity` and `sourceWidgetId` into the Action View
  contract-action projection.
- `actionViewContractActionRuntime.buildContractActionButtonRequest()` requires
  the complete identity and emits:

  ```text
  button.name
  button.type
  button.action_id
  button.backend_identity
  button.source_widget_id
  ```

- Missing contract identity raises a `ContractGapError` before
  `execute_button` is called.
- `ExecuteButtonHandler` resets its validated identity per request, matches the
  current action rule by canonical actionId plus backendIdentity, validates
  sourceWidgetId and button name/type, then records the rule's canonical
  `actionId`.
- Feedback is generated only from that revalidated identity. Missing or
  mismatched identity produces the existing fail-closed execution error without
  a fabricated `runtimePatch.actionFeedback`.
- The frontend request fixture consumed by the ORM tests is asserted equal to
  the output of the real Action View request builder.

## Verification

- `verify.p0_c_fix01.action_id.unit`: PASS. The real frontend projection and
  request builder chain emits the complete identity and blocks a missing
  canonical actionId before backend execution.
- `verify.p0_c_fix01.action_id.orm`: PASS, 15 real ORM tests. The exact frontend
  builder fixture is received by `ExecuteButtonHandler`; success, denied and
  failed actions preserve the canonical actionId and request traceId.
- Negative ORM cases cover missing actionId, actionId mismatch,
  backendIdentity mismatch, sourceWidgetId mismatch and button mismatch; none
  fabricates feedback.
- `verify.p0_contract_producer.p0c.unit`: PASS, 14 carrier tests, 29
  authorization/action-boundary tests and TypeScript regression suite.
- `verify.execute_button.authority.unit`: PASS, 37 tests.
- `verify.action_view_runtime_smoke.behavior`: PASS.
- `verify.frontend.lint.src`: PASS, 0 errors and 3 pre-existing warnings outside
  this batch.
- `verify.frontend.typecheck.strict`: PASS.
- Production-mode Vite build: PASS.
- `verify.test.baseline`: PASS, 366 cases in three independent orders,
  quarantine 0.
- `local.test.baseline`: PASS, 6 cases across three fresh ORM attempts.
- `make ci.local.iteration`: PASS, 23 affected targets with zero failed or
  unexecuted targets.

One initial ORM attempt failed because the test inspected the wrong
`BaseIntentHandler.params` envelope shape (`params.params` instead of `params`).
It was classified as a validation-tool defect; the assertion was corrected and
the same real ORM suite then passed. No product behavior was weakened.

The candidate remains unmerged, undeployed and awaiting independent review.
