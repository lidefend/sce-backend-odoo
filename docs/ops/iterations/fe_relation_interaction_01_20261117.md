# FE relation interaction 01 (2026-11-17)

## Boundary

- Formal Product Layer: P0
- Layer Target: generic Contract V2 relation/action interaction plus P0 conditional-delivery and assembled-cache revalidation
- Module: `frontend/apps/web`, `addons/smart_core`
- Standard vs User-Specific: platform standard

The backend child-onchange contract already declares `patch`, `modifiers_patch`, `line_patches` and `warnings`. The current relationship loader rejects any modifier or warning effect, making a valid row interaction fail before the shared one2many runtime can consume it.

This batch keeps the declaration authority unchanged. It moves declared child modifiers into the row modifier overlay, surfaces child warnings through the existing row hint presentation, and continues to reject line patches that require nested one2many execution not implemented by this runtime.

## Exclusions

- no backend schema, model, action or business-rule change; the owner-authorized
  `smart_core` work is limited to generic Contract V2 transport and cache behavior;
- no model-specific branches for project, contract, payment or another industry form;
- no new component system;
- no claim of nested child line-patch support;
- no runtime deployment or L4 acceptance in this source batch.

## Initial defect

`loadOne2manyCreateDefaults()` and `loadOne2manyRowChange()` currently throw `尚未接入` whenever the server response contains modifiers or warnings. Those responses are already normalized and declared; the failure is therefore a frontend consumption defect.

Browser suites `list_surface_structure` and `relation_roundtrip` are moved to deployment-stage evidence, matching the existing `frontend_presentation` boundary. Merge-stage checks continue to require frontend contract and behavior tests, while actual deployed user outcomes remain final acceptance evidence.

## Verification

All checks below passed on the pre-commit dirty scope:

| Check | Result |
| --- | --- |
| `verify.frontend.create_default_hydration.unit` | PASS; 55 base cases plus child modifier/warning and invalid-envelope cases |
| `verify.frontend.professional_relation_lifecycle.unit` | PASS; relation lifecycle and 7 Python guard tests |
| `verify.frontend.professional_relation_field.unit` | PASS; relation field, option limit and column authority checks |
| `verify.frontend.presentation.lane.unit` | PASS; 7 + 74 tests |
| `verify.validation.delivery.unit` | PASS; 92 tests |
| `ci.delivery.freeze.prepare` | PASS after regenerated component-driver inventory |
| `ci.local.iteration` | PASS; 10 affected frontend targets including lint, strict TypeScript and component-driver inventory |

The source batch does not claim deployed browser acceptance or real contract/payment user journeys. Those remain deployment-stage evidence.

## Second slice: shared denied-action reason interaction

The action bar already exposes denied reasons through a focusable trigger, click popover, keyboard activation, accessible name and zero action dispatch. Canonical inline body actions only placed `reasonCode` into `title`.

`ActionReasonTrigger.vue` now owns that interaction for both header and body actions. `CanonicalActionBar.vue` and `CanonicalFormNodeRenderer.vue` pass their declared `reasonMessage` fallback through the same wrapper. The node renderer therefore consumes the same declared reason and interaction mechanics without model-specific logic.

Verification for this slice:

| Check | Result |
| --- | --- |
| `verify.frontend.node_component.component` | PASS; 49 consumption checks, 66 SSR checks, embedded Widget browser checks and mounted weighted-relation checks |
| `verify.frontend.professional_workflow.unit` | PASS; 11 tests and 45 real-component browser assertions across 1440/390 |
| `ci.delivery.freeze.prepare` | PASS after regenerated frontend inventories |

The browser assertions cover mouse, Enter, Space, focus visibility and zero dispatch for denied actions. Full business-page acceptance remains a deployment-stage concern.

## Third slice: one create-contract cache authority

The generic runtime already declares snapshot-only local reuse: `snapshot` may reuse, while `etag` requires server revalidation and `none` forbids reuse. The create-form client still treated `etag` as reusable for 30 seconds, creating a second cache policy.

`loadModelContractV2()` now calls the existing `permitsContractV2SnapshotReuse()` authority. Only a create contract explicitly declaring `snapshot` enters `createContractCache`; `etag` and `none` always perform the real contract load. No fake conditional-request capability or TTL-based revalidation is introduced.

Verification:

| Check | Result |
| --- | --- |
| `verify.frontend.contract_v2_runtime_policy.unit` | PASS; cache-policy and client-source parity checks |
| `ci.local.iteration` | PASS; 11 affected frontend targets including strict TypeScript |

## Fourth slice: one action execution identity across presentation surfaces

The form runtime previously carried only a generic `busyKind`. A save could be
identified as loading, but an executing business action had no stable frontend
identity that header, body and overflow presentations could consume together.

The frontend now stores the declared action identity while its request owns the
busy state. `actionInteractionState.ts` resolves loading and disabled from that
one identity. Canonical header/body actions, native form buttons, smart actions,
scene buttons and dropdown items all consume the same result. A stale request
cannot clear a newer action's loading state, and an executing action cannot
dispatch a second business request.

This remains ephemeral frontend interaction state. It introduces no contract
field, backend behavior, model branch, industry rule or second component system.

Verification:

| Check | Result |
| --- | --- |
| `verify.frontend.professional_workflow.unit` | PASS; 19 model cases, 4 keyboard cases, 12 Python guard tests and 61 real-browser assertions across 1440/390 |
| `verify.frontend.node_component.component` | PASS; 49 consumption checks, 73 SSR checks, embedded Widget browser checks and mounted relation checks |
| `verify.frontend.native_form_action_presentation.unit` | PASS; 15 guard tests |
| `verify.frontend.primitive_adapter.unit` | PASS; 46 component contracts, 11 event cases and 41 Python tests |
| `verify.frontend.form_header_action_primitives.unit` | PASS; 9 tests |
| `verify.frontend.typecheck.strict` | PASS |
| `verify.frontend.lint` | PASS; full app and package lint, zero errors |
| `verify.frontend.native_action_contract_consumption.unit` | PASS; 7 cases |
| `verify.frontend.adopted_form_validation_identity.unit` | PASS; 98 shipped save-chain cases, including action identity cleanup and stale-finally isolation |
| `verify.docs.links` | PASS; wired 5 link-tool tests plus repository link audit |
| `verify.guard.registry` | PASS; 1633 scripts, 168/168 unwired dispositions and 18/18 required gates enforced |
| `ci.delivery.freeze.prepare` | PASS; generated component-driver inventory and content-bound evidence refreshed |
| `ci.local.iteration` | PASS; 20 affected targets, including lint, strict TypeScript, approval closure, presenter parity, local ORM and professional workflow |

The native-form guard still looked for the declared anchor inside
`NativeFormTreeRenderer`, although the anchor had already moved to the shared
`NativeNodeComponent`. That was classified as a validation-tool defect and the
guard now follows the existing shared component while preserving the
anchor-navigation-only negative cases.

The frontend incremental planner also lacked a route from those native-action
guard files to their owning target. The rule was added so a future change cannot
fall through as an unmapped frontend path; no product behavior was compensated
in the planner.

The previous candidate's remote full lint exposed an unrelated but real test
typing defect in `native_action_contract_consumption_test.ts`: three mutation
callbacks used `any`. They now use `unknown` plus an explicit checked shape
cast, preserving the same mutation assertions while satisfying the repository
lint policy.

The remote professional gate also exposed that `test_docs_links.py` was present
but not wired. `verify.docs.links` now executes those five focused tests before
the repository link audit, so the registry guard has an actual enforcing
target instead of a documentation-only disposition.

A surface change during validation now clears both the generic save busy kind
and its `form.save` action identity. The shipped save-chain test verifies that a
superseded save cannot erase the newer save's identity and that leaving the
surface does not retain a stale action marker.

## CI remediation: conditional Contract V2 revalidation

The candidate release gate measured `form_open` at 2091 ms against the governed
1600 ms median budget after the create-contract change stopped treating `etag`
as a local TTL cache. Restoring the removed TTL behavior would violate the
declared cache policy, while allowing the performance failure would make the
candidate non-mergeable.

`ui.contract.v2` now compares a request's `If-None-Match` validator with the
delivered contract ETag and returns a bodyless 304 on equality. The frontend
keeps the existing ETag validator in its create-contract cache, sends the
conditional request, and restores the cached decoded snapshot only after the
server confirms it is current. A changed contract, a missing validator, or
`cachePolicy: none` still produces the existing full delivery.

This is a P0 delivery-transport mechanism and introduces no model, business
contract, action, permission or industry behavior. The runtime protocol guard
was also changed to parse named imports instead of matching one formatting of a
multi-line `runtimeStateApplier` import. The side-effect regression guard now
recognizes the shared `beginFormRuntimeBusy` / `endFormRuntimeBusy` applier
mechanism for save and action transaction owners while still rejecting direct
`busyKind.value` writes. Its falsification test now mutates the applier-based
release so the same finally-block ownership boundary remains proven.

Because the handler code changed, the assembled-contract cache version advanced
from `v84` to `v89` and its complete input digest was re-pinned. This prevents a
process that upgrades the code from serving a contract assembled under the
previous handler.

The first clean performance probe showed that returning 304 after rebuilding
the create contract does not reduce assembly latency; `form_open` rose to
2507 ms. Record-free create requests now also use the assembled-contract cache,
but through the isolated deep-copy read rather than the loaned shared read used
by list/edit requests. The cache identity continues to include the semantic
request parameters, acting user/groups, company, allowed companies, locale,
context epoch and source token (native views, fields, action, menu, ACL/rule,
configuration versions and code fingerprint). A create request therefore cannot
cross a role, company or configuration boundary, and sealing still runs on its
own copied contract before ETag comparison. Component-bearing create contracts
enter the hit only after the cached final nodes and component capabilities have
been validated against the current request; record-bound and non-create
component contracts retain their prior assembly path.

The handler computes a bounded SHA-256 identity from the live create
`default_get` values, including many2one identity/display/write date, and adds
that identity to the projection cache key. A create hit is therefore possible
only when the current default facts exactly match the cached assembly; any
default, relation, route context or configuration change selects a different
entry and rebuilds. Without that fingerprint, create remains a dynamic request.
Create hot reads may use the shared read-only source graph because their cache
key includes that exact defaults identity and the returned contract is copied
before sealing; all response-sensitive state remains request-scoped.

The release performance probe now records bounded form-open request diagnostics:
intent, operation, model, render profile, conditional-request presence, HTTP
status and duration. It stores no response body or business values. This is
diagnostic evidence for locating the remaining latency; it does not change the
performance budgets or accepted outcomes.

Verification for this source slice:

| Check | Result |
| --- | --- |
| `verify.frontend.contract_v2_runtime_policy.unit` | PASS; 23 cache-policy and source-parity assertions |
| `verify.node_component_validation.unit` | PASS; 268 tests, including matching and non-matching `If-None-Match` |
| `verify.contract.entry_equivalence.guard` | PASS; one shared fetch/decode authority remains |
| `verify.contract.architecture.suite` | PASS; 1781 tests |
| `verify.frontend.standard_preview.unit` | PASS; 139 tests |
| `verify.unified_page_contract.v2.assembler` | PASS; cache version and full input digest are current |
| `ci.local.iteration` | PASS; 26 affected targets executed with non-zero collection |
| `ci.delivery.freeze.prepare` | PASS; generated content-bound evidence is current |

The governed release performance probe and remote exact-head CI remain pending;
no deployment or user acceptance is claimed here.

## Runtime ETag fast path for exact assembled identities

Returning 304 after rebuilding and sealing the create contract still paid almost
all of the hot-path cost. The cache now records the delivered runtime ETag beside
the assembled contract. On a later request it can answer a bodyless 304 before
copying validation graphs, sealing or trimming only when all of the following
still match:

- the projection cache key and source token;
- source type, cache version, client type, delivery profile and limit parameters;
- the client `If-None-Match` validator and the ETag recorded for a successful
  delivery of that exact assembled identity.

Record-bound requests are explicitly excluded from this path because their cache
key is intentionally record-independent. A non-fast assembled hit returns the
stored ETag slot by reference, allowing the handler to populate it from the
properly sealed contract after the first full delivery. The outer handler returns
an early 304 directly without running component validation against a null body.

The assembled cache version advanced from `v89` to `v90` and its complete input
digest was re-pinned. This remains P0 delivery transport and cache behavior; it
does not declare or alter any model, field, action, permission, default or
industry rule.

Verification for the fast path:

| Check | Result |
| --- | --- |
| `addons/smart_core/tests/test_load_contract_response_cache.py` | PASS; 56 tests, including exact ETag identity, exclusion, shared-slot and isolation cases |
| `addons/smart_core/tests/test_ui_contract_v2_boundaries.py` | PASS; 178 tests, including bodyless 304 handling |
| `verify.node_component_validation.unit` | PASS; 273 tests |
| `verify.frontend.contract_v2_runtime_policy.unit` | PASS; create cache policy and source parity |
| `verify.contract.entry_equivalence.guard` | PASS; 10 tests and one shared request/decode authority |
| `verify.contract.architecture.suite` | PASS; 1781 tests |
| `verify.unified_page_contract.v2.assembler` | PASS; `v90`, sources=4, input digest `5dc7827d0c827f95a4db4d3de9323e56d4594ee5b6696764ddd9f26185ee2342` |
| `verify.frontend.standard_preview.unit` | PASS; 139 tests |
| `ci.local.iteration` | PASS; 27 affected targets executed with non-zero collection |
| `ci.delivery.freeze.prepare` | PASS; generated content-bound evidence is current |

The governed performance probe and exact-head publication remain pending. No
clean identity or delivery result is claimed before those checks complete.
