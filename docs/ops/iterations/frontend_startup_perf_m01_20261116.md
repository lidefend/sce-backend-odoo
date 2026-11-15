# Frontend startup performance and M-01

## Stage identity

- Baseline: `70d01d8fa52c76dc3a296f0431e39be79b98dab5`
- Branch: `fix/frontend-performance-m01-20261116`
- Status: independent review approved; extended-main sync unblocker applied

## Objective and layer

Formal Product Layer: P0 generic frontend runtime and presentation; P4 bounded
performance verification.

Layer Target: canonical startup timing marks, the record route loading boundary,
and declared scene-title consumption.

Module: `frontend/apps/web`, `scripts/verify`, and the registered frontend test
entrypoints.

Standard vs User-Specific: platform engineering standard.

Why Here / Why Not Elsewhere: startup marks and route loading are generic runtime
mechanisms. Department-management titles must consume scene and route declarations
already supplied by the backend; a frontend title dictionary would create a second
product fact. Backend contracts, permissions, data, and customer configuration are
outside this batch.

Blast Radius: document boot, session readiness, record skeleton, record contract
load, record-ready state, the record route chunk boundary, and affected activity
titles. No schema, ACL, fixture, or persisted data migration is introduced.

## Acceptance

| Finding | Acceptance |
| --- | --- |
| Startup measurements disagree on FCP | one canonical marker order is emitted and consumed by probes |
| Record readiness remains 6-10s | identify API, asset, and client-processing costs; split the route shell from the heavy form |
| M-01 technical labels remain | affected entries show declared business labels |

## Exclusions

- backend contract, schema, permission, or data changes;
- customer-specific title dictionaries;
- deployment or external runtime mutation;
- unrelated routes, full user acceptance, PR, or merge.

## Results

Canonical code marks now cover document boot, record skeleton, session bootstrap,
record contract load, and record readiness. The record route shell is statically
small and imports `ContractFormPage.vue` dynamically after rendering the loading
surface. Record deep links skip the eager `workspace_home` section of
`system.init`; the home route still requests it at startup.

Technical action authorities and scene keys are rejected as business titles.
The title resolver now falls through to declared scene, action, menu, or generic
labels instead of exposing dotted technical identities.

| Check | Result |
| --- | --- |
| `verify.frontend.startup_performance.unit` | passed, 55 cases |
| `verify.frontend.dev_acceptance_remediation.unit` | passed, 20 cases |
| `verify.frontend.workspace_scenario_lifecycle.unit` | passed, 11 affected scenarios |
| `verify.frontend.component_driver_takeover.unit` | passed, 18 cases |
| `verify.frontend.contract_basis.unit` | passed, 15 cases |
| strict frontend typecheck | passed |
| frontend lint | passed with existing warnings, 0 errors |
| `make local.dev.frontend` | passed; route shell 3.35 KB, form page 852.72 KB |

### Independent review remediation

The first independent review requested changes on two S1 findings:

- Record deep links skipped `workspace_home`; returning to the home route in the
  same SPA did not backfill the section. Home loading now awaits
  `loadWorkspaceHomeOnDemand()`, and the actual store/consumer lifecycle test
  proves one backfill request is issued.
- `record_ready` was emitted before the Vue DOM patch and could also be emitted
  for a missing record. It now requires current route identity, a loaded
  contract, successful page status, a non-missing record, and completion of
  `nextTick()`.

The related S2 asset-loading recovery is now bounded: the record route shell
uses a registered 15-second transport deadline, ignores obsolete loads after
route leave/unmount, shows an explicit error instead of an indefinite skeleton,
and offers a document-level reload after failure. Existing permission, save,
validation, and return components are unchanged.

The performance browser probe now requires served build identity, original
resource hash/size for the entry, record-route and heavy-form bundles, and all
canonical marks. The local wrapper derives `DEV_ACCEPTANCE_EXPECTED_BUILD_SHA`
from a clean exact HEAD and rejects a dirty tree before collecting record
identity evidence.

Failure classification during remediation:

- `component_driver_takeover` initially failed because the committed generated
  inventory digest was stale after source edits (`baseline_evidence_defect`).
  The registered generator refreshed only `inputDigest`; the target then passed.
- strict TypeScript initially rejected the browser timer return type
  (`product_defect`). The explicit browser `number | null` type fixed the
  owning source; typecheck and the complete affected iteration then passed.

The governed incremental execution executed 28 targets with no blocked or
not-run targets on runtime tree `44b7cac40a1bcf9912b3143cc8083ab757b8b28fef924ef397cb5efb3fcc5c62`.
The clean candidate then reused that content-identical execution:

- executed source receipt:
  `.runtime/frontend-dev-validation/executions/20261115T233225Z-2458902-922945683/receipt.json`
- clean reused receipt:
  `.runtime/frontend-dev-validation/executions/20261115T233710Z-2519118-210689907/receipt.json`

Not yet covered: a fresh independent review of the fixed candidate, exact-head
remote CI, isolated daily-clone deployment, and desktop/mobile A/B. The prior
static-proxy timing report remains diagnostic only and is not exact-candidate
deployment evidence.

### Second independent review remediation

A fresh exact-head review found two remaining blockers:

- Cancelling a pending chunk load on route leave could strand the cached record
  page because `KeepAlive` reactivation did not restart the discarded load.
- Browser identity evidence still allowed a pass when build-info, bundle lists
  or bundle hashes were absent.

The route shell now delegates to a P0 route loader that distinguishes current,
cancelled and failed generations. `onDeactivated` invalidates only after an
actual cached-page deactivation, so a failed or aborted navigation does not
cancel the active load. `onActivated` restarts loading only when the retained
instance has no page and no recoverable error. The regression covers a delayed
import, deactivation/reactivation, a failed-navigation-style uninterrupted load,
a second import on reactivation, stale-result rejection, timeout failure and
in-flight deduplication.

Record identity validation now fails closed unless all of the following exist:

- a 40-character expected build SHA;
- served `build-info.json` with the same SHA;
- entry, `ContractFormRoute` and `ContractFormPage` bundle resources;
- a non-empty decoded size and SHA-256 for each required bundle.

The acceptance wrapper also rejects dirty worktrees and derives the expected SHA
from the clean candidate HEAD. These checks share one pure validator exercised
through the existing startup performance target, so the verification lane did
not grow a new remote-only script.

Another independent exact-head review and browser observation remain pending.

### Extended-main sync P4 unblocker

The reviewed candidate's first full Quick reached 7/8 passing shards, then
failed only because current `origin/main` contains public GitLab pipeline run and
job identifiers in an audit document that match the mobile-phone pattern. The
identifiers are execution metadata, not personal data.

Three exact immutable blobs are now registered in
`scripts/ci/personal_data_false_positives.json`; no directory, path wildcard or
scan-rule exemption was introduced:

- `60f6a78813ff1d692afd5cf116eb372ae06a427a`
- `6fc5fa3ff96f8037bedfac207cb5fd28be68a360`
- `8fbde449f96c090b175b66a32681b3c8c883019d`

The targeted personal-data scan passed with zero confirmed matches and 40 exact
suppressions. The full clean-history scan passed all governed scan members over
34,780 blobs. This is P4 publication unblocking only; it does not change the
frontend product behavior reviewed above.

### Runtime marker observation

The clean candidate frontend was served through the governed 5176 static proxy
against the existing `local.dev` API. A project record was used because that
surface is available in the local data and exercises the same generic record
runtime; the daily payment record remains the final deployment check.

| Canonical mark | Since boot |
| --- | ---: |
| `boot_start` | 0 ms |
| `session_ready` | 1347 ms |
| `skeleton_shown` | 1420 ms |
| `contract_loaded` | 2512 ms |
| `record_ready` | 3559 ms |

First contentful paint was 1004 ms; record readiness is now measured from
`record_ready`, not from a DOM selector. `session_ready` legitimately precedes
the record skeleton because the router guard waits for session bootstrap before
the record route boundary mounts.

The route shell and skeleton were requested at 1368-1392 ms. The heavy
`ContractFormPage` chunk request began at 1467 ms, after the skeleton was
available, proving that the route shell is no longer blocked by the 852.60 KB
form chunk.

On the record route, `system.init` requested no optional sections and excluded
`workspace_home`. Its response fell from 460681 bytes before the request cleanup
to 427806 bytes, a reduction of 32875 bytes (7.1%). The record contract remains
the dominant payload at 1548788 bytes and 905 ms; API payload reduction there is
the next measured target.

M-01 is closed at the shared title-consumption layer by unit coverage, including
a technical action/scene identity falling through to “部门管理”. A target-daily
browser rerun remains required after deployment because the local development
data exposes only one scenario center and does not contain the affected entries.

## Rollback

Revert this branch's frontend, test, and measurement changes. No schema, fixture,
permission, or persisted business data migration is introduced.
