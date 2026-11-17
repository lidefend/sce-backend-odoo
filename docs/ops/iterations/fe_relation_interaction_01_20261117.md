# FE relation interaction 01 (2026-11-17)

## Boundary

- Formal Product Layer: P0
- Layer Target: generic Contract V2 one2many child initialization and row-onchange consumption
- Module: `frontend/apps/web`
- Standard vs User-Specific: platform standard

The backend child-onchange contract already declares `patch`, `modifiers_patch`, `line_patches` and `warnings`. The current relationship loader rejects any modifier or warning effect, making a valid row interaction fail before the shared one2many runtime can consume it.

This batch keeps the declaration authority unchanged. It moves declared child modifiers into the row modifier overlay, surfaces child warnings through the existing row hint presentation, and continues to reject line patches that require nested one2many execution not implemented by this runtime.

## Exclusions

- no backend schema, model, action or business-rule change;
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
