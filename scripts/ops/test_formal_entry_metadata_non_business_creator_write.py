#!/usr/bin/env python3
"""Lock the governed non-business-creator repair to behavior and declaration.

The repair rewrites user-visible formal-entry records whose creator metadata is
an operator login (``admin``/``系统``/...) into a real business name or the
sanctioned legacy label. These tests bind the repair registry to the declared
formal-entry contract and the audit's entry-pair fields, then exercise the real
``fix_records`` behavior against a fake model instead of asserting strings.
"""

import ast
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WRITE_TOOL = ROOT / "scripts" / "ops" / "formal_entry_metadata_non_business_creator_write.py"
AUDIT = ROOT / "scripts" / "verify" / "formal_entry_metadata_audit.py"
EXTENSIONS = (
    ROOT
    / "addons"
    / "smart_construction_core"
    / "models"
    / "support"
    / "formal_entry_metadata_extensions.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("nbc_write_tool", WRITE_TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == name:
                return ast.literal_eval(node.value)
    raise AssertionError("assignment %s not found in %s" % (name, path.name))


class FakeRecord:
    def __init__(self, values):
        self._values = dict(values)
        self.display_name = values.get("name") or ""

    def __getitem__(self, key):
        return self._values.get(key)

    def __getattr__(self, name):
        return self._values.get(name, "")

    def __setitem__(self, key, value):
        self._values[key] = value

    def write(self, values):
        self._values.update(values)

    @property
    def id(self):
        return self._values["id"]


class FakeModel:
    def __init__(self, fields, records):
        self._fields = {name: object() for name in fields}
        self._records = records

    def sudo(self):
        return self

    def with_context(self, **_kwargs):
        return self

    def search(self, domain):
        out = []
        for record in self._records:
            matched = True
            for key, op, value in domain:
                current = record[key]
                if op == "=" and current != value:
                    matched = False
                    break
                if op == "in" and current not in value:
                    matched = False
                    break
            if matched:
                out.append(record)
        return out


class FakeCursor:
    def __init__(self):
        self.committed = 0

    def commit(self):
        self.committed += 1


class FakeEnv:
    def __init__(self, models):
        self._models = models
        self.cr = FakeCursor()
        self.dbname = "sc_fake"

    def __getitem__(self, name):
        return self._models[name]


class NonBusinessCreatorWriteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tool = _load()

    def test_settlement_rule_targets_a_declared_contract_model(self) -> None:
        declared = set(_module_assignment(EXTENSIONS, "FORMAL_ENTRY_METADATA_MODELS"))
        self.assertIn("sc.settlement.order", declared)
        rules = dict((model, field) for model, field, _resolver in self.tool.CREATOR_RULES)
        self.assertEqual(rules.get("sc.settlement.order"), "source_created_by")

    def test_registry_fields_are_declared_entry_creator_fields(self) -> None:
        pairs = _module_assignment(AUDIT, "ENTRY_PAIRS")
        creator_fields = {creator for creator, _time in pairs}
        for model, field_name, _resolver in self.tool.CREATOR_RULES:
            self.assertIn(field_name, creator_fields, "%s uses %s" % (model, field_name))

    def test_fix_records_rewrites_non_business_creator(self) -> None:
        record = FakeRecord({"id": 7, "name": "FE", "creator": "admin", "active": True})
        env = FakeEnv({"sc.receipt.income": FakeModel({"creator": object(), "active": object()}, [record])})
        result = self.tool.fix_records(env, "sc.receipt.income", "creator", lambda _record: "")
        self.assertEqual(result["updated"], 1)
        self.assertEqual(record["creator"], self.tool.LEGACY_SYSTEM_ADMIN_LABEL)
        self.assertEqual(result["field"], "creator")

    def test_fix_records_keeps_business_creator(self) -> None:
        record = FakeRecord({"id": 8, "name": "FE", "creator": "张三", "active": True})
        env = FakeEnv({"sc.receipt.income": FakeModel({"creator": object(), "active": object()}, [record])})
        result = self.tool.fix_records(env, "sc.receipt.income", "creator", lambda _record: "")
        self.assertEqual(result["updated"], 0)
        self.assertEqual(record["creator"], "张三")

    def test_fix_records_uses_resolver_business_name(self) -> None:
        record = FakeRecord({"id": 9, "name": "FE", "creator": "admin", "applicant_name": "李四", "active": True})
        env = FakeEnv({"sc.expense.claim": FakeModel({"creator": object(), "applicant_name": object(), "active": object()}, [record])})
        result = self.tool.fix_records(env, "sc.expense.claim", "creator", self.tool.expense_claim_creator)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(record["creator"], "李四")

    def test_fix_records_skips_model_without_field(self) -> None:
        env = FakeEnv({"x": FakeModel({"other": object()}, [])})
        result = self.tool.fix_records(env, "x", "creator", lambda _record: "")
        self.assertEqual(result, {"model": "x", "field": "creator", "updated": 0, "rows": []})


if __name__ == "__main__":
    unittest.main()
