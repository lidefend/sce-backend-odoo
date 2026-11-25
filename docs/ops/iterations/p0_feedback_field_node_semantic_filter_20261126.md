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
- `git diff --check`: passed.
- Real browser replay: pending candidate commit and local runtime rebind.

## Exclusions

No backend contract, project model, view, permission, database, fixture or
deployment change.
