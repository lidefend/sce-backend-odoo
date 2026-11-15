"""Exercise the production batching and permission consumer without Odoo boot."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[2] / 'addons/smart_core/delivery/menu_service.py'
ENTRY_TARGET_SOURCE = Path(__file__).resolve().parents[2] / 'addons/smart_core/core/navigation_entry_target.py'
CLASS = next(node for node in ast.parse(SOURCE.read_text()).body if isinstance(node, ast.ClassDef) and node.name == 'MenuService')
METHODS = {'_action_xmlids_from_facts', '_route_entry_from_menu', '_native_visible_menu_paths', '_groups_authorize_current_user'}
_ENTRY_TARGET_SPEC = importlib.util.spec_from_file_location('navigation_entry_target_under_test', ENTRY_TARGET_SOURCE)
ENTRY_TARGET_MODULE = importlib.util.module_from_spec(_ENTRY_TARGET_SPEC)
_ENTRY_TARGET_SPEC.loader.exec_module(ENTRY_TARGET_MODULE)
namespace = {
    'MenuFactService': SimpleNamespace(ACTION_MODELS={'ir.actions.act_window', 'ir.actions.server'}),
    'build_web_surface_entry_target': ENTRY_TARGET_MODULE.build_web_surface_entry_target,
    'derive_entry_route': ENTRY_TARGET_MODULE.derive_entry_route,
}
exec(compile(ast.Module(body=[node for node in CLASS.body if isinstance(node, ast.FunctionDef) and node.name in METHODS], type_ignores=[]), str(SOURCE), 'exec'), namespace)


class MenuMetadataBatchTests(unittest.TestCase):
    def model(self, mapping=None, error=None):
        model = Mock()
        model.sudo.return_value = model
        model.browse.return_value = model
        model.get_external_id.side_effect = error
        model.get_external_id.return_value = mapping or {}
        return model

    def test_deduplicates_per_model_and_preserves_empty_native_choice(self):
        window = self.model({1: 'native.choice', 2: ''})
        server = self.model({1: 'server.choice'})
        actor = SimpleNamespace(env={'ir.actions.act_window': window, 'ir.actions.server': server})
        rows = [{'action_exists': True, 'action_model': model, 'action_id': rid}
                for model, rid in [('ir.actions.act_window', 1), ('ir.actions.act_window', 1),
                                   ('ir.actions.act_window', 2), ('ir.actions.server', 1)]]
        result = namespace['_action_xmlids_from_facts'](actor, rows)
        self.assertEqual(result, {('ir.actions.act_window', 1): 'native.choice',
                                  ('ir.actions.act_window', 2): '', ('ir.actions.server', 1): 'server.choice'})
        window.browse.assert_called_once_with([1, 2])
        server.browse.assert_called_once_with([1])

    def test_failed_batch_is_unresolved_and_does_not_persist(self):
        model = self.model(error=RuntimeError('metadata unavailable'))
        actor = SimpleNamespace(env={'ir.actions.act_window': model})
        rows = [{'action_exists': True, 'action_model': 'ir.actions.act_window', 'action_id': 1}]
        self.assertEqual(namespace['_action_xmlids_from_facts'](actor, rows), {})
        model.get_external_id.side_effect = None
        model.get_external_id.return_value = {1: 'recovered.choice'}
        self.assertEqual(namespace['_action_xmlids_from_facts'](actor, rows), {('ir.actions.act_window', 1): 'recovered.choice'})

    def test_batch_never_authorizes_denied_action(self):
        action = SimpleNamespace(id=1, _name='ir.actions.act_window', name='Example')
        model = self.model()
        model.exists.return_value = action
        actor = SimpleNamespace(env={'ir.actions.act_window': model},
                                _action_is_runtime_allowed=Mock(return_value=False), _record_xmlid=Mock())
        row = {'action_exists': True, 'action_model': 'ir.actions.act_window', 'action_id': 1, 'menu_id': 2}
        result = namespace['_route_entry_from_menu'](actor, row, route_kind='PRIMARY_NAV', source='test',
                                                     action_xmlids={('ir.actions.act_window', 1): 'known.action'})
        self.assertIsNone(result)
        actor._action_is_runtime_allowed.assert_called_once_with(action, 'read')
        actor._record_xmlid.assert_not_called()

    def test_empty_batch_value_does_not_trigger_singleton_query(self):
        action = SimpleNamespace(id=1, _name='ir.actions.act_window', name='Example')
        model = self.model()
        model.exists.return_value = action
        actor = SimpleNamespace(env={'ir.actions.act_window': model},
                                _action_is_runtime_allowed=Mock(return_value=True), _record_xmlid=Mock(return_value='singleton'))
        row = {'action_exists': True, 'action_model': 'ir.actions.act_window', 'action_id': 1, 'menu_id': 2}
        result = namespace['_route_entry_from_menu'](actor, row, route_kind='PRIMARY_NAV', source='test',
                                                     action_xmlids={('ir.actions.act_window', 1): ''})
        self.assertEqual(result['action_xmlid'], '')
        actor._record_xmlid.assert_not_called()
        result = namespace['_route_entry_from_menu'](actor, row, route_kind='PRIMARY_NAV', source='test', action_xmlids={})
        self.assertEqual(result['action_xmlid'], 'singleton')
        actor._record_xmlid.assert_called_once_with(action)

    def test_path_batch_keeps_native_model_identity_missing_and_duplicate_refs(self):
        data = Mock()
        refs = {'module.a': ('ir.ui.menu', 1), 'module.alias': ('ir.ui.menu', 1),
                'module.missing': (False, False), 'module.wrong': ('res.users', 1),
                'module.dangling': ('ir.ui.menu', 2)}
        data._xmlid_to_res_model_res_id.side_effect = lambda key, **kwargs: refs[key]
        menus = Mock()
        menus.browse.return_value.exists.return_value = [SimpleNamespace(id=1, complete_name=' Parent / Child ')]
        actor = SimpleNamespace(env={'ir.model.data': data, 'ir.ui.menu': menus})
        result = namespace['_native_visible_menu_paths'](actor, [*refs, 'module.a', ''])
        self.assertEqual(result, {'module.a': 'Parent / Child', 'module.alias': 'Parent / Child',
                                 'module.missing': '', 'module.wrong': '', 'module.dangling': '', '': ''})
        menus.browse.assert_called_once_with([1, 2])
        menus.browse.return_value.exists.assert_called_once_with()
        self.assertEqual(data._xmlid_to_res_model_res_id.call_count, len(refs))

    def test_path_batch_access_failure_remains_unresolved_without_sudo(self):
        data = Mock()
        data._xmlid_to_res_model_res_id.return_value = ('ir.ui.menu', 1)
        menus = Mock()
        menus.browse.return_value.exists.side_effect = PermissionError('denied')
        actor = SimpleNamespace(env={'ir.model.data': data, 'ir.ui.menu': menus})
        self.assertEqual(namespace['_native_visible_menu_paths'](actor, ['module.a']), {})
        menus.sudo.assert_not_called()
        data.sudo.assert_not_called()



class GroupXmlidReuseTests(unittest.TestCase):
    class Records:
        def __init__(self, owner, ids):
            self.owner, self.ids = owner, ids
        def __bool__(self): return bool(self.ids)
        def __iter__(self): return iter(self.owner.records[i] for i in self.ids)
        def sudo(self): return self
        def browse(self, ids): return type(self)(self.owner, ids)
        def get_external_id(self):
            self.owner.batches.append(list(self.ids))
            if self.owner.fail_batch: raise RuntimeError('unavailable')
            return {i: self.owner.choices[i][0] if self.owner.choices[i] else '' for i in self.ids}

    def setUp(self):
        self.choices = {1: ['native.first', 'alias.second'], 2: [], 3: ['native.third']}
        self.records = {i: SimpleNamespace(id=i) for i in self.choices}
        self.batches, self.singles = [], []
        self.fail_batch = False
        self.allowed = set()
        def singleton(group):
            self.singles.append(group.id)
            return self.choices[group.id][0] if self.choices[group.id] else ''
        self.user = SimpleNamespace(groups_id=[], has_group=Mock(side_effect=lambda xid: xid in self.allowed))
        self.actor = SimpleNamespace(env=SimpleNamespace(user=self.user), _record_xmlid=singleton)

    def authorize(self, ids, actor=None):
        return namespace['_groups_authorize_current_user'](actor or self.actor, self.Records(self, ids))

    def test_only_missing_metadata_is_batched_and_authority_remains_live(self):
        self.assertFalse(self.authorize([1, 2]))
        self.allowed.add('native.first')
        self.assertTrue(self.authorize([1, 2]))
        self.allowed.clear()
        self.assertFalse(self.authorize([1, 2, 3]))
        self.assertEqual(self.batches, [[1, 2], [3]])
        self.assertEqual(self.singles, [])
        self.assertNotIn('alias.second', [c.args[0] for c in self.user.has_group.call_args_list])
        self.assertGreaterEqual(self.user.has_group.call_count, 4)

    def test_empty_xmlid_is_cached_but_intersection_is_live(self):
        # Hashable identity records model the original recordset intersection.
        self.records[2] = 2
        class Group(int):
            @property
            def id(self): return int(self)
        self.records[2] = Group(2)
        self.assertFalse(self.authorize([2]))
        self.user.groups_id = [self.records[2]]
        self.assertTrue(self.authorize([2]))
        self.user.groups_id = []
        self.assertFalse(self.authorize([2]))
        self.assertEqual(self.batches, [[2]])
        self.user.has_group.assert_not_called()

    def test_batch_failure_uses_singletons_then_retries_after_recovery(self):
        self.fail_batch = True
        self.allowed.add('native.first')
        self.assertTrue(self.authorize([1, 2]))
        self.assertEqual(self.actor._group_xmlid_cache, {})
        self.assertEqual(self.singles, [1])
        self.fail_batch = False
        self.assertTrue(self.authorize([1, 2]))
        self.assertEqual(self.batches, [[1, 2], [1, 2]])
        self.assertEqual(self.actor._group_xmlid_cache, {1: 'native.first', 2: ''})

    def test_instances_do_not_share_metadata(self):
        self.authorize([1])
        self.choices[1] = ['changed.native']
        other = SimpleNamespace(env=self.actor.env, _record_xmlid=self.actor._record_xmlid)
        self.allowed.add('changed.native')
        self.assertTrue(self.authorize([1], other))
        self.assertEqual(self.batches, [[1], [1]])

if __name__ == '__main__':
    unittest.main()
