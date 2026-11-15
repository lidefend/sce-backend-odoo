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
| `verify.frontend.startup_performance.unit` | passed, 22 cases |
| `verify.frontend.dev_acceptance_remediation.unit` | passed, 19 cases |
| `verify.frontend.workspace_scenario_lifecycle.unit` | passed |
| strict frontend typecheck | passed |
| frontend lint | passed with existing warnings, 0 errors |
| `make local.dev.frontend` | passed; route shell 2.78 KB, form page 852.60 KB |

Runtime marker observation and the M-01 browser rerun remain pending.

## Rollback

Revert this branch's frontend, test, and measurement changes. No schema, fixture,
permission, or persisted business data migration is introduced.
