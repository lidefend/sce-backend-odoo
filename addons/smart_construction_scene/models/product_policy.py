# -*- coding: utf-8 -*-
from odoo import api, models


class ScProductPolicy(models.Model):
    _inherit = "sc.product.policy"

    @api.model
    def _apply_company_route_scope(self, authority):
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import build_menu_index, load_surface
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import list_scene_entries
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key, business_states, filter_business_authority
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement

        authority = super()._apply_company_route_scope(authority)
        index = build_menu_index(load_surface())
        stored = {}
        for scene in load_surface().get("scenarios") or []:
            key = str(scene.get("key") or "").strip()
            if key:
                stored[business_key(key)] = read_tenant_enablement(self.env, self.env.company.id, business_key(key))
        enabled = business_states(stored)
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
