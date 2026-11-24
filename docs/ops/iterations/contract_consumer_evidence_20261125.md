# Contract Consumer Evidence and Runtime Routing

## Identity

- Baseline: `0b980ce0ee730f8095374aa1c10c751379fbf367`
- Branch: `fix/contract-consumer-evidence-20261125`
- Run: `.agent/runs/CONTRACT-CONSUMER-EVIDENCE-20261125/run.json`

## Objective

Preserve the original frontend consumer failure context and ensure generic form,
overlay and contract-carrier changes select the runtime checks that can expose
composed failures.

## Boundaries

- P0 generic contract-consumer evidence and shared overlay lifecycle.
- P4 incremental target selection and remote frontend risk routing.
- No industry model, database, fixture, demo-data or deployment change.

## Result

Consumer errors now retain the original error type, lifecycle stage, component
trace and stack while remaining distinct from contract-missing and
contract-mismatch defects. The status surface no longer reports a consumer
`TypeError` as `ContractGapError`.

The remote frontend risk classifier now routes exact generic form, overlay,
relation-carrier and contract-producer paths to the bounded payment-request
runtime diagnostic. An ordinary list page and unrelated template component
remain in the standard frontend lane.

## Verification

- `make verify.p0_contract_producer.p0a.unit`: passed; 51 tests.
- `make verify.frontend.dev.incremental.unit`: passed; 241 tests.
- `make verify.frontend.overlay_lifecycle.unit`: passed; 14 tests and 27 runtime
  lifecycle checks.
- `make verify.ci.workflow.contract`: passed; 517 tests.
- `make verify.frontend.lint.src`: passed with three existing warnings outside
  this batch.
- `make verify.frontend.typecheck.strict`: passed.
- `make verify.frontend.contract_basis.unit`: passed.
- `make verify.frontend.systemic.convergence.static`: passed after replacing an
  unregistered component-name `split` with path-boundary slicing.
- `make verify.frontend.contract_error_business_ownership.unit`: passed; 100
  contract-error cases.

Raw logs are recorded under
`.runtime/agent-runs/CONTRACT-CONSUMER-EVIDENCE-20261125/`.

## Blocker

`make ci.local.iteration` passed the P0 consumer/error-state tests but stopped at
`verify.frontend.delivery_hardening.guard`:

```text
group='smart_construction_core.group_sc_cap_executive_approver'
AssertionError: False != True
```

The mainline commit `a5aff5c2684ef015a9462d836e29d82d970a4971`
(PR #996) grants `group_sc_cap_executive_approver` read access to
`model_payment_request`, while `settlement_views.xml` does not include that group
in the `compliance_state` and `compliance_message` visibility groups. The test
and all implicated files are unchanged by this batch. This is classified as a
P1 product defect and must be corrected on main before this candidate can be
integrated.

Receipt:
`.runtime/frontend-dev-validation/executions/20261124T232151Z-2849506-477208105/receipt.json`

## Next Step

Wait for the mainline PR #996 permission-closure correction, synchronize this
candidate to the new main, rerun the invalidated local checks, then publish the
clean exact-head candidate for remote review and required CI. No database,
deployment or consumer-product semantics are involved in this batch.
