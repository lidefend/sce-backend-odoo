# Contract V2 2.6 Closure

## Identity

- Baseline: `a5aff5c2684ef015a9462d836e29d82d970a4971`
- Branch: `release/daily-main-mode-20261124`
- Run: `.agent/runs/P0-CONTRACT-RUNTIME-2.6-CLOSURE/run.json`

## Scope

This batch closes only the P0 interoperability defects exposed by the real
income-contract list-to-form journey:

- strict field descriptor shape;
- Contract V2 2.6 component version coverage;
- strict occurrence and action identity validation;
- native collection row target identity;
- visible contract decode failure attribution.

No industry model, view, workflow, ACL, fixture or database migration is in
scope. P4 walkthrough tools may observe the result but do not define product
behavior.

## Validation Responsibility

- Local: affected non-zero semantic, contract, component, navigation and
  backend unit targets only.
- Remote: exact-head required PR CI.
- Scheduled release: excluded from this batch.
- Runtime: the declared configuration-admin income-contract list-to-form
  journey on the governed `local.dev` profile.
- Full baseline, Quick and all-entry matrix: not required.

## Confirmed Findings

1. Contract V2 2.6 published a `contextRaw` property inside the strict
   `fieldDescriptor`. Native raw context evidence already exists on
   `fieldInfo` and `nativeIdentity.nativeBehavior`; duplicating it inside the
   descriptor violates the strict schema.
2. The component declaration still capped support at `<2.6.0`, so every field
   component rejected the negotiated 2.6 page contract.
3. The consumer's native occurrence and action-identity guards stopped at 2.5.
   That made 2.6 less strict than 2.5 instead of cumulative.
4. Native collection row-open actions declared a form view but no record-entry
   identity. The frontend compensated by constructing a model/id route itself.
5. Contract V2 decode failures reached the form lifecycle as ordinary errors,
   so the user error surface lost the exact contract issue paths and ownership.
6. The negative-closure walkthrough serialized independent role logins; the
   ten profiles took multiple timeout waves. The tool now uses a bounded
   concurrency of four with identical fail-closed assertions.

The `contextRaw`, component range, occurrence/action guards, row target and
error presentation changes are all P0 platform-contract fixes. No industry
business model was changed.

## Validation

- `verify.semantic.registry.lint`: passed.
- `verify.p0_contract_producer.p0a.unit`: passed.
- `verify.frontend.professional_component_registry.unit`: passed.
- `verify.frontend.contract_v2_occurrence_authority.unit`: passed.
- `verify.frontend.collection_row_action_identity.unit`: passed.
- `verify.node_component_validation.unit`: passed.
- Affected form lifecycle/navigation units: passed.
- Strict frontend typecheck: passed.
- Frontend lint: passed with the three pre-existing warnings outside scope.
- Assembler/schema/action/web-consumer guards: passed.
- `verify.frontend.business_entry.evidence_scope.unit`: passed.
- Real local runtime, final targeted entry:
  `smart_construction_core.menu_sc_p1_income_contract`
  - navigation through the published menu: passed;
  - hierarchical collection ready with 50 rendered rows: passed;
  - first-row detail/form contract and readback: passed;
  - final record: `21`;
  - workflow actions: `activate`, `complete`, `cancel`;
  - console errors: `0`;
  - final route:
    `/f/construction.contract.income/21?menu_id=662&action_id=680`;
  - negative-authority closure: passed after concurrent observation.

The broader `verify.unified_page_contract.v2.web_architecture` guard was also
attempted and failed on an unchanged workflow-statusbar token in
`smart_construction_core/models/support/workflow_contract_service.py`. That
file and the failing guard are not changed by this batch; the generated report
side effect was removed. It remains a pre-existing, outside-scope blocker.
