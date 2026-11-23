from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.dev.local_test_inputs import fingerprint


class LocalTestInputFingerprintTest(unittest.TestCase):
    def test_only_test_runtime_inputs_invalidate_the_fingerprint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            addon = root / "addons/example/__manifest__.py"
            addon.parent.mkdir(parents=True)
            addon.write_text("{'depends': ['dependency']}")
            dependency = root / "addons/dependency/__manifest__.py"
            dependency.parent.mkdir(parents=True, exist_ok=True)
            dependency.write_text("{}")
            dependency_test = root / "addons/dependency/tests/test_example.py"
            dependency_test.parent.mkdir(parents=True)
            dependency_test.write_text("class TestExample: pass")
            tool = root / "scripts/test/odoo_ordered_tests.py"
            tool.parent.mkdir(parents=True)
            tool.write_text("print('test')")
            docs = root / "docs/iteration.md"
            docs.parent.mkdir(parents=True)
            docs.write_text("documentation")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            before = fingerprint(root, "example")
            docs.write_text("changed documentation")
            self.assertEqual(before, fingerprint(root, "example"))
            dependency_test.write_text("class TestExample: changed = True")
            self.assertEqual(before, fingerprint(root, "example"))
            addon.write_text("{'name': 'changed'}")
            self.assertNotEqual(before, fingerprint(root, "example"))


if __name__ == "__main__":
    unittest.main()
