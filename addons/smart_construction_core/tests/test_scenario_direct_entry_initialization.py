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

    def test_xmlid_batches_match_native_choice_and_keep_group_authority_live(self):
        from unittest.mock import patch
        from odoo.addons.smart_core.delivery.menu_service import MenuService
        from ..services import scenario_surface_projection as projection

        groups = self.env['res.groups'].create([
            {'name': 'Batch metadata with aliases'}, {'name': 'Batch metadata without XMLID'},
        ])
        metadata = self.env['ir.model.data']
        for name in ['first_group_alias', 'second_group_alias']:
            metadata.create({'module': 'test_r7_metadata', 'name': name,
                             'model': 'res.groups', 'res_id': groups[0].id})
        expected = {group.id: group.get_external_id().get(group.id, '') for group in groups}
        principal = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Metadata batch principal', 'login': 'test.r7.metadata.principal',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        service = MenuService(self.env(user=principal.id))
        original = type(groups).get_external_id
        calls = []
        def observe(records):
            calls.append(records.ids)
            return original(records)
        with patch.object(type(groups), 'get_external_id', observe):
            self.assertFalse(service._groups_authorize_current_user(groups))
            principal.write({'groups_id': [(4, groups[0].id)]})
            self.assertTrue(service._groups_authorize_current_user(groups))
            principal.write({'groups_id': [(3, groups[0].id)]})
            self.assertFalse(service._groups_authorize_current_user(groups))
        self.assertEqual(calls, [groups.ids])
        self.assertEqual(service._group_xmlid_cache, expected)

        menu = self.env['ir.ui.menu'].create({
            'name': 'Archived metadata binding', 'active': False,
            'groups_id': [(4, groups[0].id)],
        })
        for name in ['first_menu_alias', 'second_menu_alias']:
            metadata.create({'module': 'test_r7_metadata', 'name': name,
                             'model': 'ir.ui.menu', 'res_id': menu.id})
        scenario = self.env['sc.product.scenario'].create({
            'code': 'test.r7.metadata', 'name': 'Archived metadata scenario', 'active': False,
        })
        self.env['sc.product.scenario.entry'].create({'scenario_id': scenario.id, 'menu_id': menu.id})
        actor_env = self.env(user=principal.id)
        with patch.object(projection, '_menu_external_ids', return_value={}):
            before = projection.load_runtime_surface(actor_env)
            before_scope = projection.runtime_menu_scope(actor_env, before)
        after = projection.load_runtime_surface(actor_env)
        self.assertEqual(after, before)
        self.assertEqual(projection.runtime_menu_scope(actor_env, after), before_scope)
        archived = next(row for row in after['scenarios'] if row['key'] == scenario.code)
        self.assertFalse(archived['active'])
        self.assertEqual(archived['bindings'][0]['menu_key'], menu.get_external_id()[menu.id])
