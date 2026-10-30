import importlib.util
import json
import os
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

    def test_receipt_written_from_one_worktree_is_readable_from_another(self):
        head = "1" * 40
        main = WORKSPACE / "sce-backend-odoo"
        pc02 = WORKSPACE / "sce-backend-odoo-pc02"
        if not (main / ".git").exists() or not pc02.exists():
            self.skipTest("additional worktrees not present")
        path = self.module.evidence_path(main, head)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"suite": "quick", "head": head, "tree": "2" * 40, "coverage": {}}
        # atomic temp-then-replace, matching the real writer
        tmp = path.with_name(f".{head}.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        try:
            other = self.module.evidence_path(pc02, head)
            self.assertEqual(path, other)
            self.assertEqual(json.loads(other.read_text(encoding="utf-8"))["head"], head)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
