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


if __name__ == '__main__':
    unittest.main()
