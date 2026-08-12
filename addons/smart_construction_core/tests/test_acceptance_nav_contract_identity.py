# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.handlers.system_init import (
    _acceptance_surface_matchers,
    _node_is_user_acceptance_surface,
)
from odoo.addons.smart_construction_core.core_extension_hook_facts import (
    user_data_acceptance_nav_contract,
)


@tagged("post_install", "-at_install", "acceptance_nav_identity")
class TestAcceptanceNavContractIdentity(TransactionCase):
    def test_acceptance_contract_never_uses_database_local_numeric_ids(self):
        contract = user_data_acceptance_nav_contract()

        self.assertNotIn("acceptance_surface_menu_ids", contract)
        self.assertNotIn("acceptance_surface_action_ids", contract)

    def test_unrelated_released_action_id_collision_is_not_filtered(self):
        matchers = _acceptance_surface_matchers(user_data_acceptance_nav_contract())
        office_asset = {
            "menu_id": 719,
            "action_id": 899,
            "label": "办公资产",
            "menu_xmlid": "smart_construction_core.menu_sc_product_office_asset_v1",
            "model": "sc.office.asset",
            "meta": {"action_id": 899},
        }

        self.assertFalse(
            _node_is_user_acceptance_surface(
                office_asset,
                acceptance_matchers=matchers,
            )
        )

    def test_stable_acceptance_token_remains_filtered(self):
        matchers = _acceptance_surface_matchers(user_data_acceptance_nav_contract())
        acceptance_node = {
            "label": "旧业务数据",
            "menu_xmlid": "smart_construction_core.menu_legacy_direct_acceptance_example",
        }

        self.assertTrue(
            _node_is_user_acceptance_surface(
                acceptance_node,
                acceptance_matchers=matchers,
            )
        )
