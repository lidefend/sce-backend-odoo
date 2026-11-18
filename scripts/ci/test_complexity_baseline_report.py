"""Line budgets report debt without hiding broken inventory configuration."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'complexity_report', Path(__file__).with_name('enforce_complexity_baseline_lock.py'))
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)


class ComplexityReportTest(unittest.TestCase):
    def run_report(self, files, text='first\nsecond\n'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'Makefile').write_text(text)
            baseline = root / 'baseline.json'
            baseline.write_text(json.dumps({'files': files}))
            output = io.StringIO()
            with patch.object(REPORT, 'ROOT', root), patch.object(REPORT, 'BASELINE', baseline), \
                    contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                status = REPORT.main()
            return status, output.getvalue()

    def test_growth_warns_without_blocking_or_changing_reference(self):
        status, output = self.run_report({'Makefile': {'max_lines': 1}})
        self.assertEqual(status, 0)
        self.assertIn('WARNING Makefile: line count increased to 2, reference 1', output)
        self.assertIn('checked=1 warnings=1', output)

    def test_within_budget_has_no_warning(self):
        status, output = self.run_report({'Makefile': {'max_lines': 2}})
        self.assertEqual(status, 0)
        self.assertNotIn('WARNING', output)

    def test_missing_file_still_blocks(self):
        status, output = self.run_report({'missing.mk': {'max_lines': 10}})
        self.assertEqual(status, 1)
        self.assertIn('missing.mk: file missing', output)

    def test_invalid_inventory_still_blocks(self):
        for files in ({}, {'Makefile': None}, {'Makefile': {'max_lines': 0}}):
            with self.subTest(files=files):
                status, output = self.run_report(files)
                self.assertNotEqual(status, 0)
                self.assertTrue('ERROR' in output or 'FAIL' in output)


if __name__ == '__main__':
    unittest.main()
