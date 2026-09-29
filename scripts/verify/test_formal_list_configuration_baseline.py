"""Execute the shipped P1 hook with its real P0 composer and bounded ORM doubles."""
import ast
from copy import deepcopy
import importlib.util
import logging
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('orchestrator_tests', ROOT / 'addons/smart_core/tests/test_view_orchestrator.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
helpers._load_orchestrator()
source = ROOT / 'addons/smart_construction_core/core_extension.py'
node = next(n for n in ast.parse(source.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == 'smart_core_finalize_projected_contract_data')
namespace = {'_logger': logging.getLogger(__name__), '_user_confirmed_formal_list_action_ids': lambda env: {775}}
exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
finalize = namespace[node.name]


class Record:
    def sudo(self): return self
    def browse(self, _): return self
    def exists(self): return True
    def with_context(self, **_): return self
    def with_user(self, _): return self
    def _generate_from_fields_view_get(self, *_): return self
    def get_contract_api(self, **_): return {'columns': [], 'columns_schema': []}
    def fields_get(self):
        return {'name': {'string': '编号', 'type': 'char'}, 'request_amount_display': {'type': 'monetary'}, 'note': {'type': 'char'}}


class FormalListConfigurationTest(unittest.TestCase):
    def run_hook(self, columns=None, rows=None, prior_schema=None):
        action = Record()
        action.res_model = 'payment.request'
        action.view_id = Record()
        action.view_id.arch_db = '<tree><field name="name"/><field name="request_amount_display" sum="申请付款金额合计"/><field name="note" optional="hide"/></tree>'
        class Env(dict): user = object()
        env = Env({'ir.actions.act_window': action, 'app.view.config': Record(), 'payment.request': Record()})
        data = {'model': 'payment.request', 'view_type': 'tree', 'action_id': 775, 'fields': {}, 'views': {}}
        if columns is not None:
            env['ui.business.config.contract'] = helpers._ConfigModel({'view_orchestration': {'views': {'tree': {'columns': rows or [{'name': name, 'sequence': i + 1} for i, name in enumerate(columns)]}}}})
            data['list_profile'] = {'columns': columns, 'fact_columns': columns, 'column_policy': {'reason': 'business_list_config_contract_authoritative'}}
        if prior_schema:
            data['views'] = {'tree': {'columns_schema': prior_schema}}
        before = deepcopy(data)
        result = finalize(env, data, {'view_type': 'tree'})
        self.assertEqual(data, before, 'source must not be mutated')
        return result

    def test_label_only_keeps_native_schema_and_locks(self):
        base = self.run_hook()
        columns = base['views']['tree']['columns']
        updated = self.run_hook(columns, [{'name': name, 'sequence': i + 1, **({'label': '改后编号'} if name == 'name' else {})} for i, name in enumerate(columns)])
        schema = updated['views']['tree']['columns_schema']
        expected = deepcopy(base['views']['tree']['columns_schema'])
        expected[0].update(label='改后编号', string='改后编号')
        self.assertEqual(schema, expected)
        self.assertEqual(updated['list_profile']['preference_policy'], base['list_profile']['preference_policy'])
        self.assertEqual(schema[1]['value_field'], 'amount')
        self.assertEqual(schema[1]['sort_field'], 'amount')
        self.assertEqual(schema[2]['optional'], 'hide')

    def test_full_configuration_can_reduce_and_reorder_columns(self):
        result = self.run_hook(['note', 'name'])
        self.assertEqual(result['views']['tree']['columns'], ['note', 'name'])
        self.assertEqual([r['name'] for r in result['views']['tree']['columns_schema']], ['note', 'name'])
        self.assertEqual(result['list_profile']['preference_policy']['locked_columns'], ['note', 'name'])
        self.assertFalse(result['list_profile']['preference_policy']['allow_visibility'])

    def test_explicit_visibility_is_still_applied(self):
        result = self.run_hook(['name', 'note'], [{'name': 'name', 'sequence': 1}, {'name': 'note', 'sequence': 2, 'visible': True}])
        self.assertEqual(result['views']['tree']['columns_schema'][1]['optional'], 'show')

    def test_non_native_extension_metadata_is_preserved(self):
        row = {'name': 'extra', 'type': 'selection', 'sort_field': 'amount', 'value_field': 'amount',
               'readonly': True, 'required': True, 'selection': [['one', 'One']], 'optional': 'hide'}
        result = self.run_hook(['name', 'extra'], prior_schema=[row])
        self.assertEqual(result['views']['tree']['columns_schema'][1], row)

    def test_explicit_editability_overrides_do_not_erase_other_metadata(self):
        row = {'name': 'extra', 'type': 'char', 'readonly': True, 'required': False, 'sort_field': 'code'}
        result = self.run_hook(['extra'], [{'name': 'extra', 'readonly': False, 'required': True}], [row])
        self.assertEqual(result['views']['tree']['columns_schema'], [{**row, 'readonly': False, 'required': True}])


if __name__ == '__main__': unittest.main()
