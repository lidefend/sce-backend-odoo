# -*- coding: utf-8 -*-
from odoo import api, models, tools


class ScProductPolicy(models.Model):
    _inherit = "sc.product.policy"

    @api.model
    def _company_route_scope_cache_key(self):
        from odoo.addons.smart_core.delivery.runtime_route_authority import (
            principal_group_signature,
        )

        return principal_group_signature(self.env)

    @api.model
    @tools.ormcache(
        "self.env.cr.dbname",
        "self.env.user.id",
        "self.env.company.id",
        "self._company_route_scope_cache_key()",
    )
    def _company_route_scope_context(self):
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import (
            load_runtime_surface, runtime_menu_scope,
        )
        from odoo.addons.smart_construction_scene.profiles.scene_registry_content import list_scene_entries
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import business_key, business_states, filter_business_authority
        from odoo.addons.smart_construction_scene.services.tenant_scene_activation import read_tenant_enablement

        surface = load_runtime_surface(self.env)
        index, by_id, by_action = runtime_menu_scope(self.env, surface)
        stored = {business_key(scene["key"]): read_tenant_enablement(
            self.env, self.env.company.id, business_key(scene["key"]))
            for scene in surface["scenarios"]}
        return surface, index, by_id, by_action, business_states(stored), list_scene_entries()

    @api.model
    def _apply_company_route_scope(self, authority):
        from odoo.addons.smart_construction_scene.services.business_scene_enablement import (
            filter_business_authority,
        )

        authority = super()._apply_company_route_scope(authority)
        _surface, index, by_id, by_action, enabled, entries = self._company_route_scope_context()
        return filter_business_authority(
            authority,
            surface_index=index,
            enabled=enabled,
            entries=entries,
            menu_xmlids_by_id=by_id,
            menu_xmlids_by_action=by_action,
        )
