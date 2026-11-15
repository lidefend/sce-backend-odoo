# Frontend startup performance and M-01

## Stage identity

- Baseline: `70d01d8fa52c76dc3a296f0431e39be79b98dab5`
- Branch: `fix/frontend-performance-m01-20261116`
- Status: active

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
| `verify.frontend.startup_performance.unit` | passed, 25 cases |
| `verify.frontend.dev_acceptance_remediation.unit` | passed, 20 cases |
| `verify.frontend.workspace_scenario_lifecycle.unit` | passed |
| strict frontend typecheck | passed |
| frontend lint | passed with existing warnings, 0 errors |
| `make local.dev.frontend` | passed; route shell 2.54 KB, form page 852.60 KB |

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
