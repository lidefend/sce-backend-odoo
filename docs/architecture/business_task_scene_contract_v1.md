# Business Task Scene Contract v1

## Decision

This document continues on the single active `feature/business-task-scene-contract-v2`
integration line at baseline `0c89746904232fb168593d3610289aa0dfcb6075`.

The project does not introduce a fourth page protocol. `business_task` is a versioned
terminal profile inside the existing Scene Contract. Existing native and normalized
contracts remain compiler inputs; they are not renderer inputs.

```text
Odoo model/security/native view
          -> UI base / normalized contract (internal)
          +  domain capability verdicts (authoritative)
          +  P1 task profile (industry semantics)
          -> Scene Contract.business_task (terminal)
          -> generic scene runtime
          -> native / TDesign / UI5 driver
```

## Product boundary

| Item | Owner | Responsibility |
| --- | --- | --- |
| Business-task schema, compiler mechanics and fail-closed validation | P0 `smart_scene` | Generic mechanism only |
| Construction task goals, stages, facts, blockers, handoffs and outcomes | P1 `smart_construction_scene` | Reusable construction-industry semantics |
| Business state, permission and action verdicts | Domain models/services | Authoritative business decisions |
| Layout and interaction rendering | Generic frontend scene runtime | Render contract without business inference |
| Visual control implementation | Scene UI driver | Native, TDesign or UI5 without semantic authority |

The scene layer must not query ORM or invent a business verdict. P1 profiles reference
domain facts and capabilities; the compiler projects already-authoritative values.

## Terminal vocabulary

`business_task` contains nine sections:

- `task`: user goal, expected outcome, mode, stage and state;
- `facts`: business facts with applicability and source authority;
- `inputs`: visible/readonly/required decisions with source authority;
- `blockers`: active reason, repair capability and responsible party;
- `capabilities`: business availability, authorization, execution state, safety,
  idempotency and outcome;
- `evidence`: attachments, approvals, audit or other proof required by the task;
- `relations`: business relationships and traceability anchors;
- `completion`: completion verdict, next capability and outcome code;
- `profile_version`: independent version for forward-compatible profile evolution.

The profile rejects adapter vocabulary such as `model`, `view_type`, `xml_id`,
`notebook`, `modifier`, `odoo_action` and `server_action_id`. Such values may exist in
compiler inputs or restricted diagnostics, but a product renderer cannot depend on them.

## Authority rules

| Semantic | Authority | Compiler rule |
| --- | --- | --- |
| Business fact value/state | Domain model/service | Project only; never calculate in scene/frontend |
| Business availability | Domain capability service | Explicit boolean required |
| Authorization | Existing capability/ACL verdict | Explicit boolean required; missing means deny |
| Enabled state | Availability + authorization + active blockers | Must be internally consistent |
| Block reason and repair | Domain/P1 task profile | Disabled actions cannot report `OK` |
| Primary action | P1 presentation policy after verdict merge | At most one enabled primary |
| Input interaction | Native modifiers + policy + state verdict | Explicit visible/readonly/required booleans |
| Outcome and next step | Domain transition + P1 task profile | Frontend must not infer from state sequence |

## Compiler input boundary

The compiler accepts two already-materialized inputs:

- `profile`: P0/P1 declaration of task wording, ordering, presentation,
  blocker relationships, safety, idempotency and expected outcome;
- `semantic_supply`: resolved facts, applicability, interaction flags,
  availability, authorization, enabled state, reasons and source authorities.

The compiler has no environment, ORM, user or company access. It copies only an
explicit field allowlist. Extra adapter metadata in the semantic supply is not
emitted. Missing declared supply is an error; missing authorization never falls
back to a role name or a permissive default.

The resulting trace contains deterministic profile, supply and sealed-contract
SHA256 values. The seal covers terminal semantics and can be independently
verified after transport or evidence capture.

## C0 authority inventory

The first representative task is the professional payment-request journey. Its current
facts are distributed across the payment model, available-actions handler, financial
workspace contract, field matrix, native/product contracts and browser audit. The task
profile must consolidate references to those authorities without copying their logic.

The current qualification records are inconsistent: the capability contract reports
runtime implementation while all fourteen field-completeness journeys remain `partial`.
Until journey evidence is bound to the terminal profile and one frozen candidate, the
product qualification remains `runtime_verification_required`.

## Long-line checkpoints

1. **C0 authority** — freeze source ownership and qualification semantics.
2. **C1 language** — validate the generic terminal profile and its negative cases.
3. **C2 compiler** — compile normalized input + domain verdicts + P1 profile; seal trace.
4. **C3 payment vertical slice** — readonly, create/edit, approval, execution and reversal.
5. **C4 local user simulation** — state transitions, role handoff, retry and isolation before browser.
6. **C5 frontend terminal** — scene components consume only `business_task`.
7. **C6 driver integration** — reconnect the existing UI5/TDesign/native component branch.
8. **C7 cross-model proof** — approval workbench plus contract/settlement representative pages.
9. **C8 governed runtime** — official acceptance environment and complete user journeys.
10. **C9 release** — clean install, upgrade, idempotency, performance and independent review.

The UI driver experiment remains independent through C4. It is rebased and connected only
after the terminal profile is stable, so vendor controls cannot influence contract design.

## Current checkpoint

- C0 authority and qualification conflict are documented.
- C1 terminal vocabulary and fail-closed validation are executable.
- C2 pure compiler, source trace and deterministic seal are executable.
- The compiler rejects adapter vocabulary recursively across snake-case,
  camel-case and kebab-case spellings. Its top-level and compatibility mirrors
  are deep-copy isolated and contain one compiler pipeline event each.
- C3 has started with a construction-standard payment-request task profile:
  thirteen first-screen facts, three blocker families, nine capabilities,
  two evidence groups and five relationship anchors. Pure behavior coverage now
  exercises draft submission, approval handoff, approved execution creation,
  execution reopening, account repair and authorization denial. A final
  post-canonical extension point
  now projects the existing normalized action verdicts and hydrated facts into a
  sealed `runtimeContract.businessTaskSceneContract`; it never recomputes ACLs,
  roles or business availability. It does not yet change the payment product
  qualification or runtime state.
- Payment execution submission, approval handoff, paid posting, cancellation and
  reversal now use a separate C3 task profile backed by canonical
  `sc.payment.execution` action/status verdicts. The payment-request profile does
  not impersonate these downstream capabilities.
- C4 pure simulation now proves retry-stable seals, role-handoff verdict changes
  without business-fact drift, relationship-anchor continuity, and explicit
  terminal states. It is not a substitute for ORM transactions or browser evidence.
- C5 now has a framework-neutral frontend boundary: Contract V2 strictly decodes
  `runtimeContract.businessTaskContract`, rejects native adapter vocabulary and
  inconsistent verdicts, and exposes a terminal presentation model from the task
  profile alone. Visual scene components remain in the independent driver checkpoint.
- C7 vocabulary proof compiles approval-work-item and contract-settlement
  profiles through the same terminal schema. Contract settlement is now the first
  non-payment declaration connected to production: its domain service projects
  real model prechecks and exact capability-group/OCA review verdicts into the
  canonical action contract. The same domain service materializes structured
  blocker verdicts into `runtimeContract.businessTaskSemantics`; the scene
  projection refuses to infer blockers from display fields and fails closed
  when this authority is missing. The final terminal hook consumes only those
  normalized action/status and blocker verdicts. Alternate OCA/native methods for the same
  semantic capability select the one applicable method; simultaneous enabled
  aliases fail closed as ambiguous. Approval work-item remains declaration-only
  until its own authority adapter is connected.

## Exit metrics

- every terminal fact/input/capability has an explicit authority;
- no frontend business component reads native/Odoo vocabulary;
- unknown permission, applicability or action state fails closed;
- capability visibility is an authoritative domain verdict: state-inapplicable
  actions are hidden, while handoff and repair actions may remain visible but disabled;
- no disabled capability reports success reason;
- at most one enabled primary capability per task state;
- payment-request journey gates move from `partial` only with bound task, backend, browser,
  audit and retry evidence;
- at least two non-payment scenes prove that the mechanism is platform-generic.
