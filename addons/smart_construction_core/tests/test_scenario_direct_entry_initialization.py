import runpy
from pathlib import Path

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.support.product_scenario import (
    DIRECT_CONFIGURATION_MENU_XMLIDS,
    DIRECT_PLATFORM_MENU_XMLIDS,
    DIRECT_WORKSPACE_MENU_XMLIDS,
    NAVIGATION_ENTRY_SCOPE_MARKER,
)
from ..services.scenario_surface_projection import (
    load_maintained_runtime_surface,
    runtime_menu_scope,
)
from odoo.addons.smart_construction_scene.services.business_scene_enablement import (
    business_key,
    business_states,
    filter_business_authority,
    location_business_enabled,
)


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
        index, by_id, _ = runtime_menu_scope(
            self.env,
            load_maintained_runtime_surface(self.env),
        )
        self.assertEqual(len(DIRECT_CONFIGURATION_MENU_XMLIDS), 4)
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            with self.subTest(xmlid=xmlid):
                menu = self.env.ref(xmlid)
                self.assertTrue(menu.sc_scenario_exempt)
                self.assertIn(menu.id, by_id, (xmlid, menu.active, menu.get_external_id()))
                self.assertEqual(index[by_id[menu.id]]['location'], 'scenario')
                self.assertTrue(index[by_id[menu.id]]['direct_platform_exempt'])
                entry = self.env['sc.product.scenario.entry'].sudo().search([
                    ('menu_id', '=', menu.id),
                ], limit=1)
                self.assertTrue(entry)
                self.assertEqual(entry.scenario_id.code, "config.presentation"
                                 if xmlid in {
                                     "smart_construction_core.menu_sc_business_config_workbench",
                                     "smart_construction_core.menu_ui_form_field_policy_business_config",
                                     "smart_construction_core.menu_ui_menu_config_policy_business_config",
                                 }
                                 else "config.approval")

    def test_upgrade_preserves_direct_declarations_and_revoked_generic_entries(self):
        Scenario = self.env['sc.product.scenario']
        Entry = self.env['sc.product.scenario.entry']
        params = self.env['ir.config_parameter'].sudo()
        module = self.env['ir.module.module'].search([('name', '=', 'smart_construction_core')])
        module.state = 'to upgrade'
        custom = Scenario.create({'code': 'test.custom.direct', 'name': 'Custom'})
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            menu = self.env.ref(xmlid)
            Entry.create({'scenario_id': custom.id, 'menu_id': menu.id}).unlink()
            self.assertTrue(menu.sc_scenario_exempt)
        unknown = self.env['ir.ui.menu'].create({'name': 'Unknown leaf'})
        params.set_param('smart_construction_core.scenario_entry_scope.v1', False)
        Scenario.initialize_direct_entry_exemptions()
        for xmlid in DIRECT_CONFIGURATION_MENU_XMLIDS:
            self.assertTrue(self.env.ref(xmlid).sc_scenario_exempt)
        self.assertFalse(unknown.sc_scenario_exempt)
        Scenario.initialize_direct_entry_exemptions()
        self.assertTrue(self.env.ref(DIRECT_CONFIGURATION_MENU_XMLIDS[0]).sc_scenario_exempt)

    def test_fresh_install_declares_shell_and_platform_direct_entries(self):
        index, by_id, _ = runtime_menu_scope(
            self.env,
            load_maintained_runtime_surface(self.env),
        )
        Entry = self.env["sc.product.scenario.entry"].sudo()
        for xmlid in DIRECT_WORKSPACE_MENU_XMLIDS + DIRECT_PLATFORM_MENU_XMLIDS:
            with self.subTest(xmlid=xmlid):
                menu = self.env.ref(xmlid)
                if xmlid != "smart_construction_core.menu_sc_workspace_home":
                    self.assertTrue(menu.action)
                self.assertTrue(menu.sc_scenario_exempt)
                location = index[by_id[menu.id]]
                self.assertTrue(location.get("direct_platform_exempt"))
                self.assertTrue(location_business_enabled(location, {}))
                bound = bool(Entry.search_count([("menu_id", "=", menu.id)]))
                self.assertEqual(
                    location["location"],
                    "scenario" if bound else "exempt",
                )

    def test_navigation_exemption_is_one_time_and_direct_binding_survives(self):
        Scenario = self.env["sc.product.scenario"]
        Param = self.env["ir.config_parameter"].sudo()
        menu = self.env.ref(DIRECT_WORKSPACE_MENU_XMLIDS[0])
        Param.set_param(NAVIGATION_ENTRY_SCOPE_MARKER, False)
        Scenario.initialize_navigation_entry_exemptions()
        self.assertTrue(menu.sc_scenario_exempt)
        menu.sc_scenario_exempt = False
        Scenario.initialize_navigation_entry_exemptions()
        self.assertFalse(menu.sc_scenario_exempt)
        self.assertTrue(Param.get_param(NAVIGATION_ENTRY_SCOPE_MARKER))

    def test_direct_platform_exemption_survives_disabled_scenario_filter(self):
        Scenario = self.env["sc.product.scenario"]
        Param = self.env["ir.config_parameter"].sudo()
        menu = self.env.ref("smart_construction_core.menu_sc_runtime_user_management")
        entry = self.env["sc.product.scenario.entry"].sudo().search([
            ("menu_id", "=", menu.id),
        ], limit=1)
        self.assertTrue(entry)
        self.assertTrue(menu.sc_scenario_exempt)
        Scenario.initialize_navigation_entry_exemptions()
        self.assertTrue(menu.sc_scenario_exempt)
        index, menu_ids, _ = runtime_menu_scope(
            self.env,
            load_maintained_runtime_surface(self.env),
        )
        location = index[menu_ids[menu.id]]
        self.assertEqual(location["location"], "scenario")
        self.assertEqual(entry.scenario_id.code, "admin.organization")
        authority = {
            "primary_actions": [{
                "menu_id": menu.id,
                "action_id": menu.action.id,
                "menu_xmlid": menu.get_external_id()[menu.id],
            }],
        }
        filtered = filter_business_authority(
            authority,
            surface_index=index,
            enabled=business_states({business_key(entry.scenario_id.code): False}),
            entries=[],
            menu_xmlids_by_id=menu_ids,
            menu_xmlids_by_action={menu.action.id: [menu.get_external_id()[menu.id]]},
            company_id=self.env.company.id,
        )
        self.assertEqual(filtered["primary_actions"], authority["primary_actions"])
        self.assertTrue(
            filtered["scenario_composition"]["selected_by_menu"][str(menu.id)][
                "direct_exempt"
            ]
        )

    def test_bound_business_page_still_cannot_claim_direct_exemption(self):
        menu = self.env.ref("smart_construction_core.menu_sc_user_payment_apply")
        self.assertTrue(self.env["sc.product.scenario.entry"].sudo().search_count([
            ("menu_id", "=", menu.id),
        ]))
        menu.sc_scenario_exempt = False
        with self.assertRaises(ValidationError):
            menu.sc_scenario_exempt = True

    def test_direct_exemption_does_not_expand_native_menu_visibility(self):
        config_group = self.env.ref(
            "smart_construction_core.group_sc_cap_business_config_admin"
        )
        menu = self.env.ref("smart_construction_core.menu_sc_runtime_user_management")
        self.assertTrue(menu.sc_scenario_exempt)
        self.assertIn(config_group, menu.groups_id)
        principal = self.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Direct exemption ACL principal",
            "login": "direct.exemption.acl.principal",
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        self.assertNotIn(
            menu.id,
            self.env["ir.ui.menu"].with_user(principal)._visible_menu_ids(),
        )

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
            before = projection.load_maintained_runtime_surface(actor_env)
            before_scope = projection.runtime_menu_scope(actor_env, before)
        after = projection.load_maintained_runtime_surface(actor_env)
        self.assertEqual(after, before)
        self.assertEqual(projection.runtime_menu_scope(actor_env, after), before_scope)
        archived = next(row for row in after['scenarios'] if row['key'] == scenario.code)
        self.assertFalse(archived['active'])
        self.assertEqual(archived['bindings'][0]['menu_key'], menu.get_external_id()[menu.id])

    def _migration(self, version_dir):
        path = Path(__file__).resolve().parents[1] / (
            "migrations/%s/pre-migrate.py" % version_dir
        )
        return runpy.run_path(str(path))["migrate"]

    @staticmethod
    def _cursor(table_exists, xmlid_row=None):
        class Cursor:
            def __init__(self):
                self.queries = []
                self.row = None

            def execute(self, query, params=None):
                normalized = " ".join(str(query).split())
                self.queries.append((normalized, params))
                if normalized.startswith("SELECT to_regclass"):
                    self.row = (
                        ("public.sc_product_scenario_entry",)
                        if table_exists else (None,)
                    )
                elif normalized.startswith("SELECT res_id"):
                    self.row = xmlid_row
                else:
                    self.row = None

            def fetchone(self):
                return self.row

        return Cursor()

    def test_old_version_without_scenario_table_is_a_compatible_noop(self):
        for version_dir in ("17.0.0.180", "17.0.0.181"):
            for installed_version in ("17.0.0.172", "17.0.0.173"):
                with self.subTest(version_dir=version_dir, version=installed_version):
                    cursor = self._cursor(False)
                    self._migration(version_dir)(cursor, installed_version)
                    self.assertEqual(1, len(cursor.queries))
                    self.assertIn("to_regclass", cursor.queries[0][0])

    def test_modern_version_without_scenario_table_must_fail(self):
        for version_dir in ("17.0.0.180", "17.0.0.181"):
            for installed_version in (
                "17.0.0.174",
                "17.0.0.179",
                "17.0.0.180",
                "17.0.0.182",
            ):
                with self.subTest(version_dir=version_dir, version=installed_version):
                    cursor = self._cursor(False)
                    with self.assertRaisesRegex(
                        RuntimeError, "SCENARIO_ENTRY_TABLE_MISSING_INVALID_STATE"
                    ):
                        self._migration(version_dir)(cursor, installed_version)
                    self.assertEqual(1, len(cursor.queries))

    def test_unknown_version_without_scenario_table_must_fail(self):
        for version_dir in ("17.0.0.180", "17.0.0.181"):
            for installed_version in ("", None, "garbage", "17.0"):
                with self.subTest(version_dir=version_dir, version=installed_version):
                    cursor = self._cursor(False)
                    with self.assertRaisesRegex(
                        RuntimeError, "SCENARIO_ENTRY_TABLE_MISSING_UNKNOWN_VERSION"
                    ):
                        self._migration(version_dir)(cursor, installed_version)
                    self.assertEqual(1, len(cursor.queries))

    def test_existing_table_runs_original_migration_operations(self):
        cursor = self._cursor(True)
        self._migration("17.0.0.180")(cursor, "17.0.0.174")
        self.assertEqual(2, len(cursor.queries))
        self.assertIn("ALTER TABLE sc_product_scenario_entry", cursor.queries[-1][0])
        self.assertIn(
            "DROP CONSTRAINT IF EXISTS sc_product_scenario_entry_menu_uniq",
            cursor.queries[-1][0],
        )

        cursor = self._cursor(True, xmlid_row=(321,))
        self._migration("17.0.0.181")(cursor, "17.0.0.174")
        self.assertEqual(3, len(cursor.queries))
        self.assertIn("SELECT res_id", cursor.queries[1][0])
        self.assertIn("DELETE FROM sc_product_scenario_entry", cursor.queries[2][0])
        self.assertEqual((321,), cursor.queries[2][1])

    def test_existing_table_without_runtime_user_xmlid_keeps_entries(self):
        cursor = self._cursor(True, xmlid_row=None)
        self._migration("17.0.0.181")(cursor, "17.0.0.174")
        self.assertEqual(2, len(cursor.queries))
        self.assertFalse(any("DELETE FROM" in query for query, _params in cursor.queries))

    def test_runtime_user_management_keeps_scenario_identity_and_direct_access(self):
        menu = self.env.ref(
            "smart_construction_core.menu_sc_runtime_user_management",
            raise_if_not_found=False,
        )
        self.assertTrue(menu)
        entry = self.env["sc.product.scenario.entry"].sudo().search([
            ("menu_id", "=", menu.id),
        ], limit=1)
        self.assertTrue(entry)
        self.assertEqual(entry.scenario_id.code, "admin.organization")
        self.assertTrue(menu.sc_scenario_exempt)
