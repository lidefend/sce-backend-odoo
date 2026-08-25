# Material Domain Frontend Rollout v1

This report covers the repository formal-product runtime baseline for the material center.
Demo, customer overlays, and user-specific visibility are deliberately excluded.

## Summary

- status: `PASS`
- formal actions: `3`
- models: `3`
- ready collection surfaces: `3`
- readable fallbacks: `0`
- structural forms: `3`
- fail-closed surfaces: `0`
- gaps: `0`

## Formal entries

| Menu | Action | Model | Views | Layered authority |
| --- | --- | --- | --- | --- |
| `smart_construction_core.menu_sc_material_inbound` | `smart_construction_core.action_sc_material_inbound_handling` | `sc.material.inbound` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_project_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_material_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_material_inbound`:[`smart_construction_core.group_sc_cap_material_manager`, `smart_construction_core.group_sc_cap_material_read`, `smart_construction_core.group_sc_cap_material_user`] → action:[`smart_construction_core.group_sc_cap_material_manager`, `smart_construction_core.group_sc_cap_material_read`, `smart_construction_core.group_sc_cap_material_user`] |
| `smart_construction_core.menu_sc_material_outbound` | `smart_construction_core.action_sc_material_outbound` | `sc.material.outbound` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_project_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_material_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_material_outbound`:[`smart_construction_core.group_sc_cap_material_manager`, `smart_construction_core.group_sc_cap_material_read`, `smart_construction_core.group_sc_cap_material_user`] → action:[`smart_construction_core.group_sc_cap_material_manager`, `smart_construction_core.group_sc_cap_material_read`, `smart_construction_core.group_sc_cap_material_user`] |
| `smart_construction_core.menu_sc_product_material_return_v1` | `smart_construction_core.action_sc_material_supplier_return` | `sc.material.supplier.return` | tree:table:ready, form:form_structure:structural | `smart_construction_core.menu_sc_root`:[public] → `smart_construction_core.menu_sc_project_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_material_center`:[`smart_construction_core.group_sc_cap_project_read`] → `smart_construction_core.menu_sc_product_material_return_v1`:[`smart_construction_core.group_sc_cap_material_read`] → action:[`smart_construction_core.group_sc_cap_material_read`] |

## Gap classification

No P0/P1 frontend rollout gaps were detected for the formal material-center entries.

## Acceptance routing

- Primary journey: a formal material entry preserves its resolved action/menu and form authority.
- Security counterexample: an unauthorized user cannot gain entry or write authority.
- Any future unregistered `smart_*` view class fails this audit closed.
