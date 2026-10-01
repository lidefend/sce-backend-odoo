"""Industry configuration entry authority; no Odoo registry or database."""
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

MODULE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("category_role_policy", MODULE / "core_extension_policy_maps.py")
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)
CATEGORY = "smart_construction_core.menu_sc_business_category"


class CategoryEntryPolicyTest(unittest.TestCase):
    def test_configuration_role_declares_existing_native_entry(self):
        role = policy.ROLE_SURFACE_OVERRIDES["business_config_admin"]
        self.assertEqual(role["admin_menu_xmlids"].count(CATEGORY), 1)
        tree = ET.parse(MODULE / "views/support/business_category_views.xml")
        menu = tree.find(".//menuitem[@id='menu_sc_business_category']")
        self.assertEqual(menu.get("action"), "action_sc_business_category")
        self.assertEqual(menu.get("groups"), "smart_construction_core.group_sc_cap_business_config_admin")
        action = tree.find(".//record[@id='action_sc_business_category']")
        self.assertEqual(action.find("field[@name='res_model']").text, "sc.business.category")

    def test_business_roles_do_not_gain_configuration_entry(self):
        for name in ("finance", "pm", "owner", "executive"):
            role = policy.ROLE_SURFACE_OVERRIDES[name]
            for key in ("admin_menu_xmlids", "primary_menu_xmlids", "role_home_menu_xmlids", "contextual_menu_xmlids"):
                self.assertNotIn(CATEGORY, role.get(key, []), (name, key))

    def test_contract_operator_event_entry_keeps_native_capability_boundary(self):
        import csv
        event = 'smart_construction_core.menu_sc_contract_event'
        self.assertEqual(policy.ROLE_SURFACE_OVERRIDES['project_member']['contextual_menu_xmlids'].count(event), 1)
        tree = ET.parse(MODULE / 'views/menu_business_taxonomy.xml')
        menu = tree.find(".//menuitem[@id='menu_sc_contract_event']")
        self.assertEqual(menu.get('action'), 'smart_construction_core.action_sc_contract_event')
        groups = set(menu.get('groups').split(','))
        self.assertEqual(groups, {'smart_construction_core.group_sc_cap_contract_read',
                                 'smart_construction_core.group_sc_cap_contract_user',
                                 'smart_construction_core.group_sc_cap_contract_manager'})
        with (MODULE / 'security/ir.model.access.csv').open() as stream:
            access = next(row for row in csv.DictReader(stream) if row['id'] == 'access_sc_contract_event_user')
        self.assertEqual([access[k] for k in ('perm_read', 'perm_write', 'perm_create', 'perm_unlink')], ['1', '1', '1', '0'])
        roles = ET.parse(MODULE / 'security/sc_role_groups.xml')
        implied = roles.find(".//record[@id='group_sc_role_operation_user']/field[@name='implied_ids']").get('eval')
        self.assertIn('group_sc_cap_contract_user', implied)



if __name__ == "__main__":
    unittest.main()
