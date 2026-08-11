# TDesign Frontend Engine Integration Specification v1

Status: topic baseline candidate
Product layer: P0 platform frontend mechanism
Scope: `frontend/apps/web`

## 1. Decision

The custom frontend uses TDesign Vue Next as its mature interaction and visual engine while keeping `Sc*` components as the product-semantic and vendor-isolation layer. Pages, business modules, and contract renderers must not import TDesign directly.

This decision improves primitive consistency, accessibility, interaction states, and complex-table maturity. It does not change the authority of backend contracts, permissions, routes, data, or business rules. TDesign is neither a page generator nor a second business contract.

## 2. Single dependency direction

```text
Unified page contract / native-view facts
        ↓
Pages and generic renderers
        ↓
Sc* product-semantic components
        ↓
tdesignAdapter (the only vendor entry)
        ↓
TDesign Vue Next

SC semantic tokens
        ↓
tdesign-bridge.css
        ↓
TDesign theme variables
```

The following reverse dependencies are forbidden:

- direct `tdesign-vue-next` or icon-package imports from pages or business modules;
- model, field, menu, or industry semantics inside TDesign adapters;
- backend-provided breakpoints, pixels, or vendor component properties;
- changes to formal page contracts, permissions, routes, or write semantics for library convenience;
- a second public component API alongside `Sc*`.

## 3. Version and theme governance

- Pin exact versions of `tdesign-vue-next` and `tdesign-icons-vue-next`.
- Runtime code may import only reviewed component subpaths through `tdesignAdapter.ts`, avoiding full-package traversal and accidental dependency growth.
- TDesign CSS is loaded only by `tdesign-bridge.css`.
- Brand, text, background, border, radius, and shadow variables map to `--sc-semantic-*` or existing SC tokens. Pages may not override vendor variables outside the token bridge.
- Upgrades require separate review of adapter changes, bundle size, keyboard behavior, responsive behavior, and the three representative surfaces.

## 4. System-wide adoption model

System-wide adoption means one engine, one token authority, one public component API, and one enforcement boundary. It does not mean that pages call vendor components directly. Adoption has three rings: global engine loading, `Sc*` public primitives, and prioritized business-surface migration.

This iteration expands the fail-closed boundary to every Vue source file under `frontend/apps/web/src`. Business pages, layouts, renderers, and public components may not reintroduce ordinary native `input`, `select`, or `textarea` elements; they must use product-semantic primitives such as `ScTextField`, `ScTextArea`, `ScSelect`, `ScMultiSelect`, `ScCheckbox`, and `ScDateField`. Native file upload and radio controls that preserve browser selection semantics remain explicit, inventoried exceptions. The gate also prints the source-wide native-control inventory so the exception scope cannot grow silently.

## 5. First real closures

| Surface | Integration point | Iteration goal | Preserved authority |
|---|---|---|---|
| Contract list | `ScButton`, `ScIcon`, status components | Consistent buttons, icons, and states | Existing contract supplies columns, filters, and actions |
| Contract form | `ScTextField`, `ScTextArea`, `ScCheckbox`, `ScDateField`, `ScSelect`, `ScDialog`, `ScDrawer` | Consistent data entry, selection, overlays, and feedback | Backend supplies fields, modifiers, and save semantics |
| WBS hierarchy | `ScHierarchyTable` | Mature table engine, discoverable hierarchy, keyboard selection | Page-contract projection supplies tree, columns, commands, and records |

These surfaces are the representative browser-acceptance closures. Ordinary data-entry controls have migrated across the complete source tree. Complex command buttons, tree nodes, drag handles, and sort triggers continue to evolve through their dedicated interaction primitives instead of being mechanically replaced merely to drive the native-tag count to zero. Further adoption must proceed through `Sc*` capabilities; direct vendor API use is not an acceptable shortcut.

## 6. Quality gates

The topic baseline requires:

1. exact vendor versions and a reproducible lockfile;
2. vendor imports confined to one adapter;
3. all theme variables bridged through SC semantic tokens and zero hardcoded colors;
4. contract list, contract form, and WBS hierarchy consuming their required `Sc*` components;
5. every Vue source file rejecting ordinary native data-entry regression and reporting the repository-wide native-control and controlled-exception inventory;
6. the WBS guard verifying the real `ScHierarchyTable → TEnhancedTable` chain, not obsolete CSS markers;
7. strict typecheck, release units, production build, table-primitive guard, workspace-layout guard, and `git diff --check` passing;
8. when a runtime is available, five-viewport browser acceptance for text, textarea, checkbox, select, keyboard focus, expand/collapse, overlay close behavior, page overflow, and console errors.

Static guards must not be presented as visual acceptance when a browser environment is unavailable; the evidence boundary must be explicit in delivery records.

## 7. Performance budget

- Package-root component or icon imports are forbidden; the adapter uses reviewed subpaths.
- Each added TDesign capability may include only components actually consumed.
- Large-chunk build warnings must be recorded and compared with mainline; warning thresholds must not be raised to conceal them.
- Runtime interaction performance continues to use the repository's existing absolute and relative budgets. A candidate may not recalibrate its own baseline.

## 8. Compatibility, evolution, and rollback

- Public `Sc*` properties and events form the compatibility boundary; pages do not know which vendor is used.
- Adapters preserve existing call shapes so business pages do not require bulk rewrites.
- Complex primitives not yet covered remain on current `Sc*` implementations; full replacement is not a goal by itself.
- Roll back per component by restoring the corresponding `Sc*` internals and removing its adapter export, without touching page contracts or business data.
- Remove the dependencies only after every adapted component has rolled back and the direct-import guard still passes.

## 9. Next sequence

1. Freeze this topic branch as the UI-engine baseline.
2. Calibrate density, overlays, tables, and mobile behavior with real-page evidence.
3. Add high-reuse `Sc*` capabilities before page-specific styling.
4. Include theme, accessibility, and performance verification in release gates.
5. Expand into editable tables, tree selection, notification, and complex input by product priority, without a wholesale page rewrite.
