# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_construction_core.services import scenario_surface_projection


@tagged(
    "post_install",
    "-at_install",
    "sc_smoke",
    "company_route_scope_cache",
)
class TestCompanyRouteScopeCache(TransactionCase):
    def test_scene_state_is_not_a_second_route_authority(self):
        policy = self.env["sc.product.policy"]
        authority = {
            "primary_actions": [],
            "role_home_actions": [],
            "contextual_actions": [],
            "admin_actions": [],
            "menu_containers": [],
            "denied_actions": [],
        }
        self.env.registry.clear_cache()
        with patch.object(
            scenario_surface_projection,
            "load_runtime_surface",
            wraps=scenario_surface_projection.load_runtime_surface,
        ) as load_surface:
            first = policy._apply_company_route_scope(authority)
            second = policy._apply_company_route_scope(authority)
        self.assertEqual(load_surface.call_count, 0)
        self.assertEqual(first, second)
        self.assertEqual(first, authority)
        self.assertEqual(authority["denied_actions"], [])
