# Daily published-face merged entry identity

Status: verification_pending

The second daily release attempt reached published-face convergence at
`c4e2061fa284c6402b0c49e38c056d90080e29db`. The prior mixed action/scene
target failure was gone, and both runtime-version endpoints already returned the
new source revision.

The release gate then reported two released native entries missing from the
delivered navigation:

- `smart_construction_core.menu_sc_comprehensive_cost_statistics_report`
- `smart_construction_core.menu_sc_p1_project_budget`

Read-only runtime evidence showed that both menus are active, visible to the
`demo_full` principal, present in both maintained product policies, and present
in both newly frozen release snapshots. They disappeared only when
`MenuService._merge_explicit_entry_with_directory()` merged each executable leaf
into its same-label policy directory: the merge retained menu/action IDs and the
route, but not `menu_xmlid`.

The P0 fix carries `menu_xmlid` and `menu_key` onto the merged directory. No
business menu, policy row, ACL, release snapshot or frontend behavior is changed.

The owner explicitly selected a direct daily-development hotfix lane; mainline
integration is deferred.

Validation at the P0/P4 dirty candidate:

- `verify.backend.navigation_delivery.unit`: 63 tests, PASS.
- `verify.frontend.dev.incremental.unit`: 95 tests, PASS.
- `verify.agent.resume.unit`: 56 tests, PASS.
- `verify.agent.ledger.unit`: 18 tests plus ledger guard, PASS.
- `make ci.local.iteration`: four required targets executed, PASS.
