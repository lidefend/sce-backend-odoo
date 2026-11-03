# -*- coding: utf-8 -*-
from odoo import api, models


class ScProductPolicy(models.Model):
    _inherit = "sc.product.policy"

    @api.model
    def _apply_company_route_scope(self, authority):
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import build_menu_index, load_surface
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import list_scene_entries
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_states, filter_business_authority

        authority = super()._apply_company_route_scope(authority)
        index = build_menu_index(load_surface())
        rows = self.env["sc.scene.company.enablement"].search([("company_id", "=", self.env.company.id)])
        enabled = business_states({row.scene_key: bool(row.enabled) for row in rows})
        by_id = {}
        by_action = {}
        for xmlid in index:
            menu = self.env.ref(xmlid, raise_if_not_found=False)
            if menu and menu._name == "ir.ui.menu":
                by_id[menu.id] = xmlid
                if menu.action:
                    by_action.setdefault(menu.action.id, []).append(xmlid)
        return filter_business_authority(authority, surface_index=index, enabled=enabled,
                                        entries=list_scene_entries(), menu_xmlids_by_id=by_id,
                                        menu_xmlids_by_action=by_action)
