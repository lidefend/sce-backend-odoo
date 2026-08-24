# Professional Base Field Components v1

## Authority

Phase 7A establishes one P0 professional field family for `char`, `text`,
`html`, `integer`, `float`, `date`, `datetime`, `boolean`, and `selection`.
These controls consume the component resolution already admitted by the Phase 6
registry; they do not reinterpret component keys or grant capabilities.

The supported matrix is:

```text
task      × create | edit | readonly
workspace × create | edit | readonly
```

Canonical form fields carry both axes from the Presenter into FormSection and
the professional control emits them as deterministic DOM evidence. FormSection
uses outside the canonical Contract path are marked `unscoped`; they are not
silently described as workspace/edit authority.

## Production boundary

`ProfessionalBaseFieldControl` owns editable and readonly presentation for the
nine base types. It uses project primitives for input, select, and date/time,
and keeps HTML readonly output sanitized. The former duplicated base-field
branches in `FormSection` are removed; relation, binary, monetary, radio, and
date-range capabilities remain with their owning later batches or explicit
special-widget paths.

The component emits:

- `data-professional-field-family=base`;
- exact field type and control kind;
- presentation mode and render profile when canonical;
- effective editable/readonly control state.

## Exclusions

- Money/currency, user/company, relations, x2many, workflow, and collaboration.
- Backend Contract, permission, route, action, menu, and mutation semantics.
- Model, field-name, label, action-ID, or menu-ID special cases.
