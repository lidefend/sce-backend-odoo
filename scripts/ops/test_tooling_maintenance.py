from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ops import tooling_maintenance as lane


class ClassificationTests(unittest.TestCase):
    def test_tooling_paths_are_allowed(self):
        result = lane.classify(
            [
                "docs/ops/example.md",
                "scripts/verify/guard.py",
                "scripts/verify/test_guard.py",
                "scripts/ops/tool.py",
            ]
        )
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["allowed"]), 4)

    def test_product_runtime_paths_are_blocked(self):
        result = lane.classify(
            [
                "addons/smart_core/models/x.py",
                "frontend/apps/web/src/App.vue",
                "config/ops/runtime.json",
                ".agent/runs/x.json",
            ]
        )
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["blocked"]), 4)

    def test_make_guards_requires_explicit_flag(self):
        without_flag = lane.classify(["make/guards.mk"])
        with_flag = lane.classify(["make/guards.mk"], allow_make_guards=True)
        self.assertFalse(without_flag["ok"])
        self.assertTrue(with_flag["ok"])

    def test_changed_paths_include_untracked_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "base.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
            subprocess.run(["git", "branch", "origin/main"], cwd=root, check=True)
            (root / "scripts").mkdir()
            (root / "scripts/ops").mkdir()
            (root / "scripts/ops/new.py").write_text("print('x')\n", encoding="utf-8")
            paths = lane.changed_paths(root, base="origin/main")
            self.assertIn("scripts/ops/new.py", paths)

    def test_temporary_bypass_payload_preserves_rules_and_removes_actor(self):
        ruleset = {
            "name": "main-github-authoritative-pr",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
            "rules": [{"type": "non_fast_forward"}],
        }
        enabled = lane.ruleset_payload_with_bypass(ruleset, 307461631)
        disabled = lane.ruleset_payload_with_bypass(ruleset, 0)
        self.assertEqual(enabled["rules"], ruleset["rules"])
        self.assertEqual(
            enabled["bypass_actors"],
            [{"actor_id": 307461631, "actor_type": "User", "bypass_mode": "always"}],
        )
        self.assertEqual(disabled["bypass_actors"], [])


if __name__ == "__main__":
    unittest.main()
