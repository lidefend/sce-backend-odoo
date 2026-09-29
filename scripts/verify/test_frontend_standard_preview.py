import importlib.util
import os
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('preview', Path(__file__).resolve().parents[1] / 'dev/frontend_standard_preview.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


class PreviewIdentityTest(unittest.TestCase):
    def setUp(self):
        self.env = {'STATIC_ROOT': str(preview.PREVIOUS), 'STATIC_PORT': '5180', 'API_PROXY_TARGET': 'http://127.0.0.1:18082'}

    def test_registered_previous_can_be_replaced(self):
        self.assertEqual(preview.validate_listener(self.env, 'node scripts/release/release_static_server.mjs', os.getuid()), str(preview.PREVIOUS))

    def test_unrelated_candidate_is_never_stopped(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener({**self.env, 'STATIC_ROOT': '/other'}, 'node scripts/release/release_static_server.mjs', os.getuid())

    def test_browser_rejects_the_previous_candidate(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener(self.env, 'node scripts/release/release_static_server.mjs', os.getuid(), current_only=True)

    def test_wrong_proxy_is_never_reused(self):
        with self.assertRaises(RuntimeError):
            preview.validate_listener({**self.env, 'API_PROXY_TARGET': 'http://127.0.0.1:18081'}, 'node scripts/release/release_static_server.mjs', os.getuid())

    def test_other_owner_and_command_rejected(self):
        for command, owner in [('other', os.getuid()), ('node scripts/release/release_static_server.mjs', os.getuid() + 1)]:
            with self.assertRaises(RuntimeError):
                preview.validate_listener(self.env, command, owner)
