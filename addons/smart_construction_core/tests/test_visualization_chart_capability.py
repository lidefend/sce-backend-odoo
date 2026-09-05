# -*- coding: utf-8 -*-
"""visualization.chart capability 契约单测（G6.1，ADR-002 条件 4）。

桩加载模式：不依赖 Odoo 数据库，验证
- 注册表纪律：缺字段/坏 key/坏类型/缺 source_authority 拒绝登记
- handler 降级链：缺参 → MISSING_PARAMS；未登记 chart → CHART_NOT_REGISTERED
  （结构化，不抛异常，前端渲染通用空态）；项目不可访问 → PROJECT_NOT_FOUND；
  构建器异常 → CHART_DATASET_ERROR
- 正常路径 → sc.visualization.chart.v1 投影（series 透传、readonly）
- 契约登记：contracts/domain/chart.yaml v1 已在 registry.yaml 双向登记
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ADDON_ROOT = Path(__file__).resolve().parents[1]


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


def _load_registry_module():
    module_name = "odoo.addons.smart_construction_core.services.visualization_chart_registry"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        ADDON_ROOT / "services" / "visualization_chart_registry.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_handler_module(registry_module):
    _install_module("odoo")
    _install_module("odoo.addons")
    core_root = ADDON_ROOT.parent / "smart_core"
    smart_core_mod = _install_module("odoo.addons.smart_core")
    core_mod = _install_module("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(core_root)]
    core_mod.__path__ = [str(core_root / "core")]
    _install_module("odoo.addons.smart_core.core.base_handler", BaseIntentHandler=_BaseIntentHandler)
    _install_module("odoo.addons.smart_construction_core")
    services_pkg = _install_module("odoo.addons.smart_construction_core.services")
    services_pkg.visualization_chart_registry = registry_module

    module_name = "odoo.addons.smart_construction_core.handlers.visualization_chart_fetch"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(
        module_name,
        ADDON_ROOT / "handlers" / "visualization_chart_fetch.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 测试桩
# ---------------------------------------------------------------------------


class _FakeProject:
    def __init__(self, project_id):
        self.id = project_id


class _FakeProjectRecordset:
    def __init__(self, rows):
        self._rows = list(rows)

    def __bool__(self):
        return bool(self._rows)


class _FakeProjectModel:
    def __init__(self, visible_ids):
        self._visible = set(visible_ids)
        self.calls = []

    def search(self, domain, limit=None, order=None):
        self.calls.append({"domain": domain, "limit": limit})
        rows = []
        for clause in domain or []:
            if len(clause) == 3 and clause[0] == "id":
                if clause[2] in self._visible:
                    rows = [_FakeProject(clause[2])]
        return _FakeProjectRecordset(rows)


class _FakeEnv(dict):
    def __init__(self, project_model):
        super().__init__({"project.project": project_model})
        self.context = {}


def _valid_chart_defn(registry, builder=None):
    return {
        "key": "project.cost.structure",
        "label": "成本构成",
        "chart_type": "bar",
        "metric": {"key": "amount", "label": "金额", "unit": "CNY"},
        "dimensions": [{"key": "category", "label": "成本科目"}],
        "unit": "CNY",
        "source_authority": {
            "kind": "visualization_chart_readonly_projection",
            "authorities": ["project.cost.line"],
            "projection_only": True,
            "no_business_fact_authority": True,
        },
        "dataset_builder": builder or (lambda env, project_id: []),
    }


# ---------------------------------------------------------------------------
# 注册表纪律
# ---------------------------------------------------------------------------


class VisualizationChartRegistryDisciplineTests(unittest.TestCase):
    def setUp(self):
        self.registry = _load_registry_module()

    def tearDown(self):
        self.registry.reset_charts()

    def test_valid_definition_registers_and_resolves(self):
        self.registry.register_chart(_valid_chart_defn(self.registry))
        chart = self.registry.get_chart("project.cost.structure")
        self.assertIsNotNone(chart)
        self.assertEqual(chart["chart_type"], "bar")
        self.assertEqual(self.registry.list_chart_keys(), ["project.cost.structure"])

    def test_duplicate_key_rejected(self):
        self.registry.register_chart(_valid_chart_defn(self.registry))
        with self.assertRaises(ValueError):
            self.registry.register_chart(_valid_chart_defn(self.registry))

    def test_missing_required_fields_rejected(self):
        defn = _valid_chart_defn(self.registry)
        del defn["metric"]
        with self.assertRaises(ValueError):
            self.registry.register_chart(defn)

    def test_bad_key_format_rejected(self):
        for bad_key in ("Project.Cost.Structure", "cost", "a.b.c.d", "cost structure"):
            defn = _valid_chart_defn(self.registry)
            defn["key"] = bad_key
            with self.assertRaises(ValueError):
                self.registry.register_chart(defn)

    def test_bad_chart_type_rejected(self):
        defn = _valid_chart_defn(self.registry)
        defn["chart_type"] = "radar3d"
        with self.assertRaises(ValueError):
            self.registry.register_chart(defn)

    def test_missing_source_authority_rejected(self):
        defn = _valid_chart_defn(self.registry)
        defn["source_authority"] = {"authorities": ["project.cost.line"]}
        with self.assertRaises(ValueError):
            self.registry.register_chart(defn)

    def test_non_callable_builder_rejected(self):
        defn = _valid_chart_defn(self.registry)
        defn["dataset_builder"] = "not-callable"
        with self.assertRaises(ValueError):
            self.registry.register_chart(defn)

    def test_unknown_key_returns_none(self):
        self.assertIsNone(self.registry.get_chart("project.nothing.chart"))


# ---------------------------------------------------------------------------
# handler 降级与正常路径
# ---------------------------------------------------------------------------


class VisualizationChartFetchHandlerTests(unittest.TestCase):
    def setUp(self):
        self.registry = _load_registry_module()
        self.registry.reset_charts()
        self.module = _load_handler_module(self.registry)

    def tearDown(self):
        self.registry.reset_charts()

    def _handler(self, env, params=None):
        return self.module.VisualizationChartFetchHandler(
            env=env, params=params or {}, payload={}
        )

    def test_missing_params_returns_structured_error(self):
        handler = self._handler(_FakeEnv(_FakeProjectModel([2])), {"project_id": 2})
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "MISSING_PARAMS")
        self.assertEqual(result["error"]["suggested_action"], "fix_input")
        self.assertIn("source_authority", result["meta"])

    def test_unregistered_chart_degrades_structurally(self):
        handler = self._handler(
            _FakeEnv(_FakeProjectModel([2])),
            {"chart_key": "project.unknown.chart", "project_id": 2},
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "CHART_NOT_REGISTERED")
        self.assertEqual(result["data"]["chart_key"], "project.unknown.chart")
        self.assertEqual(
            result["data"]["schema"],
            self.registry.CHART_SCHEMA_VERSION,
        )

    def test_project_not_found_same_semantics_as_inaccessible(self):
        self.registry.register_chart(_valid_chart_defn(self.registry))
        handler = self._handler(
            _FakeEnv(_FakeProjectModel([])),  # 不可见 = 不存在
            {"chart_key": "project.cost.structure", "project_id": 404},
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "PROJECT_NOT_FOUND")

    def test_registered_chart_returns_v1_projection(self):
        series = [
            {
                "name": "成本构成",
                "metric": {"key": "amount", "label": "金额"},
                "dimensions": [{"key": "category", "label": "成本科目"}],
                "points": [
                    {"dimension_value": "人工", "value": 320000.0},
                    {"dimension_value": "材料", "value": 442000.0},
                ],
            }
        ]
        self.registry.register_chart(
            _valid_chart_defn(self.registry, builder=lambda env, pid: series)
        )
        handler = self._handler(
            _FakeEnv(_FakeProjectModel([2])),
            {"chart_key": "project.cost.structure", "project_id": 2},
        )
        result = handler.handle()
        self.assertTrue(result["ok"])
        data = result["data"]
        self.assertEqual(data["schema"], "sc.visualization.chart.v1")
        self.assertEqual(data["chart_key"], "project.cost.structure")
        self.assertEqual(data["chart_type"], "bar")
        self.assertEqual(data["title"], "成本构成")
        self.assertTrue(data["readonly"])
        self.assertEqual(data["series"], series)

    def test_builder_exception_degrades_to_chart_dataset_error(self):
        def _boom(env, project_id):
            raise RuntimeError("dataset builder exploded")

        self.registry.register_chart(_valid_chart_defn(self.registry, builder=_boom))
        handler = self._handler(
            _FakeEnv(_FakeProjectModel([2])),
            {"chart_key": "project.cost.structure", "project_id": 2},
        )
        result = handler.handle()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "CHART_DATASET_ERROR")
        self.assertEqual(result["error"]["suggested_action"], "retry_or_contact_admin")


# ---------------------------------------------------------------------------
# 契约登记钉死（静态）
# ---------------------------------------------------------------------------


class ChartContractRegistrationTests(unittest.TestCase):
    def test_domain_chart_yaml_exists_with_version_and_readonly(self):
        text = (REPO_ROOT / "contracts" / "domain" / "chart.yaml").read_text(encoding="utf-8")
        self.assertIn("id: chart", text)
        self.assertIn("version: 1", text)
        self.assertIn("read_only: true", text)
        self.assertIn("sc.visualization.chart.v1", text)
        self.assertIn("CHART_NOT_REGISTERED", text)

    def test_registry_yaml_registers_chart_contract(self):
        text = (REPO_ROOT / "contracts" / "registry.yaml").read_text(encoding="utf-8")
        self.assertIn("path: domain/chart.yaml", text)
        self.assertIn("domain: chart", text)

    def test_services_package_wires_registry(self):
        text = (ADDON_ROOT / "services" / "__init__.py").read_text(encoding="utf-8")
        self.assertIn("from . import visualization_chart_registry", text)


if __name__ == "__main__":
    unittest.main()
