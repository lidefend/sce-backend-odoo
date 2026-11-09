# Contract V2 Action Semantics v1

## 1. Purpose

This standard separates four independent questions:

1. Is the action exposed to the current actor?
2. Is the actor authorized to execute it?
3. Does the current business state permit progress?
4. Is the action temporarily busy or already executing?

Contract V2 remains the authority. No parallel permission, eligibility or action
registry is introduced.

## 2. Field semantics

| Field | Meaning | Owner |
| --- | --- | --- |
| `visible` | The action is part of the current actor's product surface | Contract projection |
| `authorizationAllowed` | The actor has the execution right | Contract producer / P0 projection |
| `businessAvailable` | The current document/business state permits progress | Contract producer |
| `enabled` | The projected action can be invoked now | Contract producer / presenters |
| `disabled` | The projected action is intentionally non-executable | Contract producer / presenters |
| `reasonCode` | Stable identity of the denial | Contract producer |
| `reasonMessage` | User-facing explanation | Contract producer |
| `allowed` | Compatibility execution permission; must not contradict authorization and business availability | Contract producer |

Frontend `busy`, `pending`, focus and loading are transient interaction states.
They never redefine authorization or business availability.

## 3. Decision matrix

| Authorization | Business condition | Presentation | Server result |
| --- | --- | --- | --- |
| Denied | Any | Hidden | Reject if invoked |
| Allowed | Eligible | Visible + enabled | Execute |
| Allowed | Business state ineligible with explanation value | Visible + disabled + reason | Reject if invoked |
| Allowed | Business data incomplete | Declared guidance policy: visible-disabled reason or visible-enabled with server validation | Server revalidates |
| Allowed | Transient busy/pending | Temporarily disabled/loading | Prevent duplicate invocation |
| Allowed | Unsupported capability | Hidden or explicit degraded state | Never execute |
| Allowed | Concurrent/already executed | Contract reason or hidden according to policy | Server rejects duplicates |

## 4. Producer responsibility

### P0 platform kernel

- `addons/smart_core/core/unified_page_contract_v2_action.py`
- `addons/smart_core/core/unified_page_contract_v2_assembler.py`
- `addons/smart_core/core/unified_page_contract_v2_status.py`
- `addons/smart_core/core/unified_page_contract_v2_runtime.py`
- `addons/smart_core/core/action_guidance.py`
- `addons/smart_core/app_config_engine/services/assemblers/page_assembler.py`
- `addons/smart_core/handlers/execute_button.py`

P0 must:

- hide explicit actor denials;
- preserve business-state denials as visible disabled where declared;
- preserve stable reason identity and message;
- fail closed on unresolved identity or authority;
- keep final execution validation in `execute_button`.

### P1 business producers

- `addons/smart_construction_core/services/financial_workspace_contract.py`
- `addons/smart_construction_core/handlers/payment_request_available_actions.py`
- `addons/smart_construction_core/models/support/workflow_contract_service.py`
- `addons/smart_construction_core/core_extension.py` and business action extensions
- `project_execution_next_actions_builder.py`
- `project_execution_readiness_precheck_builder.py`
- `project_plan_next_actions_builder.py`
- settlement, payment and cost slice next-action builders
- risk and My Work action handlers

P1 owns business eligibility, state eligibility, data-completeness guidance,
reason codes and messages. P1 must not use a generic `enabled=false` for every
failure category.

## 5. Frontend responsibility

- `contractFormPresenter.ts`
- `contractActionPresentation.ts`
- `canonicalNativeFormBridge.ts`
- `CanonicalActionBar.vue`
- `ContractFormProductHeader.vue`
- `ScDropdown.vue`
- Action View action presentation runtimes

Frontend must:

- not infer business eligibility;
- hide explicit unauthorized actions;
- retain authorized business-state denials with their reason;
- keep body/header/direct/overflow equivalent;
- keep busy/loading separate from action authority.

## 6. Final execution boundary

`execute_button` must revalidate:

- action identity and contract binding;
- actor authorization;
- current business state;
- record identity and company scope;
- concurrency/idempotency;
- data consistency and service-level invariants.

Frontend disabling is never a security control.

## 7. Initial Golden Sample

`payment.request` → `payment_execution`

- unauthorized actor: hidden;
- approved + eligible: visible enabled;
- approved + missing payment basis: visible disabled with
  `PAYMENT_EXECUTION_BASIS_MISSING`;
- approved + incomplete payee account: visible disabled with
  `PAYEE_ACCOUNT_INCOMPLETE`;
- active execution: visible disabled with
  `PAYMENT_EXECUTION_ALREADY_EXISTS`;
- fully paid: visible disabled with `PAYMENT_REQUEST_FULLY_PAID`;
- concurrent/duplicate invocation: server rejects even if the UI was stale.

The P1 producer keeps `businessAvailable=true` for approved state conditions
whose only remaining blocker is data completeness; `enabled` combines state,
data and authorization.

## 8. Producer inventory

The inventory separates executable business actions from state guidance,
administration controls and navigation. Only the first group is a Contract V2
business-action surface.

| Producer family | Authority it supplies | Current classification | Consumer / evidence |
| --- | --- | --- | --- |
| Native form header and layout buttons | Native view composition, field modifiers, declarations | Adopted: authoritative buttons receive an entitlement verdict; unresolved group constraints fail closed | `page_assembler.py`, `unified_page_contract_v2_assembler.py`, `test_unified_page_contract_v2_mobile_compact.py` |
| Payment request submit / approve / reject / complete | State, prerequisites, role capability and method availability | Adopted: actor denial is hidden; state or prerequisite denial is visible disabled with reason | `payment_request_available_actions.py`, `financial_workspace_contract.py`, `test_p1_payment_request_capability.py` |
| Payment execution (`生成付款登记`) | Document type/state, paid state, active execution, basis/account completeness and finance capability | Adopted: authorization hides; state and data denial remain visible disabled with stable reason | `financial_workspace_contract.py`, `test_p1_payment_request_capability.py` |
| Native action guidance JSON fact | Actor-readable computed JSON fact bound by the native declaration | Adopted: blocking changes business availability, not authorization; confirmation remains invokable with warning | `action_guidance.py`, `test_unified_page_contract_v2_mobile_compact.py` |
| Workflow contract service | Record state, editable phase, approval phase and evidence gates | Supporting authority only: it publishes state candidates and narrowing evidence; it is not an execution grant | `workflow_contract_service.py`, `test_workflow_contract_backend.py`, assembler workflow-veto tests |
| `execute_button` and work-item origin | Final ACL, record rule, action identity, state, concurrency and idempotency | Adopted as the security boundary; never replaced by frontend disabled state | `handlers/execute_button.py`, `test_execute_button_server_action_boundaries.py` |
| Action View collection create | Model ACL, action/menu publication and entry capability | Adopted: actor denial hides the create entry; valid target remains an executable action | `ui_contract_v2.py`, collection-create projection tests |
| Settlement/payment/cost/project `next_actions` block builders | Project facts and stage guidance | Compatibility guidance, not Contract V2 action rules. The legacy `action_list` payload has no registered Web block consumer and is not evidence of a delivered business action. It requires a separate retirement or migration decision. | P1 dashboard builders and their block-fetch handlers |
| Project decision-engine recommendations | Project state rules and configured recommendation rules | Guidance only: recommendations navigate to an intent; they do not grant execution | `project_next_actions_builder.py`, `project_next_action_service.py` |
| Product configuration and platform administration controls | Authoring surface state, editable/published/busy flags | Local tool interaction state, not Contract V2 record business actions | `frontend/apps/web/src/views/businessConfigSurface`, product configuration handlers |
| Navigation and route entries | Published menu state and route availability | Navigation projection, not a business action; no `execute_button` or action `enabled` inference | canonical navigation projection and `CanonicalNavigationMenuNode.vue` |
| My Work completion and other command intents | Command handler validation | Server command boundary; UI eligibility must come from its owning contract, not from generic action inference | My Work and work-item boundary tests |

### 8.1 Projection rules

1. P0 copies producer facts; it does not create authorization or business
   eligibility.
2. `reasonCode` is the stable diagnostic identity. `reasonMessage` is the
   user-facing explanation and may be projected from the producer's declared
   `blocked_message`.
3. An explicit authorization denial hides the action. A business-state or data
   completeness denial remains visible when the producer supplies an
   explanation value.
4. A workflow catalog omission cannot grant an action, and a catalog `enabled`
   value cannot override an explicit stricter denial.
5. `execute_button` rechecks the full target even when the frontend action was
   previously enabled.

## 9. Required test mapping

| Contract behavior | Automated evidence |
| --- | --- |
| Authorization hides; business denial remains visible | `test_unified_page_contract_v2_mobile_compact.py` |
| Business reason message reaches action and status | `test_unified_page_contract_v2_mobile_compact.py` |
| Native guidance preserves authorization and narrows business availability | `test_unified_page_contract_v2_mobile_compact.py` |
| Payment execution authorization / state / data split | `test_p1_payment_request_capability.py` |
| Final execution identity and ACL boundary | `test_execute_button_server_action_boundaries.py` |
| Frontend presenter hides unauthorized and disables business-denied actions | `canonical_form_presenter_test.ts`, `canonical_form_presenter.unit` |
| Direct and overflow disabled reasons | `verify.frontend.contract_header_action.unit` |
| Workflow contract catalog is narrowing-only | `test_workflow_contract_backend.py`, assembler workflow-veto tests |

## 10. Compatibility and rollback

No schema or field-name change is introduced. The rollback unit is this batch's
commit set: restore prior action projection behavior and the previous assembled
contract cache version. No data migration is required.

The legacy `action_list` dashboard guidance remains explicitly outside the V2
adoption claim. It must not be converted wholesale to visible-disabled actions;
a separate product decision must choose retirement, migration to a registered
block, or a dedicated action surface.
