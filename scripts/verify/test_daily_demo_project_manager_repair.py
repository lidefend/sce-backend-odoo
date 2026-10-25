import unittest
import ast
from pathlib import Path
from types import SimpleNamespace
from scripts.verify.daily_demo_project_manager_repair import validate_checkpoint


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.facts = {"database": "sc_demo", "uuid": "c7ffe700-ce02-11f1-9a86-a213133df790",
                      "project_id": 2, "project_code": "DEMO-PJ-001", "company_id": 1,
                      "old_manager_id": 1, "root_id": 1, "actor_id": 40,
                      "target_id": 8, "target_login": "pm1", "target_active": True,
                      "target_company_id": 1, "project_user_id": 8}

    def test_observed_checkpoint(self):
        validate_checkpoint(self.facts)

    def test_replay_refused(self):
        self.facts["old_manager_id"] = 8
        with self.assertRaises(RuntimeError):
            validate_checkpoint(self.facts)

    def test_each_identity_drift_refused(self):
        for key in self.facts:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                validate_checkpoint({**self.facts, key: None})

    def test_extra_scope_refused(self):
        with self.assertRaises(RuntimeError):
            validate_checkpoint({**self.facts, "another_project": 3})

    def test_boolean_identity_refused(self):
        with self.assertRaises(RuntimeError):
            validate_checkpoint({**self.facts, "root_id": True})

    def test_seed_replaces_only_empty_or_system_manager(self):
        root = object()
        person = SimpleNamespace(id=8)
        env = SimpleNamespace(ref=lambda key: root if key == "base.user_root" else None)
        for name in ("step_demo_showroom.py", "step_20_projects_demo.py"):
            path = Path(__file__).resolve().parents[2] / "demo_addons/smart_construction_demo/seed/steps" / name
            tree = ast.parse(path.read_text())
            conditions = [node.test for node in ast.walk(tree) if isinstance(node, ast.If)
                          and 'base.user_root' in ast.unparse(node.test)
                          and 'manager_id' in ast.unparse(node.test)]
            self.assertEqual(len(conditions), 1)
            expression = compile(ast.Expression(conditions[0]), str(path), "eval")
            for old, expected in ((None, True), (root, True), (person, False), (object(), False)):
                with self.subTest(seed=name, old=old):
                    self.assertEqual(bool(eval(expression, {"pm_person": person, "env": env,
                                                           "project": SimpleNamespace(manager_id=old)})), expected)
