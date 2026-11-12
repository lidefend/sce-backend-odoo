# Final Scene Shell Delivery

## Objective

Ensure every executable final-navigation entry reaches the user through
`/s/{scene_key}` while preserving the content boundary:

- designed business targets use their explicit scene contract;
- ordinary action pages use a generated `native_delegate` scene shell.

## Responsibility Boundary

- Odoo owns native menu/action/view/model/ACL facts.
- `smart_core` compiles the final scene path and generated scene shell.
- Scene composition owns designed product outcomes.
- Native delegate shells preserve the original action as page content.
- Frontend consumes the scene route and embeds the declared native content.

## Acceptance

- Every executable final navigation leaf has a `/s/...` route.
- Directories have no published path.
- `my_work.workspace` remains a designed scene.
- One ordinary action page is reachable through a generated native-delegate scene.

## Status

Local mechanism validation passed.

- `verify.scene.shell_compiler.unit`: 6 tests passed.
- `verify.navigation_contract_compiler.unit`: 5 tests passed.
- `verify.backend.navigation_delivery.unit`: 55 core tests passed, with all nested compiler/catalog/shell suites passing.
- `verify.frontend.scene_shell_contract.unit`: the scene registry consumes a generated native-delegate row and resolves its native action target.
- `TestIntentSmoke`: 10 tests passed in the isolated Odoo test database. Every executable startup leaf used `/s/...` and declared `designed_scene` or `native_delegate`.
- `ci.local.iteration`: 12 affected targets passed.

The first managed browser run correctly rejected a stale acceptance-tool
assumption: the list probe still searched for the native `/a/...` route after
the final contract moved the same entry to `/s/...`. The probe now keeps the
native action route only as an identity alias for locating the capability while
navigating through the delivered scene route. Its contract lock passes 23 tests;
the rerun of `ci.local.iteration` executes 12 affected targets with no unmapped
paths.

The next managed browser run reached the sceneized payment-request route and then
failed with a `400` response for `ui.contract`. Backend logs showed the request
carried only company/context and no action identity. The generated shell target
had incorrectly declared `entry_intent=ui.contract`, which made `SceneView`
choose the scene-block contract path instead of embedding the native action.
Native-delegate targets now carry only route/action/menu/model/view mode; action
identity drives the embedded `ActionView`, while only designed scenes may carry
scene entry intent.

The next browser run proved the sceneized list rendered and completed its
18-state structure matrix. It then stopped before the record walk because the
P4 probe parsed the action id from `/s/entry...` rather than the node's retained
`nativeRoute=/a/881?menu_id=560` identity. Both profile and record paths now use
one native-identity resolver and fail explicitly when a scene target omits it.

The following run passed the 1440 record contract, approved binding and renderer,
and the screenshot showed the source list restored. It failed only because the
probe required byte-identical query text while the router canonicalizes the
scene route with scene/action identity. Return checks now require the same scene
path and source menu identity, plus matching action identity when present.
The same run also exposed an 18-minute Playwright teardown hang after the
assertion; context, browser and lease cleanup now have bounded waits.

The candidate still requires freeze preparation, clean commit, exact acceptance
runtime preparation and user-flow verification. No deployment or product
acceptance is claimed.

## Designed-scene behavior closure

PR #873 integrated the scene shell compiler and validated the ordinary
`native_delegate` list/detail path. The remaining goal condition is one
designed-scene browser proof.

The existing My Work approval acceptance now resolves
`smart_construction_core.menu_sc_my_work` from final `system.init`, requiring:

- `scene_key=my_work.workspace`;
- `content_kind=designed_scene`;
- route path `/s/my_work.workspace`;
- the product `MyWorkView` renderer marker;
- no `ActionView` in the rendered designed scene.

This changes only P4 acceptance consumption. It does not add or maintain native
menu/action facts and does not alter the scene or product contract.

The former dead-surface disposition for
`verify.frontend.my_work_approval.guard` was removed after its exact path mapping
made the target live in `ci.local.iteration`; the reason is recorded in the
disposition audit trail.

The first designed-scene browser run found a product publication defect before
rendering: the native My Work menu was visible and ACL-authorized, but the
persisted `construction.standard` policy and active release snapshot each had
91 entries while the shipped P1 contract has 92. `menu_sc_my_work` was the
missing entry.

Migration `17.0.0.182` now performs an add-only policy reconciliation and then
freezes and releases a new snapshot from the reconciled policy. Existing policy
rows and administrator edits are preserved; the migration only adds a formal
entry absent from the maintained policy. The exact ORM test verifies that the
newly active snapshot contains the native My Work menu/action pair.

The governed acceptance database was upgraded to `17.0.0.182` on
`04aa7bd642b44c75e8a08920a72241e354e8ea6e`. Readback then showed:

- `construction.standard` policy: 92 menus;
- active release snapshot 53: 92 pages;
- My Work: `release_state=released`, `published_in_runtime_nav=true`.

The My Work browser acceptance passed through the final contract:
`my_work.workspace` arrived as `designed_scene` at
`/s/my_work.workspace`, the MyWorkView renderer was present, and ActionView was
absent. The test also passed counts/detail/submission, company A-B-A scope,
reviewer approval and readback, reject-reason safety, project-member isolation,
and 1440/1280/390 responsive views. This closes the batch's behavioral
acceptance; it does not deploy the candidate or claim user acceptance.

Generated tracked reports no longer require manual insertion into each run's
scope. `generated_evidence_paths.py` is the single canonical ownership list used
by both run resolution and branch synchronization. Generated changes are
reported as `derived_scope`; unlisted or unowned files still make the run
`reconcile` and fail closed.
