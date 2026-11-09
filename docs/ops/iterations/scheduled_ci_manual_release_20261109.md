# SCHEDULED-CI-MANUAL-RELEASE-20261109

## Scope

- Formal Product Layer: P4 ops delivery tool.
- Baseline: `9086ddab6cd19b0ee30e6f6dae149c0df83ededd`.
- No product route, ACL, business contract or database changes.

## Failure

The manually dispatched full frontend release gate `42608865956` failed after
runtime navigation and static checks passed.

Two validation-tool defects were confirmed:

1. `verify.frontend.role_release_projection` collected valid identities and a
   matching release snapshot, but the make wrapper hard-coded `NOT_VERIFIED`,
   so the release audit rejected the projection scope.
2. The delivery-hardening performance scenario used manual `history.pushState`
   to open `/my-work`; the current Vue router resolved that synthetic history
   entry back to the role home and `.product-work` never appeared.

## Change

- Mark the role release projection `VERIFIED` after the governed collector and
  snapshot collection succeed.
- Navigate from the rendered role-home “查看全部” action for the My Work timing
  scenario instead of fabricating a browser history entry.

## Validation

| Check | Result |
| --- | --- |
| Delivery hardening guard | PASS, 17 tests |
| Release local entry and release audit | PASS |
| Frontend release unit suite | PASS |
| `ci.local.iteration` | PASS, 5/5 affected targets |
| Exact-head full frontend release gate | Pending after commit |

## Boundary

The role home remains the product landing page. `/my-work` remains available
through its existing governed action. No product behavior is altered.
