# Product Page Patterns v1

## Authority

Product Page Patterns are P0 structural presentation authorities. They organize
existing renderers and controls; they do not infer Contract semantics, select
business components, or grant capabilities.

The four formal patterns are:

- `task-form`: task-focused create, edit, handling, and explicit readonly presentation.
- `workspace-form`: Native structured form for professional management and decision work.
- `collection`: search, filter, group, list/kanban, selection, batch action, and pagination organization.
- `dashboard`: metric, risk, todo, readable fallback, and drilldown organization.

## Axes and invariants

Form pattern and render profile are orthogonal:

```text
task-form      × create | edit | readonly
workspace-form × create | edit | readonly
collection     × readonly
dashboard      × readonly
```

`presentationMode` remains the backend-declared form authority. The frontend
must not derive task/workspace from fields, semantic roles, model names, action
IDs, menu IDs, or renderer selection. A pattern/mode mismatch fails closed.

## Production wiring

- `ContractFormDriverHost` selects `TaskFormPattern` only from the existing
  explicit task floorplan decision and `WorkspaceFormPattern` for the existing
  Native branch. The pattern does not replace either renderer.
- `ActionView` selects `CollectionPattern` or `DashboardPattern` from its formal
  decoded view mode. Existing list, kanban, toolbar, filter, pagination, and
  dashboard surfaces remain unchanged inside the pattern.
- Every pattern emits `data-product-page-pattern`, `data-presentation-mode`, and
  `data-render-profile` for deterministic runtime evidence.

## Exclusions

- No Contract V2 or permission changes.
- No model/action/menu special cases.
- No professional component registry or readiness claims.
- No industry component implementation.
- No route, mutation, or settlement changes.
