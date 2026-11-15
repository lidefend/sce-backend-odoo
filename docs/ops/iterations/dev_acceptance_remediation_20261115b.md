# DEV-ACCEPTANCE-20261115B remediation

## Stage identity

- Deployment baseline: `f35d981b2a37d6268e31592edeef460c9580240c`
- Implementation branch base: `f35d981b2a37d6268e31592edeef460c9580240c`
- Branch: `fix/dev-acceptance-20261115b-remediation-main`
- Initial worktree: clean
- Status: active

## Objective and layer

Formal Product Layer: P0 platform contract consumption and generic presentation;
P4 bounded runtime diagnosis.

Layer Target: generic Vue action/record runtime and scene page semantics.

Module: `addons/smart_core`, `frontend/apps/web`, `scripts/verify`,
`make/frontend.mk`.

Standard vs User-Specific: platform engineering standard.

Why Here / Why Not Elsewhere: the backend list-preference policy correctly
refuses a caller-supplied model that disagrees with the action's declared model.
The defect is the frontend consumer forming that scope from a previous list
contract. Relaxing the backend would remove the mismatch detector; adding a
model/menu-specific fallback in P1/P2/P3 would create a second product fact.
Scene tab titles and page headings are generic presentation consumers of the
declared scene/page identity.

Blast Radius: shared list preference reads, activity-tab title projection, the
generic scene page heading, and the bounded acceptance probes for the three
affected lists and one record deep link. Permissions, model fields, business
rules, route authority and persisted business data remain unchanged.

## Findings and acceptance

| Finding | Acceptance |
| --- | --- |
| N-02 rapid list switch returns 400 | cost -> deduction -> equipment switching emits no 400 |
| M-01 technical scene keys appear as tab titles | affected tabs show declared scene labels |
| N-03 six pages have no h1 | each affected page exposes exactly one `h1` |
| M-02/N-01 record deep link takes 14.7s | measure cold request timeline; improve the owning layer or expose honest progress and the remaining bottleneck |

## Exclusions

- W-03 is closed by the owner after screenshot verification.
- W-04 was not reproduced.
- The two navigation leaves that are already on their target page are intentional no-ops.
- The active capability-explorer audit and its retained `sc_dev_demo` decision are not part of this product batch.

## Validation ladder

- L0: exact repository, branch, HEAD and clean/dirty scope.
- L1: focused pure tests, frontend lint/type checks and architecture guards.
- L2: non-zero targeted tests for preference identity, title selection and page semantics.
- L3: only if runtime semantics or served assets change.
- L4: governed `sc-local-dev` / `sc_dev_demo` browser observations for the three list switches, affected headings and record deep link.
- L5: not started; no delivery, PR, merge or deployment claim.

## Results

### N-02 preference request race and duplication

The deployed `f35d981b2` runtime was reproduced through the scenario navigation,
not through full-page URL loads. A rapid `劳务成本登记 -> 劳务扣款明细 ->
机械台班登记` sequence produced three identical failures:

`action_id=639`, `model=sc.labor.deduction`, HTTP 400, backend response
`model 与 action 解析不一致: sc.labor.deduction != sc.equipment.usage`.
The contract request for action 639 then returned and the same preference
request succeeded with `model=sc.equipment.usage`.

Reproduction artifacts:

- `.runtime/dev-acceptance-20261115b-remediation/browser-report.json`
- `.runtime/dev-acceptance-20261115b-remediation/rapid-switch.png`

The candidate fixes the consumer at two generic boundaries:

1. `resolveListColumnPreferenceScope` sends only the current action id when the
   action is known. The backend resolves the action's declared model; a stale
   model projected from the previous page is never paired with the new action.
2. Concurrent identical `user.view.preference.get` requests are coalesced by
   the existing intent transport. The failed response is not cached.

The focused test proves both the action-owned scope and single transport
request. The existing backend mismatch rejection remains unchanged.

### M-01 business tab title

Scene activity tabs now consume runtime scene labels, then registered scene
labels, then a distinct route-carried declared label. Technical scene keys are
no longer preferred over an available business label. No scene-key-to-title
dictionary was added.

### N-03 semantic page heading

`SceneView` now renders one semantic `h1` for a scene page. Surfaces that already
render an explicit handling-surface `h1` do not receive a duplicate.

### M-02/N-01 loading communication

The record form skeleton now displays the loading purpose, elapsed seconds and
an indeterminate progress track, with reduced-motion handling. This makes a
long wait honest and observable; it does not claim that the 14.7-second
deep-link latency has been reduced.

### M-02/N-01 startup profile

The owner deployed candidate `7291d8389a0e904ae07bd3746e02b9ff3dd122b2` to the
daily development server. Five independent local sessions directly opened
`/t/demo/r/payment.request/53?action_id=878&menu_id=559` and all rendered
`PRQ2600050`.

| Run | First visible | Record ready |
| ---: | ---: | ---: |
| 1 | 5.66s | 6.77s |
| 2 | 5.79s | 6.89s |
| 3 | 6.27s | 8.28s |
| 4 | 5.69s | 6.80s |
| 5 | 6.87s | 10.90s |

The median was 5.79s to first visible content and 6.89s to record ready. HTTP,
console and page error counts were zero. A further three instrumented sessions
measured first contentful paint at 3.87s, 5.38s and 6.78s. The dominant path was
the initial `system.init` request, dynamic route assets and the record contract,
not record data: `system.init` took 1.49-1.57s, the action contract 0.64-0.69s,
and `api.data` 0.16-0.18s in those runs.

The document previously contained an empty `#app`, so no visible content could
be painted until Vue, the route chunk and startup state were ready. `index.html`
now carries a document-level boot surface and a delayed state after 15 seconds.
The surface has no business semantics and is replaced when Vue mounts.

### Validation

| Layer | Entry | Result |
| --- | --- | --- |
| L1/L2 | `verify.frontend.dev_acceptance_remediation.unit` | passed, 17 cases |
| L1/L2 | `verify.frontend.intent_request_coalescing.unit` | passed, including duplicate preference coalescing |
| L1/L2 | `verify.frontend.dev.incremental.unit` | passed, 153 tests |
| L1/L2 | `verify.local.dev.runtime.performance.unit` | passed, 34 tests |
| L1/L2 | `verify.action_view_runtime_smoke.behavior` | passed, 3 checks |
| L1/L2 | `make ci.local.iteration` | passed, 16 affected targets |
| Build | `make local.dev.frontend` | passed after the document boot surface change |

Original logs are under
`.runtime/agent-runs/DEV-ACCEPTANCE-20261115B-REMEDIATION/`.

### Runtime follow-up

The five-run profile was captured on `7291d8389`, before the document boot
surface was added. The local build containing the boot surface passes, but it
has not been deployed, so it is not yet evidence that the deployed first-content
paint or 15-second delayed state has changed.

The remaining measured work is:

- deploy the boot-surface candidate and rerun five direct-record sessions;
- compare first-contentful-paint and record-ready tails against the baseline;
- reduce the initial JavaScript and record-contract payload only after a changed
  candidate can be measured against this distribution.

## Rollback

Revert the remediation commits. No schema, fixture, permission or persisted
business-data migration is introduced.
