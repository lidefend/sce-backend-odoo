# -*- coding: utf-8 -*-
"""BOQ 导入批次只读预检快照 handler 单测（G3.1）。

桩加载模式：不依赖 Odoo 数据库，验证
- 参数缺失/非法 → 结构化 MISSING_PARAMS（不抛异常）
- 批次不存在（含无权限同语义）→ 结构化 BATCH_NOT_FOUND
- 正常路径 → 批次投影 + preview_payload 快照透传
- preview_payload 非对象 → 空快照安全降级
- project_id 路径按 id desc 取最新批次
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path


class _BaseIntentHandler:
    def __init__(self, env=None, params=None, payload=None, context=None):
        self.env = env or {}
        self.params = params or {}
        self.payload = payload or {}
        self.context = context or {}


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


def _load_handler_module():
    root = Path(__file__).resolve().parents[1]
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(root.parent / "smart_core")]
    core_mod.__path__ = [str(root.parent / "smart_core" / "core")]
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)

    module_name = "odoo.addons.smart_construction_core.handlers.boq_import_preview_fetch"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        root / "handlers" / "boq_import_preview_fetch.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeImportedAt:
    def isoformat(self):
        return "2026-09-03T12:00:00"


class _FakeRef:
    def __init__(self, ref_id):
        self.id = ref_id


class _FakeBatch:
    def __init__(self, **vals):
        self.id = vals.get("id", 11)
        self.name = vals.get("name", "清单导入")
        self.project_id = vals.get("project_id", _FakeRef(3))
        self.version_id = vals.get("version_id", _FakeRef(5))
        self.state = vals.get("state", "imported")
        self.filename = vals.get("filename", "boq.xlsx")
        self.file_digest = vals.get("file_digest", "0" * 64)
        self.parser_schema = vals.get("parser_schema", "sc.boq.import.v1")
        self.row_count = vals.get("row_count", 120)
        self.item_count = vals.get("item_count", 100)
        self.skipped_count = vals.get("skipped_count", 4)
        self.warning_count = vals.get("warning_count", 2)
        self.preview_payload = vals.get("preview_payload", {"schema": "sc.boq.import.preview.v1"})
        self.imported_at = vals.get("imported_at", _FakeImportedAt())
        self.imported_by = vals.get("imported_by", _FakeRef(7))


class _FakeRecordset:
    """模拟 Odoo recordset：单记录属性代理 + 空判定。"""

    def __init__(self, rows):
        self._rows = list(rows)

    def __bool__(self):
        return bool(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def __getattr__(self, name):
        if len(self._rows) == 1:
            return getattr(self._rows[0], name)
        raise AttributeError(name)


class _FakeBatchModel:
    def __init__(self, batches):
        self._batches = list(batches)
        self.calls = []

    def search(self, domain, limit=None, order=None):
        self.calls.append({"domain": domain, "limit": limit, "order": order})
        rows = list(self._batches)
        for clause in domain or []:
            if len(clause) == 3 and clause[0] == "id":
                rows = [row for row in rows if row.id == clause[2]]
            elif len(clause) == 3 and clause[0] == "project_id":
                rows = [row for row in rows if row.project_id.id == clause[2]]
        if order == "id desc":
            rows.sort(key=lambda row: row.id, reverse=True)
        if limit:
            rows = rows[:limit]
        return _FakeRecordset(rows)


class _FakeEnv(dict):
    def __init__(self, batch_model):
        super().__init__({"project.boq.import.batch": batch_model})
        self.context = {}


def _make_handler(module, env, params=None):
    return module.BoqImportPreviewFetchHandler(env=env, params=params or {}, payload={})


class BoqImportPreviewFetchHandlerTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_handler_module()

    def test_missing_params_returns_structured_error(self):
        handler = _make_handler(self.module, _FakeEnv(_FakeBatchModel([])))
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "MISSING_PARAMS")
        self.assertEqual(result["error"]["suggested_action"], "fix_input")
        self.assertIn("source_authority", result["meta"])

    def test_invalid_batch_id_degrades_to_missing_params(self):
        handler = _make_handler(
            self.module, _FakeEnv(_FakeBatchModel([])), {"batch_id": "not-a-number"}
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "MISSING_PARAMS")

    def test_batch_not_found_is_structured_not_exception(self):
        handler = _make_handler(self.module, _FakeEnv(_FakeBatchModel([])), {"batch_id": 404})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "BATCH_NOT_FOUND")
        self.assertEqual(result["error"]["suggested_action"], "check_params")

    def test_batch_id_path_serializes_readonly_projection(self):
        batch = _FakeBatch(
            id=11,
            preview_payload={
                "schema": "sc.boq.import.preview.v1",
                "row_count": 120,
                "source_diagnostics": ["legacy xls hint"],
            },
        )
        handler = _make_handler(self.module, _FakeEnv(_FakeBatchModel([batch])), {"batch_id": 11})
        result = handler.handle()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["preview_schema"], "sc.boq.import.preview.v1")
        self.assertEqual(data["batch"]["id"], 11)
        self.assertEqual(data["batch"]["project_id"], 3)
        self.assertEqual(data["batch"]["state"], "imported")
        self.assertEqual(data["batch"]["imported_at"], "2026-09-03T12:00:00")
        self.assertEqual(data["batch"]["preview_payload"]["row_count"], 120)
        self.assertEqual(
            data["safe_degradation"]["missing_payload_policy"],
            "preview_payload 非对象时以空快照降级，前端须可渲染空态",
        )

    def test_non_dict_preview_payload_degrades_to_empty_snapshot(self):
        batch = _FakeBatch(preview_payload=None)
        handler = _make_handler(self.module, _FakeEnv(_FakeBatchModel([batch])), {"batch_id": 11})
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["batch"]["preview_payload"], {})

    def test_project_id_path_searches_latest_batch_desc(self):
        older = _FakeBatch(id=10, project_id=_FakeRef(3))
        newer = _FakeBatch(id=12, project_id=_FakeRef(3))
        other_project = _FakeBatch(id=13, project_id=_FakeRef(9))
        model = _FakeBatchModel([older, newer, other_project])
        handler = _make_handler(self.module, _FakeEnv(model), {"project_id": 3})
        result = handler.handle()
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["batch"]["id"], 12)
        self.assertEqual(model.calls[-1]["order"], "id desc")

    def test_nested_params_envelope_is_unwrapped(self):
        batch = _FakeBatch(id=11)
        handler = _make_handler(self.module, _FakeEnv(_FakeBatchModel([batch])))
        result = handler.handle(payload={"params": {"batch_id": 11}})
        self.assertTrue(result["ok"])


if __name__ == "__main__":
    unittest.main()
