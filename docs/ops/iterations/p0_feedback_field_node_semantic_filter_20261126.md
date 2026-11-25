# P0 Feedback Field/Node Semantic Filter

## Result

In progress.

## Ownership

- Formal Product Layer: P0 platform kernel product
- Layer Target: frontend draft-feedback host discovery
- Module: frontend
- Standard vs User-Specific: platform engineering standard
- Why Here: the backend Form contract is valid; only the frontend consumer
  incorrectly treats field semantics as node semantics.
- Why Not Elsewhere: changing the project Form or adding a project-specific
  frontend branch would alter or compensate for correct contract facts.
- Blast Radius: draft-feedback discovery, feedback protocol regression and the
  real projects.ledger row-to-Form journey.

## Observed Failure

The governed `wutao` projects.ledger browser journey loaded the list, opened
record `DEMO-PJ-065`, and rendered the Form, but emitted:

```text
ContractGapError: 节点语义 text 未在独立语义规范中登记
```

The Form contract contains valid field nodes with `semanticType=text`.
`draftHosts()` visits every layout node and calls
`resolveNodeSemanticImplementation()` before checking whether the node declares
the feedback evaluation capability.

## Implemented Change

`draftHosts()` now checks the node's feedback purpose, capability and
visibility-owner declaration before resolving node semantics. Field nodes with
valid field semantics such as `text` therefore remain outside the node
implementation lookup. A feedback-capable node still resolves through the
frontend node implementation registry and remains fail-closed for an invalid
node semantic.

The protocol fixture now gives both source field nodes `semanticType: text`,
matching the real project Form contract.

## Validation

- Pre-fix focused regression:
  `make verify.frontend.feedback_evaluation.unit` failed with the same
  `ContractGapError: 节点语义 text 未在独立语义规范中登记`.
- Post-fix focused regression:
  `make verify.frontend.feedback_evaluation.unit` passed.
- `make verify.frontend.typecheck.strict`: passed.
- `make verify.frontend.lint.src`: passed with the existing three warnings in
  `frontend/packages/ui` and zero errors.
- `make ci.local.iteration`: passed, including strict typecheck and the affected
  frontend/governance set. The planner did not select the two explicitly
  declared run checks, so they were also executed directly.
- `git diff --check`: passed.
- Candidate runtime: `sc-local-dev` / `sc_dev_demo`, source
  `d31758e727f81d6a3fc1c83b08c4cc43e8f3e825`, frontend fingerprint
  `3fcdeb3b310946dd383a129002970059b5727cc9bf7f61452e036156351e179f`.
- `P0A_LOGIN=wutao P0A_PASSWORD=123456 make
  verify.p0_contract_producer.p0a.browser`: passed on desktop and mobile.

The browser report records the same row and Form identity on both viewports:

- clicked record `4`;
- Form state `ok`;
- model `project.project`;
- action `590`;
- menu `382`;
- strict Contract V2 decode of 45 descriptors;
- no page errors;
- the only console errors are the five intentionally exercised 409
  `CONTRACT_VERSION_UNSUPPORTED` negative cases.

## Exclusions

No backend contract, project model, view, permission, database, fixture or
deployment change.
