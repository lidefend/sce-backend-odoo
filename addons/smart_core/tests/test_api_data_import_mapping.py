"""Host regression for the native import preview adapter (no copied logic)."""
import ast
from pathlib import Path
import unittest
from typing import Any, List
from types import SimpleNamespace
import base64

SOURCE = Path(__file__).resolve().parents[1] / 'handlers/api_data_import.py'
module = ast.parse(SOURCE.read_text())
handler = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'ApiDataImportHandler')
method = next(node for node in handler.body if isinstance(node, ast.FunctionDef) and node.name == '_suggested_fields')
method.decorator_list = []
namespace = {'Any': Any, 'List': List}
exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), str(SOURCE), 'exec'), namespace)
suggest = namespace['_suggested_fields']


class NativeImportMappingTests(unittest.TestCase):
    def test_native_integer_column_positions(self):
        self.assertEqual(suggest(['id', 'name'], {0: ['id'], 1: ['name']}), ['id', 'name'])

    def test_json_positions_and_duplicate_headers(self):
        self.assertEqual(suggest(['Name', 'Name'], {'0': ['name'], '1': ['parent_id', 'name']}), ['name', 'parent_id/name'])

    def test_missing_matches_are_not_guessed_from_headers(self):
        self.assertEqual(suggest(['name', 'unknown'], {0: ['name']}), ['name', False])
        self.assertEqual(suggest(['name'], {'name': ['name']}), [False])
        self.assertEqual(suggest(['name'], False), [False])


class NativeImportPhaseTests(unittest.TestCase):
    def setUp(self):
        # Load the actual adapter, replacing only its Odoo/framework boundary.
        tree = ast.parse(SOURCE.read_text())
        tree.body = [node for node in tree.body if not isinstance(node, ast.ImportFrom)
                     or (node.level == 0 and node.module == 'typing')]
        namespace = {'__name__': 'native_import_adapter_test', 'BaseIntentHandler': object,
                     '_': lambda text: text, 'parse_bool': lambda value, default=False: bool(value),
                     'normalize_request_id': lambda value, prefix: value or prefix,
                     'failure_meta_for_reason': lambda reason: {}}
        for name in ['AccessError', 'UserError', 'ValidationError']:
            namespace[name] = type(name, (Exception,), {})
        for name in ['REASON_MISSING_PARAMS', 'REASON_NOT_FOUND', 'REASON_PERMISSION_DENIED',
                     'REASON_SYSTEM_ERROR', 'REASON_UNSUPPORTED_SOURCE', 'REASON_BUSINESS_RULE_FAILED']:
            namespace[name] = name
        exec(compile(tree, str(SOURCE), 'exec'), namespace)
        self.handler = namespace['ApiDataImportHandler']()
        self.handler.params = {}; self.handler.context = {}
        self.executions = []
        self.preview = {'headers': ['id', 'name'], 'matches': {0: ['id'], 1: ['name']},
                        'fields': [{'id': 'name', 'string': '名称', 'type': 'char'}],
                        'preview': [['external'], ['Example']], 'file_length': 3, 'options': {'has_headers': True}}
        importer = SimpleNamespace(parse_preview=lambda options, count: self.preview,
            execute_import=lambda *args, **kwargs: self.executions.append((args, kwargs)) or {'ids': [1, 2]})
        self.handler.env = {'x.sample': SimpleNamespace(check_access_rights=lambda operation: None),
                            'base_import.import': SimpleNamespace(create=lambda values: importer, get_fields_tree=lambda model: self.preview['fields'])}
        self.payload = {'params': {'model': 'x.sample', 'file_name': 'sample.csv',
                                   'file': base64.b64encode(b'id,name\na,A\nb,B\n').decode(), 'phase': 'inspect'}}

    def test_describe_needs_no_file_and_does_not_execute_rows(self):
        result = self.handler.handle({'params': {'model': 'x.sample', 'phase': 'describe'}})
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['native_fields'], self.preview['fields'])
        self.assertTrue(result['data']['native_options']['has_headers'])
        self.assertIn('has_headers', [field['name'] for field in result['data']['option_fields']])
        self.assertEqual(self.executions, [])

    def test_describe_preserves_native_templates(self):
        templates = [{'label': 'Template', 'template': '/sample/static/template.xlsx'}]
        self.handler.env['x.sample'].get_import_templates = lambda: templates
        result = self.handler.handle({'params': {'model': 'x.sample', 'phase': 'describe'}})
        self.assertEqual(result['data']['native_templates'], templates)

    def test_no_header_file_has_mappable_columns_and_correct_count(self):
        self.preview.update(headers=False, matches=False, file_length=2)
        self.payload['params']['options'] = {'has_headers': False}
        result = self.handler.handle(self.payload)
        self.assertEqual(result['data']['headers'], ['列 1', '列 2'])
        self.assertEqual(result['data']['mapping'], [False, False])
        self.assertEqual(result['data']['file_length'], 2)

    def test_inspect_exposes_native_fields_without_executing_rows(self):
        result = self.handler.handle(self.payload)
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['mapping'], ['id', 'name'])
        self.assertEqual(result['data']['native_fields'], self.preview['fields'])
        self.assertEqual(result['data']['file_length'], 2)
        self.assertFalse(result['data']['valid'])
        self.assertEqual(self.executions, [])

    def test_execute_cannot_override_explicit_dry_run(self):
        self.payload['params'].update(phase='execute', dry_run=True)
        self.assertFalse(self.handler.handle(self.payload)['ok'])
        self.assertEqual(self.executions, [])

    def test_native_row_location_retains_file_header_offset(self):
        result = self.handler._kernel_result({'messages': [{'type': 'error', 'message': 'required',
            'rows': {'from': 1, 'to': 1}, 'field': 'name'}]}, row_offset=2)
        self.assertEqual(result['messages'][0]['row_label'], '第 3 行')
        self.assertEqual(result['messages'][0]['field'], 'name')
        self.assertEqual(result['messages'][0]['message'], 'required')

    def test_unmatched_columns_can_be_mapped_before_validation(self):
        self.preview['matches'] = False
        result = self.handler.handle(self.payload)
        self.assertTrue(result['ok'])
        self.assertEqual(result['data']['mapping'], [False, False])
        self.payload['params'].update(phase='validate', fields=['id', 'name'])
        result = self.handler.handle(self.payload)
        self.assertTrue(result['data']['valid'])
        self.assertEqual(len(self.executions), 1)
        self.assertTrue(self.executions[0][1]['dryrun'])


if __name__ == '__main__':
    unittest.main()
