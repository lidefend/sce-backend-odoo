# Payment Request Golden Floorplan V1

## Status and boundary

This document freezes the first product blueprint for
`PRODUCT-PAYMENT-REQUEST-GOLDEN-FLOORPLAN-V1`.

It is a P1 construction-product presentation decision built on the existing
Normalized Contract V2 and the in-memory Canonical Form Render Model. It is
not a new API, contract version, Scene Contract, persisted configuration
format, or source of business permission. The backend remains authoritative
for values, visibility, editability, required state, blockers, action status,
action identity, and execution eligibility.

The internal seven-section payment contract remains the semantic source for
field order and grouping. The user interface does not have to expose those
seven sections as seven consecutive tabs. The floorplan composes the existing
facts into a professional task page without copying or recomputing them.

## Product outcome

A construction finance user must be able to answer, without reading a field
warehouse:

1. What payment is this and who receives it?
2. What contract or approved settlement supports it?
3. How much is requested, already paid, and still payable?
4. Is the receiving account complete and where did it come from?
5. What blocks the current task?
6. What is the one legal next action?
7. Where are the evidence, related records, activity, and audit trail?

## Floorplan anatomy

```text
ObjectTaskPage
├─ ObjectSummaryHeader
│  ├─ identity + lifecycle status
│  ├─ amount summary
│  ├─ counterparty / account summary
│  └─ legal next action / blocking notice
├─ TaskCanvas
│  ├─ current task inputs
│  ├─ evidence required for this task
│  └─ task-local validation
├─ BusinessContextRail
│  ├─ contract / settlement context
│  ├─ cumulative amount facts
│  └─ account source / risk facts
├─ RelationPanel
│  ├─ payment details / executions
│  ├─ invoices
│  └─ attachments
├─ ActivityTabs
│  ├─ activity and collaboration
│  ├─ approval history
│  └─ audit drawer
└─ StickyActionBar
   ├─ one effective primary action
   ├─ at most one direct secondary decision action
   └─ applicable remaining actions in More
```

The component names describe semantic responsibilities. TDesign is the
default product implementation. Native remains the compatibility/loading
fallback and UI5 remains a compatibility adapter; neither defines a parallel
product page system or a user-selectable product capability. Adapter choice
must not change field identity, displayed business value, action reference,
request payload, or permission result.

## Canonical content classification

| Content class | Existing authoritative facts | Product placement | Empty policy |
| --- | --- | --- | --- |
| identity | `name`, `payment_flow_label`, `state`, `validation_status`, `date_request` | summary header | generated name may be absent only before first save; no disabled empty input |
| party | `partner_id`, `actual_payee_unit`, `project_id`, `company_id` | header party card; editable selectors stay in task canvas | relation values show business names, never raw IDs |
| basis | `contract_id`, `settlement_id`, `material_settlement_id`, `related_document_text` | task canvas selector plus context summary | if not applicable, show `不适用`; if required and missing, show blocker and repair entry |
| amount | `amount`, `request_amount_display`, `paid_amount_total`, `unpaid_amount`, `currency_id` | amount summary; editable amount stays in task canvas | zero is a value; missing is not rendered as `false` or `-` in a summary card |
| account | `partner_account_name`, `partner_bank_name`, `partner_bank_account`, `payee_account_completeness`, `payee_account_source_display` | account card and blocker | missing parts are named explicitly; never expose a blank account card |
| execution | `payment_execution_status_display`, `legal_next_action_display`, `payment_blocking_reason_display` | summary header and blocking notice | always use backend facts; the frontend never derives a next step from state order |
| context money | contract and settlement total/paid/unpaid/payable facts | business context rail | hide a wholly inapplicable group; show `不适用` for a single confirmed non-applicable fact |
| evidence | `attachment_ids`, invoice/detail relations, note | relation/evidence panels | empty panels use an intentional empty state with an add/view action only when allowed |
| collaboration | chatter, activity, approval history | activity tabs | preserve the normalized subordinate identity; do not count as a main section |
| audit | approval and business audit facts declared by the contract | audit drawer, role-limited where declared | legacy IDs and migration markers never enter the product surface |

## Blueprint A — first create

### User task

Create a valid payment request with the minimum complete business basis, save
it, leave the page, and reopen it without losing facts.

### Composition

- Header: `新建付款申请`; no empty generated document number, workflow history,
  payment execution summary, or audit facts.
- Task canvas, in order:
  1. payment object: project, counterparty, business date;
  2. payment basis: contract or approved settlement, including material
     settlement when applicable;
  3. requested payment: amount and currency;
  4. receiving account confirmation: authoritative snapshot and source;
  5. note and attachments.
- Context rail: populate contract/settlement amounts only after a basis is
  selected; before that show one purposeful basis prompt, not empty cards.
- Sticky action bar: one primary `保存`; no submit, approval, payment execution,
  or technical configuration actions.

### Exit

- No empty readonly control in the first screen.
- Required facts follow normalized `required`; the floorplan adds no rule.
- Save uses the existing `form.save` action reference and unified executor.

## Blueprint B — draft or rejected edit

### User task

Correct business facts and submit or resubmit a request.

### Composition

- Header: document number, payment type, draft/rejected status, amount, payee,
  account completeness, blocker, legal next step.
- Rejected records show the current rejection reason as a prominent decision
  notice; draft records do not reserve empty space for it.
- Task canvas contains only normalized editable or required fields. Readonly
  business context is summarized in the rail instead of repeated as disabled
  inputs.
- Context rail shows contract/settlement amount facts, account source, prior
  payment facts, and risk/advisory facts when present.
- Sticky action bar: the current effective primary action only. Save may be a
  direct secondary action when both save and submit are valid; unavailable
  actions do not occupy the task bar.

### Exit

- `edit` is distinct from first `create`; generated identity and state context
  remain visible without becoming editable.
- Resubmission preserves history and clears only the current rejection reason
  according to backend workflow behavior.

## Blueprint C — approved handling

### User task

Verify that an approved request is ready for payment and create or open the
single current payment execution.

### Composition

- Header: document identity and approval state; requested, paid, and unpaid
  amounts; payee/account source; execution status; legal next step.
- Blocking notice appears before any action when the backend reports missing
  basis, incomplete account, role handoff, an in-flight execution, or full
  payment.
- Main content is read-only business cards and relation panels, not disabled
  inputs.
- Context rail shows contract/settlement basis and cumulative financial facts.
- Sticky action bar:
  - `生成付款登记` when it is the one enabled normalized primary action;
  - `查看付款登记` when an active execution exists;
  - no executable primary when blocked or fully paid.

### Exit

- Action label, enabled state, blocker, execution status, and legal next step
  are mutually consistent because all are consumed from backend authority.
- A non-capable role sees the handoff reason and cannot execute through UI or
  RPC.

## Blueprint D — blocked repair

### User task

Understand exactly why payment cannot continue and reach the correct repair
surface without guessing.

### Composition

- Header retains identity, amount, payee, status, and legal next step.
- `BlockingNotice` contains backend reason text and the normalized repair
  action when one exists.
- Missing basis names the required contract/settlement relationship.
- Incomplete account names each missing account part and shows the declared
  account source.
- Role handoff explains that another capability is required without exposing
  group XMLIDs or role implementation details.
- In-flight execution links to the active execution; fully paid shows closure
  rather than a repair action.

### Exit

- A blocked task remains visible and understandable.
- The floorplan never converts a disabled action into an enabled repair action.
- No label, model name, state sequence, or role-name inference is used.

## Blueprint E — completed readonly

### User task

Audit what was requested, approved, paid, and linked without accidentally
editing historical facts.

### Composition

- Header: completed state, requested/paid/unpaid amounts, payee/account, latest
  execution status, and closure text.
- Main content: party, basis, amount, account, payment execution, invoice, and
  evidence cards.
- Activity tabs: approval history, collaboration, and payment chronology.
- Audit drawer: source/import metadata only; migration markers are normalized
  out of ordinary notes.
- No save action and no enabled business mutation.

### Exit

- All controls are readonly and rendered as facts rather than disabled inputs.
- Every relation uses a business display name and preserves its canonical ID
  only as non-visible execution identity.

## Blueprint F — mobile 390

### User tasks

Review a pending/approved request, understand a blocker, approve or reject when
authorized, and reach the one legal payment action.

### Composition

- Single column; no horizontal section navigation.
- Collapsed summary header keeps status, amount, payee, blocker, and next step
  visible.
- Context rail moves below the task canvas as accordions in the same semantic
  order.
- Sticky action bar remains reachable above the safe-area inset and never
  covers content.
- Relation/evidence/activity panels use vertical disclosure; tables switch to
  card/list presentation without changing the normalized data request.

### Exit

- Zero horizontal overflow.
- Primary action is visually detectable and directly reachable.
- Driver switching does not refetch the contract or create a business write.

## Action placement contract

1. Exactly one visible and enabled normalized primary action may occupy the
   sticky primary slot.
2. A blocked current task may remain visible and disabled with its backend
   reason, but it does not claim the executable primary slot.
3. Approval reject may be a direct secondary decision only when the normalized
   action is visible and enabled for the current user.
4. Configuration, debug, import, migration, and unavailable technical actions
   never occupy the main task bar.
5. Every click retains the normalized `actionId`, `actionKey`,
   `backendIdentity`, and original execution reference and enters the existing
   unified executor.

## Empty and readonly policy

- `false`, `null`, and absent non-boolean values render as empty, not text.
- A confirmed non-applicable business fact renders as `不适用` or its entire
  optional group is collapsed.
- An applicable missing required fact renders as a blocker or validation
  message, never `不适用`.
- Empty derived facts do not become disabled inputs.
- Readonly mode uses semantic fact components; it does not imitate edit mode by
  disabling every control.
- Audit/source facts never fill ordinary page space merely because they exist
  in the normalized payload.

## Implementation checkpoints

### Checkpoint 1 — semantic floorplan shell

Implement `ObjectTaskPage`, `ObjectSummaryHeader`, `TaskCanvas`,
`BusinessContextRail`, `BlockingNotice`, and `StickyActionBar` using the
existing Canonical Render Model. Do not add fields, permissions, state logic,
or action mapping.

### Checkpoint 2 — business fact components

Add `MoneyFact`, `PartyCard`, `BankAccountCard`, `RelationPanel`,
`ActivityTabs`, and `AuditDrawer`. TDesign is the default implementation;
Native/UI5 prove parity rather than define separate semantics.

### Checkpoint 3 — golden payment vertical

Run create/save/reopen, edit/submit, approval, blocked repair, payment
continuation, partial/full payment, reversal, completed readonly, and mobile
tasks against real normalized payloads.

### Checkpoint 4 — reuse proof

Apply the proven floorplan to `sc.payment.execution` and one project or contract
detail. Only semantics proven necessary by at least two pages may be promoted
into reusable platform machinery.

## Product acceptance scorecard

| Dimension | Weight | V1 pass condition |
| --- | ---: | --- |
| business task efficiency | 25 | primary journey has no irrelevant required interaction or hidden next step |
| first-screen fact completeness | 20 | identity, party, basis, amount, account, blocker, execution, and next action are clear |
| hierarchy and progressive disclosure | 20 | task, context, relation, activity, and audit zones are distinct |
| action and blocker clarity | 15 | one effective primary; every blocked task has an understandable reason |
| visual, responsive, accessibility | 10 | desktop/390 usable, no overflow, adequate action contrast, keyboard path retained |
| data trust and consistency | 10 | no raw IDs, migration text, contradictory status/action, or driver-specific value drift |

The page is product-qualified only at 90/100 or above and when all hard
conditions pass: zero raw relation IDs, zero empty readonly controls in the
task surface, zero duplicate groups, zero migration markers in ordinary
content, at most one effective primary action, and zero unexpected browser or
network errors.
