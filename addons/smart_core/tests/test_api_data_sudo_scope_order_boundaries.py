# -*- coding: utf-8 -*-
import ast
import unittest
from pathlib import Path


API_DATA_SOURCE = Path(__file__).resolve().parents[1] / "handlers" / "api_data.py"


def _function(tree, name):
    return next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _calls(function, name):
    return [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and (
            isinstance(node.func, ast.Name)
            and node.func.id == name
            or isinstance(node.func, ast.Attribute)
            and node.func.attr == name
        )
    ]


class TestApiDataSudoScopeOrderBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(API_DATA_SOURCE.read_text(encoding="utf-8"))
        cls.create = _function(cls.tree, "_op_create")
        cls.authorize = _function(cls.tree, "_authorize_account_tax_create_scope")

    def test_account_tax_scope_authorization_precedes_policy_and_sudo(self):
        authorize_calls = _calls(self.create, "_authorize_account_tax_create_scope")
        policy_calls = _calls(self.create, "_create_execution_policy")
        sudo_calls = _calls(self.create, "sudo")

        self.assertEqual(len(authorize_calls), 1)
        self.assertEqual(len(policy_calls), 2)
        self.assertEqual(len(sudo_calls), 2)
        self.assertLess(authorize_calls[0].lineno, policy_calls[0].lineno)
        self.assertLess(authorize_calls[0].lineno, sudo_calls[0].lineno)

    def test_caller_model_is_captured_before_account_tax_policy(self):
        account_tax_guard = next(
            node
            for node in self.create.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and ast.unparse(node.test) == "model == 'account.tax'"
        )
        guard_source = ast.unparse(account_tax_guard)
        authorize_source = ast.unparse(self.authorize)

        self.assertIn(
            "self._authorize_account_tax_create_scope(p, ctx)",
            guard_source,
        )
        self.assertIn(
            "caller_env_model = self.env['account.tax'].with_context(ctx)",
            authorize_source,
        )
        self.assertIn(
            "self._apply_record_scope(caller_env_model, [], p, ctx)",
            authorize_source,
        )
        self.assertNotIn(".sudo(", authorize_source)
        self.assertNotIn(".browse(", authorize_source)
        self.assertNotIn(".exists(", authorize_source)

    def test_operation_model_uses_preauthorized_metadata_after_sudo(self):
        source = ast.unparse(self.create)

        self.assertIn(
            "env_model = caller_env_model if caller_env_model is not None else self.env[model].with_context(ctx)",
            source,
        )
        self.assertIn("env_model = env_model.sudo()", source)
        self.assertIn("if preauthorized_scope_meta is None:", source)
        self.assertIn("project_scope_meta = preauthorized_scope_meta", source)
        self.assertNotIn(
            "self._apply_record_scope(env_model.sudo()",
            source,
        )

    def test_legitimate_create_policy_and_operation_remain_present(self):
        policy_calls = _calls(self.create, "_create_execution_policy")
        create_calls = _calls(self.create, "create")

        self.assertEqual(len(policy_calls), 2)
        self.assertTrue(create_calls)
        self.assertLess(policy_calls[-1].lineno, create_calls[-1].lineno)


if __name__ == "__main__":
    unittest.main()
