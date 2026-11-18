# Workflow Contract Interface V1

## 1. Scope

This design governs the existing `workflowContract` carrier used by the V2 page
contract. It does not introduce a second root contract or a new workflow engine.

The first implementation scope is:

- `smart_construction_core.menu_sc_user_payment_apply`
- `smart_construction_core.menu_sc_product_project_lifecycle_v1`

## 2. Two Forms Of One Carrier

`workflowContract` has exactly one of two forms.

### Create action catalog

The create form publishes action meaning only:

- model and declared action identities;
- `availabilityScope=declaration_only`;
- no `record_id`, record target or execution grant;
- no `availableActions`.

The catalog answers what commands exist for this object. It never answers what
the current user may execute on a record.

### Persisted record contract

The saved record contract publishes:

- `record_id`, state field and raw state;
- authorized and business-specific `availableActions`;
- one stable action identity per current command;
- disabled reasons when an authorized action is blocked by business facts;
- normalized `businessPhase` and independent `approvalPhase` summaries.

Every record action must reference an action in the same contract's declared
`actions` catalog. A record target must identify the same model and record.

## 3. Action Identity

`key` is the business command identity. `method` is the execution target. They do
not need to be equal.

For every action:

- `key` is unique within its catalog;
- label is presentation only and never identifies an executor;
- a business/transition/approval action has a non-empty `method`;
- `target.method` equals `method`;
- `method`, `intent`, `kind` and declared action semantics agree;
- a `save` action may use `method=null` and remains on the normal form save path.

The payment command `done -> action_done` is one identity. All payment evidence
gates and action references must use `done`; other models may continue to use
their own `complete` identity.

## 4. State Presentation

The primary statusbar is the model's real business state:

- payment request: `state`;
- project lifecycle: `lifecycle_state`.

`statusbar.field`, `statusbar.current` and `statusbar.states` must be derived
from that same model field and its selection. `businessPhase` may normalize the
state for visual semantics, but it does not replace the primary state.
`approvalPhase` is a separate approval summary.

A virtual phase is never a writable form field. Business progression occurs only
through declared actions. State ordering is presentation, not evidence that a
record has traversed every prior state.

## 5. Availability And Execution

Availability is a read snapshot. Real execution revalidates the same business
facts.

The contract producer and the model action call one model-owned read-only
blocker function. The workflow service projects those blockers; it does not copy
business rules and never detects availability by executing an action and rolling
it back.

Action disposition rules:

- unauthorized: omitted under the existing authorization projection;
- explicitly outside the entry/object scope: omitted with source evidence;
- authorized but blocked by business state or facts: visible, disabled, with a
  stable reason code and readable message;
- domain/rule evaluation error: contract-production defect, never treated as
  authorization denial;
- non-blocking warning: may coexist with an enabled action and does not itself
  disable the action.

## 6. Reason And Severity Vocabulary

The producer, schema and frontend decoder use one vocabulary.

- enabled action: `reason_code=OK`, empty `blocked_message`;
- disabled action: non-empty stable `reason_code` and `blocked_message`;
- evidence gate severity: `block`, `warn` or `info`.

## 7. Final API Handoff

Handoff evidence must traverse the actual authenticated request, production
service and V2 assembler to the final response.

For each applicable entry publish:

- create catalog;
- actionable persisted record;
- business-blocked persisted record;
- post-action response and record-contract readback for an executed action.

Each sample binds backend SHA, runtime version, database/profile, acting role and
company, menu/action/view identity and real record identity. Hand-authored JSON
is limited to schema negative tests and is never joint-acceptance evidence.

## 8. Acceptance

1. create catalogs do not grant record execution;
2. action catalog, record actions, gates and targets reconcile by identity;
3. availability and execution share model-owned business checks;
4. the primary statusbar has one model field source;
5. denied actions explain why and successful actions read back the new state and
   next action set.
