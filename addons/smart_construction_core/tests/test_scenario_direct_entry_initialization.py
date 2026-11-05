from odoo.tests.common import TransactionCase, tagged

from ..models.support.product_scenario import DIRECT_CONFIGURATION_MENU_XMLIDS
from ..services.scenario_surface_projection import runtime_menu_scope


@tagged('post_install', '-at_install', 'sc_gate', 'scenario_direct_initialization')
class TestScenarioDirectInitialization(TransactionCase):
    """Run in local.test from a freshly installed module, with no fixture grants."""

    def test_fresh_install_declares_configuration_entries(self):
        # A fresh Odoo admin has no industry configuration roles. Native menu
        # search applies menu groups even in sudo mode; declare the principal
        # prerequisite without changing any menu, exemption or publication fact.
        menus = self.env['ir.ui.menu'].browse([
            self.env.ref(xmlid).id for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS
        ])
        self.env.user.write({'groups_id': [(4, group.id) for group in menus.mapped('groups_id')]})
        index, by_id, _ = runtime_menu_scope(self.env)
        self.assertEqual(len(DIRECT_CONFIGURATION_MENU_XMLIDS), 4)
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            with self.subTest(xmlid=xmlid):
                menu = self.env.ref(xmlid)
                self.assertTrue(menu.sc_scenario_exempt)
                self.assertIn(menu.id, by_id, (xmlid, menu.active, menu.get_external_id()))
                self.assertEqual(index[by_id[menu.id]]['location'], 'exempt')
                self.assertFalse(self.env['sc.product.scenario.entry'].search_count([
                    ('menu_id', '=', menu.id),
                ]))

    def test_upgrade_without_marker_does_not_restore_revocation_or_deleted_binding(self):
        Scenario = self.env['sc.product.scenario']
        Entry = self.env['sc.product.scenario.entry']
        params = self.env['ir.config_parameter'].sudo()
        module = self.env['ir.module.module'].search([('name', '=', 'smart_construction_core')])
        module.state = 'to upgrade'
        custom = Scenario.create({'code': 'test.custom.direct', 'name': 'Custom'})
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            menu = self.env.ref(xmlid)
            Entry.create({'scenario_id': custom.id, 'menu_id': menu.id}).unlink()
            self.assertFalse(menu.sc_scenario_exempt)
        unknown = self.env['ir.ui.menu'].create({'name': 'Unknown leaf'})
        params.set_param('smart_construction_core.scenario_entry_scope.v1', False)
        Scenario.initialize_direct_entry_exemptions()
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            self.assertFalse(self.env.ref(xmlid).sc_scenario_exempt)
        self.assertFalse(unknown.sc_scenario_exempt)
        Scenario.initialize_direct_entry_exemptions()
        self.assertFalse(self.env.ref(DIRECT_CONFIGURATION_MENU_XMLIDS[0]).sc_scenario_exempt)

    def test_completed_install_does_not_restore_revoked_declaration(self):
        menu = self.env.ref(DIRECT_CONFIGURATION_MENU_XMLIDS[0])
        menu.sc_scenario_exempt = False
        self.env['sc.product.scenario'].initialize_direct_entry_exemptions()
        self.assertFalse(menu.sc_scenario_exempt)
        unknown = self.env['ir.ui.menu'].create({'name': 'Unknown action', 'action': '%s,%s' % (menu.action._name, menu.action.id)})
        self.assertFalse(unknown.sc_scenario_exempt)
