"""Prove startup metadata batching preserves native facts and contract values."""
import copy
from unittest.mock import patch
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.smart_core.handlers import system_init
from odoo.addons.smart_core.delivery.menu_service import MenuService


def previous_strip(payload):
    if isinstance(payload, list):
        return [previous_strip(item) for item in payload]
    if not isinstance(payload, dict):
        return payload
    return {key: previous_strip(value) for key, value in payload.items()
            if key not in {'ui_base_contract', 'ui_base_contract_ref'}}


@tagged('post_install', '-at_install', 'sc_gate')
class TestStartupPerformanceContract(TransactionCase):
    def test_nested_cleanup_preserves_values_and_independent_copies(self):
        shared = {'values': [None, False, 0, 'x', [], {'ui_base_contract': 'removed', 'visible': True}]}
        source = {'a': shared, 'b': shared, 'ui_base_contract_ref': 'removed'}
        before = copy.deepcopy(source)
        actual = system_init._strip_ui_base_contract_for_frontend(source)
        self.assertEqual(actual, previous_strip(source))
        self.assertEqual(source, before)
        self.assertIsNot(actual['a'], actual['b'])
        actual['a']['values'].append('mutation')
        self.assertNotEqual(actual['a'], actual['b'])
        self.assertEqual(source, before)

    def test_actual_startup_input_matches_previous_projection(self):
        original = system_init._strip_ui_base_contract_for_frontend
        observed = []

        def compare(payload):
            # Patch only the root call; recursion uses the real implementation.
            with patch.object(system_init, '_strip_ui_base_contract_for_frontend', original):
                before = copy.deepcopy(payload)
                expected = previous_strip(payload)
                result = original(payload)
                self.assertEqual(result, expected)
                self.assertEqual(payload, before)
                observed.append(True)
                return result

        with patch.object(system_init, '_strip_ui_base_contract_for_frontend', compare):
            reply = system_init.SystemInitHandler(env=self.env).handle(payload={'params': {}})
        self.assertTrue(reply.ok)
        self.assertEqual(observed, [True])

    def test_action_xmlid_batch_matches_native_selection_and_refreshes(self):
        action = self.env['ir.actions.act_window'].create({'name': 'Performance metadata test', 'res_model': 'res.partner', 'view_mode': 'tree'})
        aliases = self.env['ir.model.data'].create([
            {'module': 'performance_test', 'name': 'first_alias', 'model': action._name, 'res_id': action.id},
            {'module': 'performance_test', 'name': 'second_alias', 'model': action._name, 'res_id': action.id},
        ])
        service = MenuService(self.env)
        rows = [{'action_model': action._name, 'action_id': action.id, 'action_exists': True}]
        self.assertEqual(service._action_xmlids_from_facts(rows)[(action._name, action.id)],
                         service._record_xmlid(action))
        aliases.unlink()
        # No cache persists across calls, including the valid empty XML-ID.
        self.assertEqual(service._action_xmlids_from_facts(rows)[(action._name, action.id)], '')


    def test_native_menu_path_batch_matches_refs_and_refreshes(self):
        parent = self.env['ir.ui.menu'].create({'name': 'Performance parent'})
        child = self.env['ir.ui.menu'].create({'name': 'Performance child', 'parent_id': parent.id, 'active': False})
        self.env['ir.model.data'].create([
            {'module': 'performance_test', 'name': 'menu_path', 'model': 'ir.ui.menu', 'res_id': child.id},
            {'module': 'performance_test', 'name': 'menu_alias', 'model': 'ir.ui.menu', 'res_id': child.id},
        ])
        service = MenuService(self.env)
        keys = ['performance_test.menu_path', 'performance_test.menu_alias', 'base.user_admin', 'performance_test.absent']
        self.assertEqual(service._native_visible_menu_paths(keys), {key: service._native_visible_menu_path(key) for key in keys})
        parent.name = 'Renamed parent'
        self.assertEqual(service._native_visible_menu_paths(keys), {key: service._native_visible_menu_path(key) for key in keys})
        child.unlink()
        self.assertEqual(service._native_visible_menu_paths(keys), {key: service._native_visible_menu_path(key) for key in keys})

    def test_scene_reference_batch_preserves_native_resolution_diagnostics(self):
        from odoo.addons.smart_core.governance import scene_normalizer
        action = self.env['ir.actions.act_window'].create({'name': 'Scene metadata test', 'res_model': 'res.partner', 'view_mode': 'tree'})
        menu = self.env['ir.ui.menu'].create({'name': 'Scene metadata menu'})
        self.env['ir.model.data'].create([
            {'module': 'performance_test', 'name': 'scene_action', 'model': action._name, 'res_id': action.id},
            {'module': 'performance_test', 'name': 'scene_menu', 'model': menu._name, 'res_id': menu.id},
        ])
        source = [{'code': 'test.scene', 'target': {'action_xmlid': 'performance_test.scene_action',
                    'action_id': action.id + 1, 'menuXmlid': 'performance_test.scene_menu'}},
                  {'code': 'test.missing', 'target': {'action_xmlid': 'performance_test.absent'}}]
        previous, current = copy.deepcopy(source), copy.deepcopy(source)
        previous_errors, current_errors = [], []
        with patch.object(scene_normalizer, '_resolve_xmlids_batch', return_value={}):
            scene_normalizer._normalize_scene_targets(self.env, previous, {}, previous_errors)
        scene_normalizer._normalize_scene_targets(self.env, current, {}, current_errors)
        self.assertEqual(current, previous)
        self.assertEqual(current_errors, previous_errors)
        self.assertEqual(current[0]['target']['action_id'], action.id)
        self.assertEqual(current[0]['target']['menu_id'], menu.id)

    def test_unchanged_menu_projection_advances_freshness_without_version_bump(self):
        model = self.env['app.menu.config']
        cfg = model._generate_from_menus(scene='web')
        before = (cfg.version, cfg.config_hash, copy.deepcopy(cfg.menu_tree))
        cfg.write({'last_generated': '2000-01-01 00:00:00'})
        self.assertTrue(model._menu_metadata_changed_since(cfg))
        same = model._get_or_generate_from_menus(scene='web')
        self.assertEqual(same.id, cfg.id)
        self.assertEqual((same.version, same.config_hash, same.menu_tree), before)
        self.assertGreater(str(same.last_generated), '2000-01-01 00:00:00')
        # A second lookup must consume the validated projection, not rebuild it.
        with patch.object(type(model), '_generate_from_menus', side_effect=AssertionError('repeated rebuild')):
            self.assertEqual(model._get_or_generate_from_menus(scene='web').id, cfg.id)

    def test_menu_edit_during_generation_remains_newer_than_snapshot(self):
        model = self.env['app.menu.config']
        original_hash = type(model)._hash
        edits = []
        def edit_after_source_read(recordset, payload):
            edits.append(self.env['ir.ui.menu'].create({'name': 'Concurrent metadata fixture', 'active': True}))
            return original_hash(recordset, payload)
        with patch.object(type(model), '_hash', edit_after_source_read):
            cfg = model._generate_from_menus(scene='web')
        self.assertEqual(len(edits), 1)
        self.assertGreater(edits[0].write_date, cfg.last_generated)
        self.assertTrue(model._menu_metadata_changed_since(cfg))
