#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SOURCE = Path(__file__).with_name("production_attachment_preview_csp.py")
SPEC = importlib.util.spec_from_file_location("production_attachment_preview_csp", SOURCE)
target = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(target)


class ProductionAttachmentPreviewCspTest(unittest.TestCase):
    def test_exact_frozen_policy_adds_only_frame_src(self):
        original = f'add_header Content-Security-Policy "{target.CURRENT}" always;\n'
        updated = target.desired_content(original)
        self.assertIn("frame-src 'self' blob:;", updated)
        self.assertEqual(updated.replace(" frame-src 'self' blob:;", ""), original)

    def test_idempotent_policy_is_unchanged(self):
        original = f'add_header Content-Security-Policy "{target.DESIRED}" always;\n'
        self.assertEqual(target.desired_content(original), original)

    def test_unknown_or_competing_policy_fails_closed(self):
        with self.assertRaises(target.CspError):
            target.desired_content("default-src *")
        with self.assertRaises(target.CspError):
            target.desired_content(target.CURRENT + "\n" + target.DESIRED)


if __name__ == "__main__":
    unittest.main()
