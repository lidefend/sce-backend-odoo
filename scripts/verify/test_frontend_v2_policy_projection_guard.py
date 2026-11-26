"""The local refusal marker must remain visible and never become wire authority."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.verify import frontend_v2_policy_projection_guard as guard


class RefusalMarkerGuardTest(unittest.TestCase):
    def run_guard(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = guard.main()
        return result, output.getvalue()

    def test_existing_consumed_marker_passes(self):
        result, output = self.run_guard()
        self.assertEqual(result, 0, output)

    def test_unconsumed_marker_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'consumer.ts'
            path.write_text('export const value = false;')
            with patch.object(guard, 'ACTION_SEMANTICS_INVALID_CONSUMERS', (path,)), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('whitelisted but unread', output)

    def test_delete_policy_token_must_have_a_backend_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'delete_policy.py'
            path.write_text('DELETE_POLICY_ALLOWED = "DELETE_POLICY_ALLOWED"')
            with patch.object(guard, 'DELETE_POLICY_PRODUCERS', (path,)), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('is not declared by the backend delete policy producers', output)

    def test_backend_identity_token_must_have_a_backend_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'assembler.py'
            path.write_text('IDENTITY_PREFIX = "unrelated_identity"')
            with patch.object(guard, 'BACKEND_IDENTITY_PRODUCERS', (path,)), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('is not declared by the backend identity producers', output)

    def test_relation_domain_token_must_have_a_backend_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'assembler.py'
            path.write_text('UNRELATED = True')
            with patch.object(guard, 'RELATION_DOMAIN_PRODUCERS', (path,)), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('is not declared by the backend relation domain producers', output)

    def test_native_relation_metadata_schema_rejects_malformed_snapshots(self):
        import jsonschema
        schema = json.loads(guard.BACKEND_SCHEMA.read_text())['$defs']['dataMeta']['properties']
        jsonschema.validate({'lines': 'one2many'}, schema['nativeModifierFieldTypes'])
        for value in ['', ' ', False, None]:
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({'lines': value}, schema['nativeModifierFieldTypes'])
        snapshot_schema = schema['nativeModifierRelationSnapshots']
        for ids in ([], [7, 9]):
            jsonschema.validate({'lines': {'sourceValue': [], 'persistedIds': ids}}, snapshot_schema)
        for value in ({'persistedIds': []}, {'sourceValue': []}, {'sourceValue': [], 'persistedIds': [True]},
                      {'sourceValue': [], 'persistedIds': [0]}, {'sourceValue': [], 'persistedIds': [9007199254740992]}):
            with self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({'lines': value}, snapshot_schema)

    def test_modifier_declaration_token_must_have_a_backend_producer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'native_modifier.py'
            path.write_text('MODIFIER_KEYS = ("unrelated_key",)')
            with patch.object(guard, 'MODIFIER_DECLARATION_PRODUCERS', (path,)), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('is not declared by the backend modifier declaration producers', output)

    def test_backend_cannot_publish_web_refusal_marker(self):
        schema = json.loads(guard.BACKEND_SCHEMA.read_text())
        schema['$defs']['actionRule']['properties']['actionSemanticsInvalid'] = {'type': 'boolean'}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'schema.json'
            path.write_text(json.dumps(schema))
            with patch.object(guard, 'BACKEND_SCHEMA', path), patch.object(guard, '_relative', lambda p: str(p)):
                result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('must not publish actionSemanticsInvalid', output)

    def test_button_visibility_explanation_is_bound_to_schema_and_consumers(self):
        result, output = self.run_guard()
        self.assertEqual(result, 0, output)
        with patch.object(guard, 'BUTTON_VISIBILITY_EXPLANATION_VALUES', ('native_modifier',)):
            result, output = self.run_guard()
        self.assertNotEqual(result, 0)
        self.assertIn('buttonStatus.visibilityExplanation enum must be', output)




class RequiredObjectReadTests(unittest.TestCase):
    def wrap(self, body):
        return "export function decodeContractV2Snapshot(value: unknown): ContractV2Snapshot {\n" + body + "\n}"

    def test_current_source_matches_backend_required_set(self):
        expected = set(json.loads(guard.BACKEND_SCHEMA.read_text())["required"])
        self.assertEqual(expected, guard._strict_required_object_reads(guard.STRICT_SCHEMA.read_text()))

    def test_multiline_and_double_quote_calls_are_recognized(self):
        self.assertEqual({"meta"}, guard._strict_required_object_reads(self.wrap(
            'const meta = requiredRecord(\n root, "meta", "$", issues\n);')))

    def test_removed_required_read_is_detected_even_with_comment_decoy(self):
        source = guard.STRICT_SCHEMA.read_text()
        source = source.replace("requiredRecord(root, 'pageInfo', '$', issues)", "root.pageInfo")
        source = source.replace("const root = asRecord(value);", "const root = asRecord(value);\n// requiredRecord(root, 'pageInfo', '$', issues)")
        self.assertNotIn("pageInfo", guard._strict_required_object_reads(source))

    def test_literals_and_retired_alias_helpers_cannot_satisfy_reads(self):
        body = """
// requiredRecord(root, 'pageInfo', '$', issues)
/* requiredRecord(root, 'layoutContract', '$', issues) */
const prose = "requiredRecord(root, 'statusContract', '$', issues)";
const template = `requiredRecord(root, 'dataContract', '$', issues)`;
readAliasedObject(root, 'meta', [], '$', issues);
requiredRecord(other, 'runtimeContract', '$', issues);
"""
        self.assertEqual(set(), guard._strict_required_object_reads(self.wrap(body)))

    def test_unrelated_function_does_not_supply_missing_terminal_read(self):
        source = self.wrap("return snapshot;") + "\nfunction unrelated() { requiredRecord(root, 'meta', '$', issues); }"
        self.assertEqual(set(), guard._strict_required_object_reads(source))


if __name__ == '__main__':
    unittest.main()
