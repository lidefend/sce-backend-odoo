# -*- coding: utf-8 -*-
import json
from pathlib import Path

from odoo.addons.smart_core.identity.identity_resolver import IdentityResolver
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "role_capability_authority")
class TestRoleCapabilityAuthority(TransactionCase):
    def _xmlid(self, group):
        return group.get_external_id().get(group.id) or ""

    def _closure(self, group):
        seen = self.env["res.groups"]
        pending = group
        while pending:
            current = pending[0]
            pending = pending[1:]
            if current in seen:
                continue
            seen |= current
            pending |= current.implied_ids - seen
        return seen

    def _entry_closure(self, group):
        return {
            xmlid.rsplit(".group_sc_entry_", 1)[-1]
            for xmlid in (self._xmlid(item) for item in self._closure(group))
            if ".group_sc_entry_p" in xmlid
        }

    def _role_groups(self):
        data = self.env["ir.model.data"].sudo().search([
            ("module", "=", "smart_construction_core"),
            ("model", "=", "res.groups"),
            ("name", "=like", "group_sc_role_%"),
        ])
        groups = self.env["res.groups"]
        for row in data:
            groups |= self.env["res.groups"].browse(row.res_id).exists()
        groups |= self.env.ref("smart_construction_core.group_sc_business_full")
        return groups

    def test_role_groups_do_not_imply_entry_carriers(self):
        for group in self._role_groups():
            direct = {self._xmlid(item) for item in group.implied_ids}
            self.assertFalse(
                {item for item in direct if ".group_sc_entry_p" in item},
                (self._xmlid(group), direct),
            )
            for xmlid in direct:
                self.assertTrue(
                    ".group_sc_cap_" in xmlid
                    or xmlid.endswith(".group_sc_internal_user")
                    or ".group_sc_role_" in xmlid
                    or xmlid.endswith(".group_sc_business_full"),
                    (self._xmlid(group), xmlid),
                )

    def test_capability_groups_never_imply_role_groups(self):
        data = self.env["ir.model.data"].sudo().search([
            ("module", "=", "smart_construction_core"),
            ("model", "=", "res.groups"),
            ("name", "=like", "group_sc_cap_%"),
        ])
        self.assertTrue(data, "capability groups must be installed")
        for row in data:
            group = self.env["res.groups"].browse(row.res_id).exists()
            self.assertTrue(group, row.name)
            self.assertFalse(
                {
                    xmlid for xmlid in (self._xmlid(item) for item in group.implied_ids)
                    if ".group_sc_role_" in xmlid or xmlid.endswith(".group_sc_business_full")
                },
                self._xmlid(group),
            )

    def test_role_to_entry_closures_are_preserved(self):
        expected = {
            "group_sc_role_accounting_read": {f"p{number:02d}" for number in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_accounting_user": {f"p{number:02d}" for number in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_accounting_manager": {f"p{number:02d}" for number in (2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14)},
            "group_sc_role_cost_user": {f"p{number:02d}" for number in (2, 3, 4, 6, 7, 8, 9, 10, 11, 13)},
            "group_sc_role_executive": {f"p{number:02d}" for number in (3, 5, 7, 13)},
            "group_sc_role_finance_user": {f"p{number:02d}" for number in (2, 3, 5, 6, 8, 13)},
            "group_sc_role_finance_manager": {f"p{number:02d}" for number in (2, 3, 5, 6, 8, 13)},
            "group_sc_role_owner": {f"p{number:02d}" for number in (2, 3, 4, 5, 6, 7, 9, 11, 13, 14)},
            "group_sc_role_project_manager": {f"p{number:02d}" for number in (2, 4, 5, 6, 7, 11, 13, 14)},
            "group_sc_role_project_user": {f"p{number:02d}" for number in (3, 4, 5, 6, 7, 8, 9, 10, 11, 14)},
            "group_sc_role_operation_user": {"p06"},
            "group_sc_business_full": {f"p{number:02d}" for number in range(1, 15)},
            "group_sc_role_experience": {f"p{number:02d}" for number in range(1, 15)},
        }
        for group_name, carriers in expected.items():
            group = self.env.ref(f"smart_construction_core.{group_name}")
            self.assertEqual(self._entry_closure(group), carriers, group_name)

    def test_business_config_admin_keeps_both_role_codes(self):
        role = self.env.ref("smart_construction_core.group_sc_role_business_admin")
        role_codes, evidence = IdentityResolver(self.env).resolve_role_codes_with_evidence(
            {self._xmlid(group) for group in self._closure(role)}
        )
        self.assertEqual(role_codes, ["business_config_admin", "business_full"])
        self.assertEqual(evidence["surface_roles"], ["business_config_admin"])

    def test_entry_scope_capabilities_own_the_carriers(self):
        for number in range(1, 15):
            suffix = f"p{number:02d}"
            capability = self.env.ref(
                f"smart_construction_core.group_sc_cap_entry_scope_{suffix}"
            )
            carrier = self.env.ref(
                f"smart_construction_core.group_sc_entry_{suffix}"
            )
            self.assertEqual(capability.implied_ids, carrier)
        full = self.env.ref(
            "smart_construction_core.group_sc_cap_entry_scope_full"
        )
        self.assertEqual(
            {self._xmlid(group) for group in full.implied_ids},
            {
                f"smart_construction_core.group_sc_cap_entry_scope_p{number:02d}"
                for number in range(1, 15)
            },
            "full entry scope must compose all 14 scoped capabilities",
        )

    def test_rebound_menus_keep_their_entry_carrier(self):
        mapping_path = Path(__file__).resolve().parents[1] / "data/menu_entry_group_rebinding.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        for menu_xmlid, entry_key in mapping.items():
            menu = self.env.ref(menu_xmlid)
            expected = self.env.ref(f"smart_construction_core.group_sc_{entry_key}")
            self.assertEqual(menu.groups_id, expected, menu_xmlid)


