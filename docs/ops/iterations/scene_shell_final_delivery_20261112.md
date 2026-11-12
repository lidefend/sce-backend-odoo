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

The candidate still requires freeze preparation, clean commit, exact acceptance
runtime preparation and user-flow verification. No deployment or product
acceptance is claimed.
