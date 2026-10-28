"""Focused tests for the read projection; no database or wizard writes."""
import ast
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'addons/smart_construction_core/services/project_stage_requirements_read.py'
spec = importlib.util.spec_from_file_location('stage_read', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StageRequirementsReadTest(unittest.TestCase):
    def project(self, items):
        p = Mock(id=17, display_name='Project A', lifecycle_state='done')
        p.sc_get_stage_requirements.return_value = items
        p._fields = {'lifecycle_state': Mock()}
        p._fields['lifecycle_state'].convert_to_export.return_value = 'Finished'
        return p

    def test_complete_collection_and_no_handling_actions(self):
        p = self.project([{'title': str(i), 'required': True, 'done': False, 'action_ref': 'private'} for i in range(5)])
        result = module.project_stage_requirements_payload(p)
        p.sc_get_stage_requirements.assert_called_once_with(limit=0)
        self.assertEqual(len(result['items']), 5)
        self.assertEqual(result['stage'], {'value': 'done', 'label': 'Finished'})
        self.assertEqual(result['project'], {'id': 17, 'name': 'Project A'})
        self.assertNotIn('action_ref', result['items'][0])
        self.assertEqual(result['return_path'], '/r/project.project/17')

    def test_empty_is_success_only_after_read(self):
        result = module.project_stage_requirements_payload(self.project([]))
        self.assertEqual(result['items'], [])
        self.assertTrue(result['labels']['empty'])

    def test_read_denial_is_not_empty(self):
        p = self.project([])
        p.sc_get_stage_requirements.side_effect = PermissionError('denied')
        with self.assertRaises(PermissionError): module.project_stage_requirements_payload(p)

    def test_unexpected_error_is_not_empty(self):
        p = self.project([])
        p.sc_get_stage_requirements.side_effect = RuntimeError('failed')
        with self.assertRaises(RuntimeError): module.project_stage_requirements_payload(p)

    def actual_read_method(self):
        tree = ast.parse((ROOT / 'addons/smart_construction_core/models/core/project_core.py').read_text())
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'sc_get_stage_requirements')
        ns = {}; exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual_project_read_method', 'exec'), ns)
        return ns['sc_get_stage_requirements']

    def test_actual_method_checks_project_and_selects_current_stage(self):
        p = Mock(id=17, lifecycle_state='done')
        items = [Mock(name='Requirement', required=True, action_xmlid=False) for _ in range(5)]
        for i in items: i.name = 'Requirement'
        model = Mock(); model.search.return_value = items
        p.env = {'sc.project.stage.requirement.item': model}
        p._sc_is_requirement_done.return_value = False
        result = self.actual_read_method()(p, limit=0)
        p.check_access_rights.assert_called_once_with('read')
        p.check_access_rule.assert_called_once_with('read')
        model.search.assert_called_once_with([('active', '=', True), ('lifecycle_state', '=', 'done')], order='sequence, id')
        self.assertEqual(len(result), 5)
        self.assertTrue(all(r['payload']['project_id'] == 17 and r['done'] is False for r in result))

    def test_actual_method_denial_precedes_item_query(self):
        for check in ['check_access_rights', 'check_access_rule']:
            p = Mock(id=17, lifecycle_state='done'); item_model = Mock()
            p.env = {'sc.project.stage.requirement.item': item_model}
            getattr(p, check).side_effect = PermissionError('denied')
            with self.assertRaises(PermissionError): self.actual_read_method()(p, limit=0)
            item_model.search.assert_not_called()

    def handler(self, params, available=True):
        tree = ast.parse((ROOT / 'addons/smart_construction_core/handlers/project_stage_requirements_read.py').read_text())
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'handle')
        ns = {'AccessError': PermissionError, 'project_stage_requirements_payload': Mock(return_value={'items': []})}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'actual_stage_handler', 'exec'), ns)
        h = Mock(params=params, context={'company_id': 3})
        h._resolve_project_scope.return_value = Mock(available=available, project='authorized-project')
        return ns['handle'], h, ns['project_stage_requirements_payload']

    def test_handler_uses_authorized_resolution_before_projection(self):
        handle, h, projection = self.handler({'project_id': 17})
        self.assertEqual(handle(h), {'ok': True, 'data': {'items': []}})
        h._resolve_project_scope.assert_called_once_with({'project_id': 17}, {'company_id': 3})
        projection.assert_called_once_with('authorized-project')

    def test_handler_denial_never_reads_or_returns_empty(self):
        handle, h, projection = self.handler({'project_id': 17}, available=False)
        with self.assertRaises(PermissionError): handle(h)
        projection.assert_not_called()

    def test_handler_rejects_missing_or_malformed_explicit_project_without_context_fallback(self):
        for project_id in (None, True, 0, -1, '17', 17.5):
            handle, h, projection = self.handler({'project_id': project_id})
            with self.assertRaises(PermissionError): handle(h)
            h._resolve_project_scope.assert_not_called()
            projection.assert_not_called()

    def contract(self):
        return {'dataContract': {'mainData': {'id': 17}}, 'actionContract': {'actionRuleList': [
            {'actionId': 'stage', 'sourceWidgetId': 'occurrence1', 'button': {'name': 'action_view_stage_requirements', 'type': 'object'}, 'allowed': False, 'visible': {'states': ['done']}},
            {'actionId': 'other', 'button': {'name': 'action_other', 'type': 'object'}}]}}

    def test_only_declared_action_changes_without_permissions_or_input_mutation(self):
        c = self.contract(); before = copy.deepcopy(c)
        result = module.stage_requirements_navigation(c, {'source_contract': {'model': 'project.project'}})
        self.assertEqual(c, before)
        stage = result['actionContract']['actionRuleList'][0]
        self.assertEqual(stage['button'], {})
        self.assertEqual(stage['target'], {'url': '/project-stage-requirements/17', 'target': 'self'})
        self.assertFalse(stage['allowed'])
        self.assertEqual(stage['visible'], before['actionContract']['actionRuleList'][0]['visible'])
        self.assertEqual(stage['sourceWidgetId'], 'occurrence1')
        self.assertEqual(result['actionContract']['actionRuleList'][1], before['actionContract']['actionRuleList'][1])

    def test_create_and_other_models_remain_unchanged(self):
        for model, record in [('other.model', 17), ('project.project', None), ('project.project', 0), ('project.project', True)]:
            c = self.contract(); c['dataContract']['mainData']['id'] = record
            self.assertIsNone(module.stage_requirements_navigation(c, {'source_contract': {'model': model}}))

    def test_project_identity_is_not_reused(self):
        c = self.contract(); c['dataContract']['mainData']['id'] = 28
        out = module.stage_requirements_navigation(c, {'source_contract': {'model': 'project.project'}})
        self.assertEqual(out['actionContract']['actionRuleList'][0]['target']['url'], '/project-stage-requirements/28')

class ExistingSampleSelectionTest(unittest.TestCase):
    def resolve(self, states):
        import json
        import os
        from types import SimpleNamespace
        from unittest.mock import patch
        source = (ROOT / 'scripts/verify/frontend_delivery_hardening_runtime_ids.py').read_text()
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'resolve_targets')
        names = ['fe_project_a', 'fe_project_b', 'fe_project_lifecycle']
        refs = {name: SimpleNamespace(id=i + 1, lifecycle_state=state) for i, (name, state) in enumerate(zip(names, states))}
        refs.update(fe_user_config_admin=SimpleNamespace(id=41), fe_company_a=SimpleNamespace(id=1), fe_project_c=SimpleNamespace(id=9))
        projects = Mock()
        projects.with_user.return_value = projects
        projects.with_context.return_value = projects
        projects.search.side_effect = lambda domain, limit: next((r for r in refs.values() if hasattr(r, 'lifecycle_state') and r.id == domain[0][2]), False)
        env = Mock()
        env.ref.side_effect = lambda xmlid, **kw: refs.get(xmlid.rsplit('.', 1)[-1], False)
        class Environment:
            ref = env.ref
            def __getitem__(self, key):
                if key != 'project.project': raise AssertionError(key)
                return projects
        ns = {'env': Environment(), 'os': os, 'json': json, 'PROJECT_MENU_XMLID': 'menu', 'PROJECT_ACTION_XMLID': 'action',
              'target': lambda menu, xmlid, **kw: {'record_xmlid': xmlid}}
        exec(compile(ast.Module(body=[node], type_ignores=[]), 'sample_selector', 'exec'), ns)
        with patch.dict(os.environ, {'SC_ACCEPTANCE_RECORD_SCOPE': 'stage_requirements'}), patch('builtins.print'):
            result = ns['resolve_targets']('fixture')
        projects.with_user.assert_called_once_with(refs['fe_user_config_admin'])
        projects.with_context.assert_called_once_with(allowed_company_ids=[1])
        self.assertEqual(projects.search.call_count, 3)
        for call in projects.search.call_args_list:
            self.assertEqual(call.args[0][1], ('company_id', '=', 1))
            self.assertEqual(call.kwargs['limit'], 1)
        return result

    def test_existing_non_draft_is_selected_without_state_changes(self):
        result = self.resolve(['draft', 'done', 'draft'])
        self.assertTrue(result['project']['record_xmlid'].endswith('.fe_project_b'))

    def test_draft_only_inventory_blocks_instead_of_direct_navigation(self):
        with self.assertRaisesRegex(AssertionError, 'No authorized non-draft'):
            self.resolve(['draft', 'draft', 'draft'])

if __name__ == '__main__': unittest.main()
