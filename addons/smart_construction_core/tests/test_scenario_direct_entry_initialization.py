from odoo.tests.common import TransactionCase, tagged

from ..models.support.product_scenario import (
    DIRECT_CONFIGURATION_MENU_XMLIDS,
    DIRECT_PLATFORM_MENU_XMLIDS,
    DIRECT_WORKSPACE_MENU_XMLIDS,
)
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

    def test_fresh_install_declares_shell_and_platform_direct_entries(self):
        index, by_id, _ = runtime_menu_scope(self.env)
        for xmlid in DIRECT_WORKSPACE_MENU_XMLIDS + DIRECT_PLATFORM_MENU_XMLIDS:
            with self.subTest(xmlid=xmlid):
                menu = self.env.ref(xmlid)
                self.assertTrue(menu.action)
                self.assertTrue(menu.sc_scenario_exempt)
                self.assertEqual(index[by_id[menu.id]]["location"], "exempt")

    def test_navigation_exemption_is_one_time_and_binding_wins(self):
        Scenario = self.env["sc.product.scenario"]
        Entry = self.env["sc.product.scenario.entry"]
        Param = self.env["ir.config_parameter"].sudo()
        menu = self.env.ref(DIRECT_WORKSPACE_MENU_XMLIDS[0])
        scenario = Scenario.create({"code": "test.shell.binding", "name": "Shell binding"})
        Entry.create({"scenario_id": scenario.id, "menu_id": menu.id})
        Param.set_param("smart_construction_core.navigation_entry_scope.v1", False)
        Scenario.initialize_navigation_entry_exemptions()
        self.assertFalse(menu.sc_scenario_exempt)
        self.assertTrue(Entry.search_count([
            ("scenario_id", "=", scenario.id),
            ("menu_id", "=", menu.id),
        ]))
        Entry.search([("scenario_id", "=", scenario.id)]).unlink()
        menu.sc_scenario_exempt = False
        Scenario.initialize_navigation_entry_exemptions()
        self.assertFalse(menu.sc_scenario_exempt)

    def test_completed_install_does_not_restore_revoked_declaration(self):
        menu = self.env.ref(DIRECT_CONFIGURATION_MENU_XMLIDS[0])
        menu.sc_scenario_exempt = False
        self.env['sc.product.scenario'].initialize_direct_entry_exemptions()
        self.assertFalse(menu.sc_scenario_exempt)
        unknown = self.env['ir.ui.menu'].create({'name': 'Unknown action', 'action': '%s,%s' % (menu.action._name, menu.action.id)})
        self.assertFalse(unknown.sc_scenario_exempt)

    def test_scope_indexes_group_gated_menus_for_unprivileged_principal(self):
        """The scene-fact index must not inherit native menu visibility."""
        from odoo.addons.smart_construction_core.services.scenario_surface_projection import runtime_menu_scope

        config_group = self.env.ref(
            'smart_construction_core.group_sc_cap_business_config_admin'
        )
        principal = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Scope index principal',
            'login': 'scope.index.principal',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        menu = self.env['ir.ui.menu'].create({
            'name': 'Group-gated config leaf',
            'parent_id': self.env.ref('smart_construction_core.menu_sc_root').id,
            'sc_scenario_exempt': True,
            'groups_id': [(4, config_group.id)],
        })
        # Native visible search still hides it from the unprivileged principal.
        principal_env = self.env(user=principal.id)
        self.assertFalse(principal_env['ir.ui.menu'].sudo().search([('id', '=', menu.id)]))
        # The fact index must still resolve the menu and its explicit exemption.
        index, by_id, _ = runtime_menu_scope(principal_env)
        self.assertIn(menu.id, by_id)
        self.assertEqual(index[by_id[menu.id]]['location'], 'exempt')
