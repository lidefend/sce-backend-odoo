"""Prove startup metadata batching preserves native facts and contract values."""
import copy
import datetime
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
        stored_digest = cfg.meta_info['source_digest']
        # Change action metadata that no menu projects: the source digest moves,
        # the projection tree does not.
        self.env['ir.actions.act_window'].create({
            'name': 'Digest-only metadata fixture',
            'res_model': 'res.partner',
            'view_mode': 'tree',
        })
        self.assertTrue(model._menu_metadata_changed_since(cfg))
        same = model._get_or_generate_from_menus(scene='web')
        self.assertEqual(same.id, cfg.id)
        self.assertEqual((same.version, same.config_hash, same.menu_tree), before)
        self.assertNotEqual(same.meta_info['source_digest'], stored_digest)
        self.assertEqual(same.meta_info['source_digest'], model._menu_source_digest())
        # A second lookup must consume the validated projection, not rebuild it.
        with patch.object(type(model), '_generate_from_menus', side_effect=AssertionError('repeated rebuild')):
            self.assertEqual(model._get_or_generate_from_menus(scene='web').id, cfg.id)

    def test_same_transaction_edit_after_generation_invalidates_projection(self):
        model = self.env['app.menu.config']
        menu = self.env['ir.ui.menu'].create({'name': 'Same-transaction fixture', 'active': True})
        cfg = model._generate_from_menus(scene='web')
        self.assertFalse(model._menu_metadata_changed_since(cfg))
        menu.write({'name': 'Same-transaction fixture renamed'})
        # The timestamp watermark cannot see this edit: both writes share the
        # transaction clock, so no source row is strictly newer than it.
        self.assertEqual(menu.write_date, cfg.last_generated)
        self.assertEqual(self.env['ir.ui.menu'].sudo().with_context(
            **{'ir.ui.menu.full_list': True, 'active_test': False}
        ).search_count([('write_date', '>', cfg.last_generated)]), 0)
        self.assertTrue(model._menu_metadata_changed_since(cfg))
        regenerated = model._get_or_generate_from_menus(scene='web')
        names = []

        def collect(nodes):
            for node in nodes:
                names.append(node['name'])
                collect(node.get('children') or [])

        collect(regenerated.menu_tree)
        self.assertIn('Same-transaction fixture renamed', names)

    def test_delayed_commit_clock_edit_invalidates_projection(self):
        model = self.env['app.menu.config']
        menu = self.env['ir.ui.menu'].create({'name': 'Delayed-commit fixture', 'active': True})
        cfg = model._generate_from_menus(scene='web')
        older = cfg.last_generated - datetime.timedelta(minutes=5)
        # A transaction that began before generation commits its edit with the
        # earlier clock, so a strict `>` comparison is blind to it.
        with patch.object(self.env.cr, 'now', return_value=older):
            menu.write({'name': 'Delayed-commit fixture renamed'})
        self.assertLess(menu.write_date, cfg.last_generated)
        self.assertFalse(self.env['ir.ui.menu'].sudo().with_context(
            **{'ir.ui.menu.full_list': True, 'active_test': False}
        ).search([('write_date', '>', cfg.last_generated)], limit=1))
        self.assertTrue(model._menu_metadata_changed_since(cfg))

    def test_menu_deletion_invalidates_projection(self):
        model = self.env['app.menu.config']
        menu = self.env['ir.ui.menu'].create({'name': 'Deletion fixture', 'active': True})
        cfg = model._generate_from_menus(scene='web')
        self.assertFalse(model._menu_metadata_changed_since(cfg))
        menu.unlink()
        self.assertTrue(model._menu_metadata_changed_since(cfg))

    def test_menu_xmlid_rename_invalidates_projection(self):
        model = self.env['app.menu.config']
        menu = self.env['ir.ui.menu'].create({'name': 'XML-ID fixture', 'active': True})
        alias = self.env['ir.model.data'].create({
            'module': 'performance_test',
            'name': 'menu_xmlid_fixture',
            'model': 'ir.ui.menu',
            'res_id': menu.id,
        })
        cfg = model._generate_from_menus(scene='web')
        self.assertFalse(model._menu_metadata_changed_since(cfg))
        # The projection persists xml_id/module; ir.ui.menu itself is unchanged.
        alias.write({'name': 'menu_xmlid_fixture_renamed'})
        self.assertTrue(model._menu_metadata_changed_since(cfg))

    def test_legacy_row_without_digest_is_rebuilt_once(self):
        model = self.env['app.menu.config']
        cfg = model._generate_from_menus(scene='web')
        meta = dict(cfg.meta_info)
        meta.pop('source_digest')
        cfg.write({'meta_info': meta})
        self.assertTrue(model._menu_metadata_changed_since(cfg))
        rebuilt = model._get_or_generate_from_menus(scene='web')
        self.assertTrue(rebuilt.meta_info['source_digest'])
        self.assertFalse(model._menu_metadata_changed_since(rebuilt))

    def test_menu_edit_during_generation_remains_newer_than_snapshot(self):
        model = self.env['app.menu.config']
        original_hash = type(model)._hash
        cursor = self.env.cr
        observed = {}

        def edit_after_source_read(recordset, payload):
            source_clock = recordset.env.cr.now()
            observed['source_clock'] = source_clock
            # Odoo stamps log-access columns with the writing transaction's
            # clock, so a concurrent editor is one that writes under a later
            # clock than the generating transaction.
            with patch.object(cursor, 'now',
                              return_value=source_clock + datetime.timedelta(microseconds=1)):
                observed['edit'] = recordset.env['ir.ui.menu'].create({
                    'name': 'Concurrent metadata fixture',
                    'active': True,
                })
            return original_hash(recordset, payload)

        with patch.object(type(model), '_hash', edit_after_source_read):
            cfg = model._generate_from_menus(scene='web')
        edit = observed['edit']
        # The watermark and the source rows share the transaction clock; a
        # wall-clock watermark would sit after every row this transaction
        # writes and would hide edits made during generation.
        self.assertEqual(cfg.last_generated, observed['source_clock'])
        self.assertGreater(edit.write_date, cfg.last_generated)
        self.assertTrue(model._menu_metadata_changed_since(cfg))
