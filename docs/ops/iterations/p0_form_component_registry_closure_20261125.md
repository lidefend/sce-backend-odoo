# Contract V2.7 Semantic and Renderer Responsibility Separation

## Current Result

Contract V2.7 now accepts only `2.7.x`, carries backend semantics and native
field management facts, and publishes no frontend component identity. The
frontend selects Vue implementations from its own registry and reports frontend
capability gaps separately from backend contract defects.

The real `projects.ledger` list-to-record browser journey now passes on the
governed `sc-local-dev` / `sc_dev_demo` runtime as the `wutao` business
configuration administrator. The browser captured the actual list contract,
opened record `4` through action `590` / menu `382`, rendered the Form on
desktop, and completed the mobile company-dashboard path. The same target also
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

- Base/HEAD: `e940285aed4a9747931c26ec0a52283b5d296d14`
- Branch: `fix/project-ledger-registry-closure-20261125`
- Dirty candidate; not frozen or committed.

Complete affected local iteration:

- Receipt:
  `.runtime/frontend-dev-validation/executions/20261125T101002Z-2826532-577357370/receipt.json`
- Status: passed
- Local targets: 71
- Freshly executed targets: 69
- Reused unchanged passing targets: 2
- Deferred remote module baselines: 1
- Layers: frontend, backend, contract, governance
- Required targets all exited zero
- `verify.smart_construction_core.module_baseline` is deferred to exact-head
  remote integration CI.

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
  mobile, including the 45-descriptor strict decode.

Not run:

- Exact-head remote required CI: publication has not been performed.
- Independent review: excluded by the owner's explicit instruction to publish
  the PR without waiting for it. This exclusion is not evidence of review.

## Remaining Exact Steps

1. Commit the clean exact candidate.
2. Publish the branch and PR through the governed entrypoint.
3. Wait for exact-head required CI before any merge decision.

Deployment, database rebuild and production data migration are outside this
batch.
