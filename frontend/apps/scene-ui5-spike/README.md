# UI5 scene foundation spike

This app validates one question only: can the generic frontend render a dense,
task-oriented enterprise scene from one semantic contract while switching
between the current component foundation and UI5 Web Components, without
changing the production app or calling a backend?

The payment-request fixture is intentionally local to this app. The reusable
`SceneObjectPage` in `frontend/packages/ui` contains no payment model, role,
action, Chinese-label inference, or direct `ui5-*` element. It renders through
neutral primitive ports provided by `SceneUiProvider`.

The optional `scene_collection_pilot` build flag plus
`?scene=list&pilot=normalized-collection` preview switch enable one read-only
company-directory snapshot. Its adapter accepts only explicit normalized
columns, labels, primary/status fields, widget visibility, source authority,
and read-only permission. Selection, actions, missing authority, missing
widgets, or incomplete identity fail closed. This is a captured-contract pilot,
not a production route or backend integration.

## Governed validation

From the repository root, run:

```bash
make verify.frontend.ui5_scene_spike
```

The target checks the change allowlist and architecture boundary, executes the
normalized adapter failure matrix, performs strict type checking and a
production build, then verifies all three component drivers and 390px layouts
in Chromium. It proves UI5 is registered only after an explicit driver switch,
that switching back preserves the same contract facts, that the normalized
pilot remains read-only, and that the prototype sends no mutating request.

## Explicit non-goals

- No production route or current page replacement.
- No normalized-contract schema change.
- No backend, authentication, database, fixture, or Odoo view change.
- No action execution or form persistence.
- No arbitrary component-level mixing inside one scene.
- No backend field that names a component vendor.
- No adoption decision for the whole component catalogue.

The spike may advance only after visual review of its generated screenshots and
an explicit decision about bundle cost, theme integration, and the mapping from
the existing normalized scene contract.
