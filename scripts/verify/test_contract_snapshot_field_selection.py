#!/usr/bin/env python3

import ast
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "contract" / "snapshot_export.py"
SOURCE = MODULE_PATH.read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)
FUNCTION_NAMES = {"_layout_field_names", "select_form_record_fields"}
BODY = [
    node
    for node in TREE.body
    if isinstance(node, (ast.FunctionDef, ast.Assign))
    and (
        getattr(node, "name", "") in FUNCTION_NAMES
        or any(
            isinstance(target, ast.Name) and target.id == "_SNAPSHOT_LAYOUT_CHILD_KEYS"
            for target in getattr(node, "targets", [])
        )
    )
]
NAMESPACE = {
    "Iterable": __import__("collections.abc").abc.Iterable,
    "Mapping": __import__("collections.abc").abc.Mapping,
}
exec(compile(ast.Module(body=BODY, type_ignores=[]), str(MODULE_PATH), "exec"), NAMESPACE)
TEST_MODULE = types.SimpleNamespace(**NAMESPACE)


class SnapshotFieldSelectionTest(unittest.TestCase):
    def test_contract_layout_is_authoritative(self):
        data = {
            "fields": {"name": {}, "manager_id": {}, "contract_ids": {}},
            "views": {
                "form": {
                    "layout": [
                        {"type": "group", "children": [{"type": "field", "name": "name"}]},
                        {"widgetList": [{"widgetType": "field", "field": "manager_id"}]},
                    ]
                }
            },
        }
        self.assertEqual(
            TEST_MODULE.select_form_record_fields(data, ["contract_ids"]),
            ["id", "name", "manager_id"],
        )

    def test_native_view_is_used_when_contract_layout_is_empty(self):
        data = {
            "fields": {"name": {}, "manager_id": {}, "contract_ids": {}},
            "views": {"form": {"layout": []}},
        }
        self.assertEqual(
            TEST_MODULE.select_form_record_fields(data, ["name", "manager_id", "unknown"]),
            ["id", "name", "manager_id"],
        )

    def test_empty_sources_never_mean_read_all_fields(self):
        data = {"fields": {"contract_ids": {}}, "views": {"form": {"layout": []}}}
        self.assertEqual(TEST_MODULE.select_form_record_fields(data), ["id"])


if __name__ == "__main__":
    unittest.main()
