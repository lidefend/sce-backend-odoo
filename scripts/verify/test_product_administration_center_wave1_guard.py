from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET

from scripts.verify.product_administration_center_wave1_guard import (
    validate,
    validate_payroll_action_groups,
)


class ProductAdministrationCenterWave1GuardTest(unittest.TestCase):
    def test_administration_wave_contract_passes(self) -> None:
        self.assertEqual(validate(), [])

    def test_payroll_action_requires_business_full(self) -> None:
        without_full = ET.fromstring(
            """
            <record id="action_sc_payroll_management">
              <field name="groups_id" eval="[(6, 0, [
                ref('smart_construction_core.group_sc_cap_business_initiator'),
                ref('smart_construction_core.group_sc_cap_business_config_admin')
              ])]"/>
            </record>
            """
        )
        errors = validate_payroll_action_groups(without_full)
        self.assertEqual(len(errors), 1)
        self.assertIn("group_sc_business_full", errors[0])

    def test_payroll_action_accepts_all_declared_audiences(self) -> None:
        with_full = ET.fromstring(
            """
            <record id="action_sc_payroll_management">
              <field name="groups_id" eval="[(6, 0, [
                ref('smart_construction_core.group_sc_cap_business_initiator'),
                ref('smart_construction_core.group_sc_cap_business_config_admin'),
                ref('smart_construction_core.group_sc_business_full')
              ])]"/>
            </record>
            """
        )
        self.assertEqual(validate_payroll_action_groups(with_full), [])


if __name__ == "__main__":
    unittest.main()
