# Professional Business Value Components v1

## Boundary

- Formal Product Layer: P0 platform kernel product.
- Layer Target: canonical business-value component family.
- Module: `frontend/apps/web` plus the generic Contract V2 field-to-component projection.
- Standard vs User-Specific: platform standard.

This batch owns money, currency, percentage, status, duration, user, and company presentation for task/workspace and create/edit/readonly. It does not own relation creation, relation dialogs, workflow transitions, business-model policies, or domain-specific labels.

## Authority

The server selects a component key only from formal field metadata: field type, declared widget, or relation model. The frontend registry validates the component key against the field type and selects `ProfessionalBusinessValueControl`. Missing or mismatched declarations fail closed; field names, labels, model names, action IDs, and menu IDs are never classifiers.

| Component key | Formal metadata |
| --- | --- |
| `sc.value.money` | `monetary` field |
| `sc.value.currency` | relation `res.currency` |
| `sc.value.percentage` | declared percentage widget |
| `sc.display.status` | declared statusbar widget |
| `sc.value.duration` | declared `float_time` widget |
| `sc.value.user` | relation `res.users` |
| `sc.value.company` | relation `res.company` |

Readonly values use stable semantic display components. Editable values preserve the existing form mutation channel; route or permission authority is unchanged.
