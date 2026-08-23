#!/usr/bin/env python3

import ast
from contextlib import contextmanager
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "contract" / "snapshot_export.py"
TREE = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
BODY = [
    node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    and node.name == "snapshot_handler_principal"
]
NAMESPACE = {"contextmanager": contextmanager, "sys": sys}
exec(compile(ast.Module(body=BODY, type_ignores=[]), str(MODULE_PATH), "exec"), NAMESPACE)
snapshot_handler_principal = NAMESPACE["snapshot_handler_principal"]


class _Relation:
    def __init__(self, ids):
        self.ids = ids


class _Company:
    def __init__(self, company_id):
        self.id = company_id


class _User:
    company_id = _Company(7)
    company_ids = _Relation([7, 9])


class ContractSnapshotPrincipalTest(unittest.TestCase):
    def test_shell_principal_is_bound_and_resolver_is_restored(self):
        module_name = "snapshot_principal_fixture"
        original = lambda: {"principal_type": "machine"}
        fixture = types.SimpleNamespace(get_principal_from_token=original)
        sys.modules[module_name] = fixture
        handler_cls = type("FixtureHandler", (), {"__module__": module_name})
        try:
            with snapshot_handler_principal(handler_cls, _User()):
                principal = fixture.get_principal_from_token()
                self.assertEqual(principal["principal_type"], "human")
                self.assertEqual(principal["auth_method"], "password")
                self.assertEqual(principal["company_id"], 7)
                self.assertEqual(principal["allowed_company_ids"], (7, 9))
            self.assertIs(fixture.get_principal_from_token, original)
        finally:
            sys.modules.pop(module_name, None)

    def test_handler_without_token_resolver_is_unchanged(self):
        module_name = "snapshot_principal_noop_fixture"
        fixture = types.SimpleNamespace()
        sys.modules[module_name] = fixture
        handler_cls = type("FixtureHandler", (), {"__module__": module_name})
        try:
            with snapshot_handler_principal(handler_cls, _User()):
                self.assertFalse(hasattr(fixture, "get_principal_from_token"))
        finally:
            sys.modules.pop(module_name, None)


if __name__ == "__main__":
    unittest.main()
