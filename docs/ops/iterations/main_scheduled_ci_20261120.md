# Mainline and scheduled CI recovery

Base: d2fb27530f5c1bf56719660af64199c6b343d8ff. Branch: fix/main-scheduled-ci-20261120.

Formal Product Layer: P4. Layer Target: CI regression prerequisites. Modules: acceptance fixture and owning module tests. Standard vs User-Specific: verification mechanism. Why Here: tests must explicitly establish the publication they exercise. Why Not Elsewhere: runtime must not restore draft fallback. Blast Radius: test and verification carriers only; exclude all preexisting worktrees and persistent runtime data.

| Gate | State | Owner | Reason |
|---|---|---|---|
| Identity | required | exact HEAD and dirty scope | Always |
| Existing affected ORM families | required | local.test.test / acceptance.frontend.fixture_orm | Changed test prerequisites |
| Module baseline | required | local.test.test | Existing families changed; unknown impact fails closed |
| Coverage registry | required | verify.test.coverage.registry | Missing tag |
| Iteration | required | ci.local.iteration | Publication precondition |
| Frontend lint/type/build | excluded | none | No frontend source changes |
| Browser | required, not_run | governed frontend release audit | Scheduled missing released payment route |
| Remote gates | required, not_run | exact-head PR and scheduled equivalent | Local tests are not remote success |

Failures: main 44659427467 managed ORM 12 failures/1 error; scheduled 44643045425 missing admin_close_01, scene ORM 2 failures, core ORM 3 errors; scheduled 44645213929 missing released payment navigation. Downstream merge/release gates correctly reject failures.

The primary worktree run is superseded; two other worktrees are clean detached archives. The product worktree remains active; this independent CI recovery is the second active writer.

## Expanded owning layer

P0 smart_core DeliveryEngine: native route discovery lost primary actions because build_route_authority received no navigation. Supply the native ACL/action-group and role-filtered tree, preserving product metadata separately. No industry/menu special case. P0 baseline and affected scene/acceptance consumers required. P1/P2/P3 runtime unchanged.

Industry baseline passed 566 tests; initial focused family passed 23; publication unit passed 41; coverage registry passed. Source inputs unchanged since industry baseline except this result metadata. Acceptance attempt failed on missing schema column, not a valid candidate result. Upgrade required before retry.

Acceptance target: registered local profile, sc-fe-r2-p1-01, sc_frontend_acceptance, exact filter ^sc_frontend_acceptance$, filestore sc_fe_r2_p1_01_odoo; isolated synthetic acceptance tenant, not customer production/control/catalog. Use governed writer leases and restoration. No other database authorized.

Scene baseline passed 10 tests. Platform CI selectors sc_smoke/smart_core,sc_gate/smart_core passed 17 tests. Static consumer checks passed 501 tests. Additional affected ORM targets passed; original logs are under .runtime/ci-recovery/affected-orm.log.

The additional exhaustive standalone smart_core diagnostic failed (29 failures, 75 errors of 460): its carrier lacks industry models and HTTP namespace configuration. It is not claimed as a passed baseline. This is separate from the actual CI-selector result above; no assertion or gate was removed.

The acceptance module upgrade consumes sealed artifact 0572684a5b732f6cce3e4748161212547c066894. Subsequent changes only relocate a test helper and correct task metadata, with no database/schema or runtime-code changes. Rebuild the acceptance service artifact at the resulting clean HEAD before the fixture rerun.
