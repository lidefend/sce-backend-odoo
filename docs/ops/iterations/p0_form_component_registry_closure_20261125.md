# Contract V2.7 Semantic and Renderer Responsibility Separation

## Current Result

Contract V2.7 now accepts only `2.7.x`, carries backend semantics and native
field management facts, and publishes no frontend component identity. The
frontend selects Vue implementations from its own registry and reports frontend
capability gaps separately from backend contract defects.

The real `projects.ledger` list-to-record browser journey now passes on the
governed `sc-local-dev` / `sc_dev_demo` runtime as the `wutao` business
configuration administrator. The browser captured the actual list contract,
opened record `4` through action `590` / menu `382`, and reached Form
`state=ok` independently at desktop `1440x960` and mobile `390x844`. Both runs
preserved the same model/record/action/menu identity, reported no page errors,
and exercised read-only, date and many2one semantics. The same target also
passed the real ORM money chain and strict decoding of 45 Form descriptors.

## Ownership

- Formal Product Layer: P0 platform kernel product
- Layer Target: Contract V2.7 semantic specification, production, negotiation,
  decoding, cache identity and frontend implementation resolution
- Module: `smart_core`
- Standard vs User-Specific: platform engineering standard
- Why Here: this is the shared contract boundary used by every page and client.
- Why Not Elsewhere: P1 views and P1 field declarations are valid inputs; the
  frontend must not compensate for backend implementation identity.
- Blast Radius: semantic/implementation registries, backend producers, strict
  field descriptors, frontend decoding/store/presentation, generated carriers,
  cache identity, snapshots and affected ORM consumers.

## Implemented Boundaries

- Backend owns semantics, native field facts, constraints, permissions,
  actions, source provenance and payload protocols.
- Frontend owns semantic-to-Vue/renderer mapping, renderer version, visual
  profile, native host capability and capability-gap reporting.
- `componentKey`, `component_key` and `componentRegistry` are forbidden V2.7
  wire facts.
- Pre-V2.7 protocol support and the development-only compatibility drill are
  removed.
- Node validation remains semantic/payload based and does not execute embedded
  Odoo components.

## Review Remediation

- Internal `system.init` callers explicitly declare the `2.7.x` client contract
  and no longer convert negotiation failure into an empty catalog, package or
  healthy scene result.
- Store field projection uses canonical `relationEntry` and `widgetOptions`;
  the relation consumer regression covers selected-ID hydration and inline
  create after the real Store projection.
- Unknown or misplaced node semantics fail as contract defects before payload
  validation, while a valid registered semantic without a renderer remains a
  frontend capability gap.
- Frontend implementation identity is rejected only in structural contract
  locations; opaque business JSON is not misclassified as renderer selection.
- The assembled-contract cache identity is re-pinned to `v122` with digest
  `7aeedd00250d9f75eda38f4d37d6fe286146ee8b3519c720e35ef83fe567d1d5`.
- The V2.7 policy guard, generated component-driver inventory digest and
  remediation source hashes were reconciled to the final source state.

## Independent Review Follow-up

The first exact-head remote run (`31d4b086c318644dcef427836bf2583c12c34344`)
passed `public_guard`, `frontend_release_gate`, and the completed frontend/managed
ORM jobs, but failed one backend test and its downstream coverage aggregate.
Review also found three remaining boundaries. The follow-up changes are:

- The refund feedback HTTP assertion now reports exact JSON paths and value
  types. It judges partner identity only in the feedback business payload,
  patches and evaluation details; unrelated session, user and elapsed-time
  scalars in the intent envelope cannot create a false identity leak.
- `relationEntry.default_vals` is an opaque business-value branch in backend
  implementation-identity scanning, backend semantic validation and frontend
  strict decoding. Structural descriptors and unknown node semantics still fail.
- Internal negotiation canonicalizes supported snake/camel aliases before
  supplying defaults. Explicit camelCase versions and client identities remain
  fail-closed; conflicting aliases are refused.
- Changed-test selection resolves actual Odoo/unittest inheritance instead of
  relying on a `Test` name prefix. Existing `SubmissionReadinessNoticeP1Tests`
  and `SubmissionReadinessNoticeSuppressionTests` are selected, mixed changes
  retain every ORM class, offline `unittest.TestCase` stays out of ORM routing,
  and an unrecognized test base blocks the planner.
- The assembled-contract cache identity is now `v123` with input digest
  `3d7776d0af5f1841d6590cde846446793b4f096244e649b3368cd05521753d7a`.

## Post-Merge Revalidation Correction

After the original tree entered main, revalidation on the updated branch
exposed a remaining V2.7 consumer:

- `useDraftFeedbackEvaluation` still discovered feedback hosts through
  `componentKey`, while V2.7 contracts carry only `semanticType`. Dynamic
  feedback therefore produced no presentation in the full frontend release
  lane.
- The protocol test fixture also still declared the old structural component
  identity.

The fixture now declares `semanticType: feedback_message`, and the dynamic
consumer resolves that semantic through the frontend implementation registry.
`verify.frontend.feedback_evaluation.unit` now passes, including atomic
presentation, stale-response isolation and relation-presence cases.

## Runtime Alignment Correction

The first browser retries exposed runtime evidence that initially looked like a
contract defect. Root-cause analysis showed:

- the governed Odoo process had started before the candidate source changes, so
  the running backend was stale until a governed restart;
- the dashboard probe still assumed an unconditional orchestration `2.1.0`,
  while the current producer correctly emits `2.0.0` when no optional carrier
  is enabled;
- a complete Form contract was then misreported as missing
  `relation_entry.options_limit` because the native-node adapter still emitted
  snake_case `relation_entry` while the canonical V2.7 consumer read
  `relationEntry`.

The frontend runtime adapter now normalizes native producer evidence once into
the canonical descriptor. The browser script asserts the producer-selected
orchestration version and reports the actual URL and stack for page errors.
Focused regression coverage proves that a complete declaration normalizes
successfully and that a genuinely missing declaration still fails closed.

The commit-time generated-evidence refresh also updated the contract structure
fingerprint, test inventory, complexity/split reports, frontend decision
authority inventory and component-driver takeover inventory from this candidate.

## Native Field Management Coverage

The Odoo 17 Web Client field-attribute set is now the reviewed upper bound for
client-management facts. The matrix is recorded in
`docs/architecture/p0_contract_producer_01/native_field_management_capability_matrix.md`.

This round additionally closes:

- `money` semantics for both `monetary` and `float + monetary widget`, with a
  required independent `currencyField`;
- currency display propagation and precision preservation;
- `help` and `uiUsage` projection/decoding;
- field `size`, change-default, searchable/sortable, store, translate, trim,
  aggregation and related-path facts;
- fact-field hydration based on canonical `uiUsage`;
- the contract cache identity and semantic digest invalidation.

Raw permission groups and backend implementation details such as compute,
inverse, search method names, database columns and cache internals remain
backend-only.

## Validation

Candidate identity:

- Base/main: `5b2724b1b56da295526f3b9e74e73f986a739085`
- Branch: `fix/project-ledger-registry-closure-20261125`
- The exact follow-up HEAD is recorded by PR #1004 after commit.

The first full affected iteration on `31d4b086` remains the parent-run evidence:

- Receipt:
  `.runtime/frontend-dev-validation/executions/20261125T121530Z-3627665-224518041/receipt.json`
- Status: passed
- Local targets: 78
- Freshly executed targets: 78
- Reused unchanged passing targets: 0
- Deferred remote module baselines: 2
- Layers: frontend, backend, contract, governance
- Required targets all exited zero
- `verify.smart_construction_core.module_baseline` and
  `verify.smart_core.close_02.module_baseline` are deferred to exact-head remote
  integration CI.

The review follow-up uses the requested affected set rather than repeating that
78-target iteration:

- `verify.unified_page_contract.v2.assembler`: passed.
- `verify.p0_contract_producer.p0a.backend_unit`: passed, 30 checks.
- `verify.p0_contract_producer.design.unit`: passed.
- `verify.node_component_validation.unit`: passed, 41 tests.
- `verify.node_component_capabilities.unit` and
  `verify.native_widget.provenance.unit`: passed.
- `verify.p0_contract_producer.p0a.descriptor_conformance`: passed; 45 strict
  descriptors decoded from the real Form.
- `verify.frontend.typecheck.strict`, `verify.frontend.lint.src`,
  `verify.frontend.contract_basis.enforce`, `verify.form_structure_authority_unification.unit`
  and `verify.contract.structure_lock`: passed.
- Changed-test selector and incremental planner tests: passed, 253 tests across
  both registered units.
- Refund feedback ORM: passed, 10 tests; refund feedback HttpCase: passed, 1
  test, including the path-aware identity probe.
- Real `projects.ledger` desktop and mobile browser rerun: passed after using the
  documented `wutao` demo identity.
- `verify.frontend.feedback_evaluation.unit`,
  `verify.frontend.typecheck.strict`, `verify.frontend.lint.src`,
  `verify.frontend.contract_basis.enforce` and
  `verify.form_structure_authority_unification.unit`: passed for the
  post-merge semantic-consumer correction.

Run-bound checks:

- `component_registry_closure`: passed, 29 tests.
- `real_project_form_decode`: passed, 46 checks, including 45 strict descriptors.
- `project_ledger_user_path`: passed, desktop and mobile runtime readback bound
  to `artifacts/p0_contract_producer_01/p0a_browser_acceptance.json`.

Representative passed checks:

- strict V2.7 producer/decoder and current-version acceptance;
- pre-V2.7 and component-identity rejection;
- semantic registry and generated-carrier consistency;
- real project form strict descriptor conformance;
- real ORM monetary contract and frontend money presentation;
- project/payment/page-finalize ORM consumers;
- canonical form presenter, collection relation runtime and typed frontend;
- contract cache input digest/version guard;
- relation-entry native-to-canonical normalization with 7 focused cases;
- real `projects.ledger` list -> row -> Form browser acceptance for desktop and
  mobile, including the 45-descriptor strict decode; both Forms reached `ok`
  with `page_errors=[]`.

Not run:

- The current follow-up HEAD has not yet been published.
- Independent review: excluded by the owner's explicit instruction to publish
  the PR without waiting for it. This exclusion is not evidence of review.

## Remaining Exact Steps

1. Commit the clean exact candidate.
2. Update existing PR #1004 through the governed entrypoint.
3. Verify the four required checks on its exact HEAD and wait for independent
   review before any merge decision.

Deployment, database rebuild and production data migration are outside this
batch.
