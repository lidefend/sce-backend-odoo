# Native Form Action Presentation v1

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: Native structured form action presentation.
- Module: `frontend/apps/web`.
- Authority: the renderer consumes backend-projected action identity, level,
  capability state and execution payload. It does not infer business meaning
  from model, action, menu, label or route.

## Presentation roles

Native structured forms expose three distinct interaction roles:

1. Ordinary record actions use the shared `ScButton` primitive. The renderer
   preserves action evidence, disabled reason and the existing executor event.
2. Smart actions use `NativeSmartAction`. This is the governed button-box/stat
   action card pattern, not a second ordinary button implementation.
3. Overflow uses `NativeActionOverflowMenu`. The trigger and menu items compose
   `ScButton`, while the component owns disclosure state, Escape settlement,
   outside-click settlement and ARIA menu relationships.

Notebook tabs and favorite toggles remain native stateful controls. They are not
generic commands and are deliberately excluded from primitive replacement.

## Compatibility

The smart-action and overflow components retain existing stable DOM class
markers used by governed acceptance scripts. Semantic component markers are the
new presentation authority; compatibility classes do not select renderer
behavior and do not own appearance in `NativeFormTreeRenderer`.

## Exclusions

- no Contract V2 schema change;
- no permission or capability inference;
- no route or record-open change;
- no action executor or mutation change;
- no task/Floorplan change;
- no model, action ID, menu ID or business-label special case.
