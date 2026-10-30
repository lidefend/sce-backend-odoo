import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent


def _load_local_quick_evidence():
    spec = importlib.util.spec_from_file_location(
        "local_quick_evidence", ROOT / "scripts" / "ops" / "local_quick_evidence.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidencePathTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_local_quick_evidence()

    def test_evidence_path_is_shared_across_worktrees(self):
        head = "0" * 40
        main = WORKSPACE / "sce-backend-odoo"
        pc02 = WORKSPACE / "sce-backend-odoo-pc02"
        if not (main / ".git").exists() or not pc02.exists():
            self.skipTest("additional worktrees not present")
        main_path = self.module.evidence_path(main, head)
        pc02_path = self.module.evidence_path(pc02, head)
        self.assertEqual(main_path, pc02_path)
        self.assertNotIn(".git/worktrees", str(main_path))
        self.assertIn("codex/evidence", str(main_path))


if __name__ == "__main__":
    unittest.main()
