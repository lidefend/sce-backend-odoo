# Scene Completion Proof Audit Scan v1

## Goal

Collect bounded candidate evidence for what still blocks a strict repository-wide
statement that scene-oriented convergence is fully complete.

This scan does not classify or conclude. It only records candidates for the next
screen.

## Scope

Bounded verification target:

- `frontend/apps/web/src/router/**`
- `frontend/apps/web/src/views/**`
- `frontend/apps/web/src/pages/**`
- `frontend/apps/web/src/app/**`
- scene-related governance documents produced in the current chain

## Scan Output

The following are raw candidate captures only. This scan does not classify
whether each point is an acceptable orchestrated-scene consumer or a remaining
completion-proof gap.

### Contract Loading Candidates

- `[frontend/apps/web/src/pages/ContractFormPage.vue](../../frontend/apps/web/src/pages/ContractFormPage.vue#L3963)` still loads page contract through `loadActionContractRaw(...)`
- `[frontend/apps/web/src/pages/ContractFormPage.vue](../../frontend/apps/web/src/pages/ContractFormPage.vue#L3981)` still falls back to `loadModelContractRaw(...)`
- `[frontend/apps/web/src/api/contract.ts](../../frontend/apps/web/src/api/contract.ts#L52)` still exposes `op: 'action_open'`
- `[frontend/apps/web/src/api/contract.ts](../../frontend/apps/web/src/api/contract.ts#L91)` still exposes `op: 'model'`

### Action/Model Consumer Candidates

- `[frontend/apps/web/src/views/ActionView.vue](../../frontend/apps/web/src/views/ActionView.vue#L1068)` still derives `actionId` from route param/query
- `[frontend/apps/web/src/views/ActionView.vue](../../frontend/apps/web/src/views/ActionView.vue#L1087)` still resolves `sceneKey` from query or menu inference, meaning action consumer can still anchor from native action context
- `[frontend/apps/web/src/pages/ContractFormPage.vue](../../frontend/apps/web/src/pages/ContractFormPage.vue#L521)` still derives `model` from route param/query plus contract head
- `[frontend/apps/web/src/pages/ContractFormPage.vue](../../frontend/apps/web/src/pages/ContractFormPage.vue#L569)` still derives `recordId` from route param/query

### Startup and Landing Proof Candidates

- `[frontend/apps/web/src/stores/session.ts](../../frontend/apps/web/src/stores/session.ts#L1242)` landing resolution still reads `defaultRoute.route` and `defaultRoute.scene_key`
- `[frontend/apps/web/src/stores/session.ts](../../frontend/apps/web/src/stores/session.ts#L1309)` compatibility menu path still falls back to `/a/${actionId}` when no scene key is available
- `[frontend/apps/web/src/app/init.ts](../../frontend/apps/web/src/app/init.ts#L68)` startup still depends on `session.loadAppInit()`, which is the core proof boundary for whether frontend boot only consumes orchestrated startup surface

### Menu Resolver and Entry Reconstruction Candidates

- `[frontend/apps/web/src/router/index.ts](../../frontend/apps/web/src/router/index.ts#L56)` router guard still reconstructs entry from `resolveMenuAction(...)`
- `[frontend/apps/web/src/views/WorkbenchView.vue](../../frontend/apps/web/src/views/WorkbenchView.vue#L375)` workbench still reconstructs menu entry by `resolveMenuAction(...)`
- `[frontend/apps/web/src/views/MenuView.vue](../../frontend/apps/web/src/views/MenuView.vue#L73)` menu page still begins from `resolveMenuAction(...)`

### Scene Registry Proof Candidates

- `[frontend/apps/web/src/app/resolvers/sceneRegistry.ts](../../frontend/apps/web/src/app/resolvers/sceneRegistry.ts#L521)` `getSceneByKey(...)` remains the main proof point that scene registry is the canonical consumer state
- `[frontend/apps/web/src/app/resolvers/sceneRegistry.ts](../../frontend/apps/web/src/app/resolvers/sceneRegistry.ts#L531)` `findSceneByEntryAuthority(...)` remains the main proof point that action/menu/record opens are now being normalized back into scene authority
