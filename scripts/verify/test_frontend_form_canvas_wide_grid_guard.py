import contextlib
import io
from pathlib import Path
import re
import runpy
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / 'scripts/verify/frontend_form_canvas_wide_grid_guard.py'


class ReadonlyGridGuardTests(unittest.TestCase):
    def run_guard(self, mutate=lambda value: value):
        original = Path.read_text
        def read(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if str(path).endswith('/components/template/FormSection.vue'):
                return re.sub(r'(?m)^\.readonly-value\s*\{([^{}]*)\}', lambda match: '.readonly-value {' + mutate(match.group(1)) + '}', value, count=1)
            return value
        with patch.object(Path, 'read_text', read), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(GUARD))

    def test_current(self):
        self.run_guard()

    def test_order_and_font_are_not_layout_authority(self):
        self.run_guard(lambda body: '\n  width: 100%;' + body.replace('\n  width: 100%;', ''))

    def test_missing_width_fails(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', ''))

    def test_wrong_width_fails(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', '\n  width: 50%;'))

    def test_neighbor_declaration_cannot_supply_width(self):
        with self.assertRaisesRegex(SystemExit, 'readonly value declaration.*width'):
            self.run_guard(lambda body: body.replace('\n  width: 100%;', '') + '}\n.neighbor { width: 100%;')
