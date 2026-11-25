# P1 Role Capability Authority 2026-11-26

## Ownership

- Formal Product Layer: P1 construction industry standard product
- Layer Target: construction role, capability and entry-visibility authority graph
- Module: `smart_construction_core`
- Standard vs User-Specific: construction industry standard
- Why Here: the faulty role-to-entry edges are standard P1 security declarations.
- Why Not Elsewhere: P2/P3 cannot repair standard permission semantics, P4 must remain evidence tooling, and P0 must not acquire construction role names.
- Blast Radius: role groups, 14 generic entry carriers, 68 cross-domain menu rebindings, role-surface guards and affected role tests.
- Exclusions: no frontend, no business model/ACL/state changes, no customer preference, and no persistent database migration before separate confirmation.

## Finding

Thirteen role identity groups currently imply `group_sc_entry_pXX` directly.
That bypasses the approved chain:

```text
role group -> capability group -> entry visibility carrier -> menu/action
```

The acceptance projection later showed that this direct graph also competes
with per-page `role_authority`, producing 221 authorized-but-unprojected pages
and 31 projected-but-not-authorized pages.

The page-level mismatch was also traceable to 68 rebound menus: their runtime
menu group is `group_sc_entry_pXX`, while the acceptance rows still declared
the superseded domain groups. The acceptance rows are now aligned to the
rebinding fact while action-level capability declarations remain unchanged.

## Decision

Preserve existing effective visibility while correcting ownership:

1. Add one explicit entry-visibility capability for each existing visibility
   carrier.
2. Make each entry-visibility capability imply only its matching carrier.
3. Replace role-to-carrier implications with role-to-capability implications.
4. Explicitly remove the old role-to-carrier edges during module replay.
5. Add a static guard forbidding role groups from directly implying any
   entry/menu/action/native permission group.

This is a graph correction, not a parallel permission engine and not a change
to ACLs, record rules or business actions.

The role exposure declaration was recomputed from the corrected menu authority;
the restricted identity's explicit narrowing set shrank from 42 to 23 pages.

## Verification Responsibility

| Gate | State | Owner target | Reason |
| --- | --- | --- | --- |
| exact base/head identity | required | identity preflight | always |
| owning module baseline coverage | deferred_remote | `verify.smart_construction_core.module_baseline` | P1 permission behavior; exact-head remote CI owns full module coverage |
| existing affected test families | required | changed-test selector and named role tests | role/group graph and role-surface consumers change |
| focused changed tests | required | `verify.role_capability_group_authority.unit` | new invariant |
| contract/schema/consumer | required | fact-layer and role-surface guards | role graph is consumed by role projection |
| frontend lint/type/build | excluded | n/a | no frontend source change |
| runtime/browser journey | deferred | governed local.dev verification | requires separately confirmed module replay/migration |
| remote required gates | required | exact-head PR CI | integration and merge authority |

## Migration Boundary

Source changes are deterministic and include explicit removal commands for the
old edges. No persistent database action is authorized by this record.

Before any module upgrade or ORM execution, create and confirm:

- exact database `sc_dev_demo` or isolated `local.test` attempt;
- module version and replay file;
- expected role/group relation removals and additions;
- authoritative pre/post closure readback;
- backup/restore or transaction rollback method.

Prepared module replay identity:

- module: `smart_construction_core`;
- target version: `17.0.0.187`;
- source data order: entry carriers before capability groups;
- expected role-to-entry direct-edge removals: the historical 13 role groups;
- expected capability additions: 14 per-scope capabilities plus one full-scope capability;
- expected postcondition: every affected role retains exactly the same
  `group_sc_entry_pXX` closure recorded in the focused static test.

## Result

## Source Validation

- `verify.role_capability_group_authority.unit`: PASS, 12 tests; graph direction,
  closure equivalence, load order and 68 acceptance rebindings checked.
- `verify.frontend.business_entry.matrix.universe`: PASS.
- `verify.frontend.role_surface_exposure_declaration.guard`: PASS,
  12 roles / 23 narrowings.
- `verify.role_surface.landing.contract.unit`: PASS, 35 tests.
- `verify.nav01.native_authority.unit`: PASS.
- `verify.frontend.dev.incremental.unit`: PASS, 245 tests.

Source result:

- `sc_entry_groups.xml` now loads before capability groups and is explicitly
  documented as resource-level carriers.
- `sc_capability_groups.xml` adds 14 entry-visibility capabilities and one
  full-scope composition capability.
- `sc_role_entry_groups.xml` removes 13 historical role-to-carrier paths and
  selects the corresponding capabilities instead; all effective role-to-carrier
  closures are unchanged.
- `sc_role_groups.xml` keeps role-identity inheritance while removing direct
  permission carriers.
- `sc_discover_entry_groups.xml` is retired; its removals and the experience
  capability selection live in `sc_role_entry_groups.xml`.
- `menu_entry_group_rebinding.json` remains the single declaration for the 68
  cross-domain menus; the acceptance CSV now consumes the same entry-carrier
  identities in its menu-chain authority.
- The role exposure narrowing declaration was reduced from 42 stale pages to the
  23 pages actually reachable by the restricted role.

## Runtime Validation

Not run. No persistent or isolated test database was upgraded because the
module replay plan above has not received a separate migration confirmation.
