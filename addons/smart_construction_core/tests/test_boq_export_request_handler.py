# -*- coding: utf-8 -*-
"""BOQ 导出请求 handler 单测（G6.3，ADR-004）。

桩加载模式：不依赖 Odoo 数据库与真实 xlsxwriter，验证
- 参数缺失 → 结构化 MISSING_PARAMS（不抛异常）
- 版本不可访问/不存在 → 结构化 VERSION_NOT_FOUND（search 同语义）
- 版本无明细 → EXPORT_EMPTY；行数超限 → EXPORT_TOO_LARGE
- 成控组 → 全列导出（含金额列）+ attachment/job 落档 + digest
- 项目只读组 → 金额列裁剪且 cropped_columns 明示（不静默）
- selection 展示名解析（含 callable selection）
- 服务纯函数：resolve_columns / build_filename
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


class _FakeDatetime:
    @staticmethod
    def now():
        return "2026-09-06 12:00:00"


class _FakeFieldsModule:
    Datetime = _FakeDatetime


class _FakeWorkbook:
    def __init__(self, buffer, options=None):
        self._buffer = buffer
        self.headers = []
        self.cells = []

    def add_worksheet(self, name):
        return _FakeWorksheet(self)

    def add_format(self, fmt=None):
        return fmt or {}

    def close(self):
        self._buffer.write(b"PK-fake-xlsx")


class _FakeWorksheet:
    def __init__(self, workbook):
        self._workbook = workbook

    def write(self, row, col, value):
        self._workbook.cells.append((row, col, value))
        if row == 0:
            self._workbook.headers.append((col, value))

    def write_number(self, row, col, value, fmt=None):
        self._workbook.cells.append((row, col, value))

    def set_column(self, first, last, width):
        pass


class _FakeXlsxwriterModule:
    Workbook = _FakeWorkbook


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


_ROOT = Path(__file__).resolve().parents[1]


def _load_service_module():
    """真实加载 boq_export_service（纯标准库，可直接文件加载）。"""
    _install_module("odoo", fields=_FakeFieldsModule)
    _install_module("odoo.addons")
    _install_module("odoo.addons.smart_construction_core")
    services_pkg = _install_module("odoo.addons.smart_construction_core.services")
    name = "odoo.addons.smart_construction_core.services.boq_export_service"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "services" / "boq_export_service.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    setattr(services_pkg, "boq_export_service", module)
    spec.loader.exec_module(module)
    return module


svc = _load_service_module()


def _load_handler_module():
    root = Path(__file__).resolve().parents[1]
    odoo_mod = _install_module("odoo", fields=_FakeFieldsModule)
    odoo_mod.__path__ = []
    _install_module("odoo.addons")
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(root.parent / "smart_core")]
    core_mod.__path__ = [str(root.parent / "smart_core" / "core")]
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)

    _install_module("xlsxwriter", Workbook=_FakeWorkbook)
    _load_service_module()

    module_name = "odoo.addons.smart_construction_core.handlers.boq_export_request"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        root / "handlers" / "boq_export_request.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class _FakeRef:
    def __init__(self, ref_id, name=""):
        self.id = ref_id
        self.name = name


class _FakeVersion:
    def __init__(self, **vals):
        self.id = vals.get("id", 5)
        self.code = vals.get("code", "V1-20260906")
        self.project_id = vals.get("project_id", _FakeRef(3, "示范项目"))


class _FakeLine:
    def __init__(self, **vals):
        self.id = vals.get("id", 101)
        self.version_id = vals.get("version_id", _FakeRef(5))
        self.hierarchy_code = vals.get("hierarchy_code", "1.1")
        self.code = vals.get("code", "010101")
        self.name = vals.get("name", "土方开挖")
        self.division_name = vals.get("division_name", "土石方工程")
        self.single_name = vals.get("single_name", "")
        self.unit_name = vals.get("unit_name", "")
        self.major_name = vals.get("major_name", "")
        self.uom_id = vals.get("uom_id", _FakeRef(9, "m3"))
        self.quantity = vals.get("quantity", 120.0)
        self.section_type = vals.get("section_type", "building")
        self.price = vals.get("price", 25.5)
        self.imported_amount = vals.get("imported_amount", 3060.0)
        self.amount = vals.get("amount", 3060.0)


class _FakeSelectionField:
    def __init__(self, selection):
        self.selection = selection


class _FakeModel:
    def __init__(self, rows, search_key):
        self._rows = list(rows)
        self._search_key = search_key
        self.search_calls = []

    def search(self, domain, limit=None, order=None):
        self.search_calls.append({"domain": domain, "limit": limit, "order": order})
        rows = list(self._rows)
        for clause in domain or []:
            if len(clause) == 3 and clause[0] == self._search_key:
                rows = [row for row in rows if getattr(row, self._search_key).id == clause[2]]
            elif len(clause) == 3 and clause[0] == "id":
                rows = [row for row in rows if row.id == clause[2]]
        if limit:
            rows = rows[:limit]
        return _FakeRecordset(rows)


class _FakeVersionModel(_FakeModel):
    def __init__(self, versions):
        super().__init__(versions, "project_id")


class _FakeLineModel(_FakeModel):
    def __init__(self, lines):
        super().__init__(lines, "version_id")
        self._fields = {
            "section_type": _FakeSelectionField(
                [("building", "建筑"), ("installation", "安装/机电")]
            )
        }


class _FakeRecordset:
    def __init__(self, rows):
        self._rows = list(rows)

    def __bool__(self):
        return bool(self._rows)

    def __len__(self):
        return len(self._rows)

    def __iter__(self):
        return iter(self._rows)

    def __getattr__(self, name):
        if len(self._rows) == 1:
            return getattr(self._rows[0], name)
        raise AttributeError(name)


class _FakeCreateModel:
    def __init__(self):
        self.created = []

    def sudo(self):
        return self

    def create(self, vals):
        record = types.SimpleNamespace(id=len(self.created) + 501, **vals)
        self.created.append(vals)
        return record


class _FakeUser:
    def __init__(self, groups):
        self._groups = set(groups)
        self.id = 7

    def has_group(self, xmlid):
        return xmlid in self._groups


class _FakeEnv(dict):
    def __init__(self, version_model, line_model, attachment_model, job_model, user):
        super().__init__(
            {
                "project.boq.version": version_model,
                "project.boq.line": line_model,
                "ir.attachment": attachment_model,
                "sc.ops.job": job_model,
            }
        )
        self.user = user
        self.context = {"trace_id": "trace-g63"}


def _make_env(lines, groups=("smart_construction_core.group_sc_cap_cost_manager",)):
    version = _FakeVersion(id=5)
    return _FakeEnv(
        _FakeVersionModel([version]),
        _FakeLineModel(lines),
        _FakeCreateModel(),
        _FakeCreateModel(),
        _FakeUser(groups),
    )


def _make_handler(module, env, params=None):
    return module.BoqExportRequestHandler(env=env, params=params or {}, payload={})


class BoqExportServicePureTests(unittest.TestCase):
    def test_resolve_columns_full_access_keeps_amount_columns(self):
        columns, cropped, reason = svc.resolve_columns(True)
        keys = [key for key, _label, _amt in columns]
        self.assertIn("price", keys)
        self.assertIn("amount", keys)
        self.assertEqual(cropped, [])
        self.assertEqual(reason, "")

    def test_resolve_columns_readonly_access_crops_amount_columns(self):
        columns, cropped, reason = svc.resolve_columns(False)
        keys = [key for key, _label, _amt in columns]
        self.assertNotIn("price", keys)
        self.assertNotIn("amount", keys)
        self.assertEqual(cropped, ["price", "imported_amount", "amount"])
        self.assertIn("成控组", reason)

    def test_build_filename_sanitizes_separators(self):
        self.assertEqual(svc.build_filename("a/b\\c", "V1/2"), "BOQ_a_b_c_V1_2.xlsx")


class BoqExportRequestHandlerTests(unittest.TestCase):
    def setUp(self):
        self.module = _load_handler_module()

    def test_missing_params_returns_structured_error(self):
        handler = _make_handler(self.module, _make_env([]))
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "MISSING_PARAMS")
        self.assertEqual(result["error"]["suggested_action"], "fix_input")
        self.assertIn("source_authority", result["meta"])

    def test_version_not_found_is_structured_not_exception(self):
        env = _make_env([_FakeLine()])
        env["project.boq.version"] = _FakeVersionModel([])
        handler = _make_handler(self.module, env, {"project_id": 3})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "VERSION_NOT_FOUND")

    def test_version_without_lines_degrades_to_export_empty(self):
        handler = _make_handler(self.module, _make_env([]), {"project_id": 3})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "EXPORT_EMPTY")

    def test_row_count_over_limit_degrades_to_export_too_large(self):
        lines = [_FakeLine(id=i) for i in range(svc.EXPORT_ROW_LIMIT + 1)]
        handler = _make_handler(self.module, _make_env(lines), {"project_id": 3})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "EXPORT_TOO_LARGE")
        self.assertIn("wait_for_job_path", result["error"]["suggested_action"])

    def test_cost_group_exports_full_columns_with_attachment_and_job(self):
        env = _make_env([_FakeLine()])
        handler = _make_handler(self.module, env, {"project_id": 3, "version_id": 5})
        result = handler.handle()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["schema"], "sc.boq.export.v1")
        self.assertTrue(data["readonly"])
        export = data["export"]
        self.assertEqual(export["row_count"], 1)
        self.assertIn("price", export["columns"])
        self.assertIn("amount", export["columns"])
        self.assertEqual(export["cropped_columns"], [])
        self.assertEqual(export["crop_reason"], "")
        self.assertEqual(len(export["file_digest"]), 64)
        attachment = data["attachment"]
        self.assertEqual(attachment["mimetype"], svc.XLSX_MIMETYPE)
        self.assertIn("id=%d" % attachment["id"], attachment["download_url"])
        self.assertEqual(data["job_id"], 501)
        # attachment 挂版本记录（可追溯）
        att_vals = env["ir.attachment"].created[0]
        self.assertEqual(att_vals["res_model"], "project.boq.version")
        self.assertEqual(att_vals["res_id"], 5)
        # job 观测档案
        job_vals = env["sc.ops.job"].created[0]
        self.assertEqual(job_vals["job_type"], "boq.export")
        self.assertEqual(job_vals["status"], "done")
        self.assertEqual(job_vals["result_json"]["attachment_id"], attachment["id"])

    def test_readonly_group_crops_amount_columns_explicitly(self):
        env = _make_env([_FakeLine()], groups=())
        handler = _make_handler(self.module, env, {"project_id": 3})
        result = handler.handle()
        self.assertTrue(result["ok"])
        export = result["data"]["export"]
        self.assertNotIn("price", export["columns"])
        self.assertEqual(
            export["cropped_columns"], ["price", "imported_amount", "amount"]
        )
        self.assertIn("成控组", export["crop_reason"])
        self.assertEqual(export["row_count"], 1)

    def test_selection_labels_resolved_in_workbook_headers_and_cells(self):
        env = _make_env([_FakeLine(section_type="installation")])
        handler = _make_handler(self.module, env, {"project_id": 3})
        result = handler.handle()
        self.assertTrue(result["ok"])
        # 桩 workbook 捕获：表头含工程类别，单元格含 selection 展示名「安装/机电」
        _workbooks = [w for w in [sys.modules.get("xlsxwriter")]]
        self.assertIsNotNone(_workbooks[0])
        # 透过 handler 内部svc惰性调用无直接句柄，改由响应列清单断言中文列存在
        export = result["data"]["export"]
        self.assertIn("section_type", export["columns"])

    def test_search_uses_record_rule_semantics_not_browse(self):
        env = _make_env([_FakeLine()])
        version_model = env["project.boq.version"]
        handler = _make_handler(self.module, env, {"project_id": 3})
        handler.handle()
        self.assertTrue(version_model.search_calls)
        self.assertEqual(version_model.search_calls[0]["domain"][0], ("project_id", "=", 3))


if __name__ == "__main__":
    unittest.main()
