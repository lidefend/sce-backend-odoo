# Enterprise initialization route authority — 2026-11-28

Branch: `fix/enterprise-initialization-route-authority-20261128`

Baseline: `0d17e91e7190e1a293e4e6ac969c39738a87218f` (`origin/main`)

## Layer declaration

| Field | Value |
| --- | --- |
| Formal Product Layer | P1 |
| Layer Target | construction scene lifecycle authority at enterprise initialization |
| Modules | `smart_construction_scene`, `smart_construction_core` |
| Standard vs User-Specific | construction standard |
| Why Here | The native initialization route exists, but P1 removes it as if it were an ordinary unselected business scenario. |
| Why Not Elsewhere | P0 already publishes native facts; the frontend must still fail closed; P3 is not a repair carrier. |
| Blast Radius | Exact initialization menu/action only; ordinary scene selection, role authority, ACL and runtime execution remain unchanged. |

## Problem

An enterprise configuration administrator can receive the native enterprise-initialization
menu/action from P0, but the P1 scene filter classifies it against an unselected business
scenario and removes it before `system.init`. The remaining configuration page asks the
administrator to select a business page even though initialization has not happened.

## Validation responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| Exact base/head identity | required | branch and full SHA preflight | always |
| Focused lifecycle unit | required | `test_tenant_scene_activation.py` | exact P1 filter behavior |
| Existing affected ORM family | required | `test_company_route_scope_cache.py` | end-to-end effective authority |
| Owning module baseline | deferred remote | scene module baseline | production P1 authority change |
| Runtime/browser journey | required after source checks | governed clean runtime | user-visible initialization |
| Remote PR and scheduled mainline | required | exact-head PR CI and main full release | independent integration |

## Progress

Source tracing established one root cause: the scene filter already preserves menu-less
internal initialization actions, but not the exact native initialization menu/action
published before business-scene selection.

## Local implementation result

- The P1 scene filter now preserves an already native-authorized row only when its
  source is a known producer and its menu/action identity exactly matches the
  declared `enterprise_initialization` entry.
- Ordinary business rows under the same disabled scenario remain denied.
- Client-declared scope, mismatched identities and denied rows remain fail-closed.
- The solution reads authorization already published by the native menu/action
  layer. It adds no group, ACL, record rule or frontend special case.

## Local evidence

| Check | Result | Evidence |
| --- | --- | --- |
| `verify.admin_close_01.backend.unit` | PASS, 170 tests | `.runtime/enterprise-initialization-route-authority/focused-unit-no-permission-change.log` |
| `verify.scene.company_route_scope_cache.orm` | PASS, 11 tests | `.runtime/enterprise-initialization-route-authority/company-route-scope-no-permission-change.log` |
| `verify.enterprise.initialization.journey.orm` | PASS, 2 tests | `.runtime/enterprise-initialization-route-authority/enterprise-initialization-journey.log` |
| `ci.local.backend.iteration` | PASS, 200 selected tests | `.runtime/enterprise-initialization-route-authority/ci-local-backend-iteration.log` |

The 11-test ORM run used the worktree-scoped template
`sc_test_template__smart_construction_scene`, a fresh attempt database and the
authoritative local-test receipt. The full module baseline remains deferred to
the exact-head remote integration lane.
