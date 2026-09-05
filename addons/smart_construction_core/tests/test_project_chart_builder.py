# -*- coding: utf-8 -*-
"""G6.1 ProjectChartBuilder 单元测试（桩加载模式，零 Odoo 运行时）。

镜像 test_project_boq_preview_builder.py：builder 与 base 均无 Odoo
运行时依赖；注册表经惰性 odoo 路径导入解析，测试以桩包注入。
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ADDON_ROOT = Path(__file__).resolve().parents[1]
BUILDERS_DIR = ADDON_ROOT / "services" / "project_dashboard_builders"

PKG = "sc_test_chart_builders"

_pkg = types.ModuleType(PKG)
_pkg.__path__ = [str(BUILDERS_DIR)]
sys.modules[PKG] = _pkg


def _load(dotted_name, relpath):
    spec = importlib.util.spec_from_file_location(dotted_name, BUILDERS_DIR / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module


base_mod = _load(f"{PKG}.base", "base.py")
builder_mod = _load(f"{PKG}.project_chart_builder", "project_chart_builder.py")


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


class _RegistryStubSession:
    """安装/卸载惰性导入所需的桩 odoo 包路径。"""

    def __init__(self, registry):
        self._names = [
            "odoo",
            "odoo.addons",
            "odoo.addons.smart_construction_core",
            "odoo.addons.smart_construction_core.services",
        ]
        self._saved = {}
        self._registry = registry

    def __enter__(self):
        for name in self._names:
            self._saved[name] = sys.modules.get(name)
        pkg = types.ModuleType("odoo.addons.smart_construction_core.services")
        pkg.visualization_chart_registry = self._registry
        sys.modules["odoo"] = types.ModuleType("odoo")
        sys.modules["odoo.addons"] = types.ModuleType("odoo.addons")
        sys.modules["odoo.addons.smart_construction_core"] = types.ModuleType(
            "odoo.addons.smart_construction_core"
        )
        sys.modules["odoo.addons.smart_construction_core.services"] = pkg
        return self

    def __exit__(self, *exc):
        for name, module in self._saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
        return False


class _FakeEnv(dict):
    pass


class _FakeProject:
    def __init__(self, pid):
        self.id = int(pid)


def _valid_chart_defn():
    return {
        "key": "project.cost.structure",
        "label": "成本结构（预算 vs 实际）",
        "chart_type": "bar",
        "metric": {"key": "amount", "label": "金额"},
        "dimensions": [{"key": "cost_code", "label": "成本科目"}],
        "source_authority": {
            "kind": "project_cost_readonly_projection",
            "authorities": ["project.cost.ledger"],
            "projection_only": True,
            "no_business_fact_authority": True,
        },
        "dataset_builder": lambda env, project_id: [],
    }


class TestProjectChartBuilder(unittest.TestCase):
    def _builder(self):
        env = _FakeEnv()
        return builder_mod.ProjectChartBuilder(env), env

    def test_block_identity(self):
        builder, _ = self._builder()
        self.assertEqual(builder.block_key, "block.project.chart")
        self.assertEqual(builder.block_type, "chart_dataset")

    def test_empty_when_no_project(self):
        builder, _ = self._builder()
        envelope = builder.build(project=None, context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertEqual(envelope["data"]["project_id"], 0)
        self.assertFalse(envelope["data"]["chart_registered"])

    def test_empty_when_registry_unreachable(self):
        # 注册表不可达（无桩 odoo 路径）→ 块级 empty，不抛异常。
        builder, _ = self._builder()
        envelope = builder.build(project=_FakeProject(7), context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertEqual(envelope["data"]["chart_registered"], False)

    def test_empty_when_chart_not_registered(self):
        registry = _load_registry_module()
        registry.reset_charts()
        with _RegistryStubSession(registry):
            builder, _ = self._builder()
            envelope = builder.build(project=_FakeProject(7), context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertFalse(envelope["data"]["chart_registered"])

    def test_ready_when_chart_registered(self):
        registry = _load_registry_module()
        registry.reset_charts()
        registry.register_chart(_valid_chart_defn())
        try:
            with _RegistryStubSession(registry):
                builder, _ = self._builder()
                envelope = builder.build(project=_FakeProject(7), context=None)
        finally:
            registry.reset_charts()
        self.assertEqual(envelope["state"], "ready")
        data = envelope["data"]
        self.assertEqual(data["project_id"], 7)
        self.assertTrue(data["chart_registered"])
        self.assertEqual(data["chart_key"], "project.cost.structure")
        self.assertEqual(data["fetch_intent"], "project.dashboard.chart.fetch")
        self.assertEqual(
            data["fetch_params"],
            {"chart_key": "project.cost.structure", "project_id": 7},
        )
        self.assertTrue(data["readonly"])

    def test_projection_carries_display_copy(self):
        builder, _ = self._builder()
        envelope = builder.build(project=_FakeProject(5), context=None)
        data = envelope["data"]
        self.assertIn("成本结构", data["loading_message"])
        self.assertIn("成本结构", data["empty_message"])
        self.assertIn("项目上下文", data["empty_message_no_context"])

    def test_visibility_allowed_for_internal_user(self):
        builder, _ = self._builder()
        envelope = builder.build(project=_FakeProject(1), context=None)
        self.assertEqual(envelope["visibility"]["allowed"], True)

    def test_forbidden_when_group_missing(self):
        class _Gated(builder_mod.ProjectChartBuilder):
            required_groups = ("smart_construction_core.group_sc_cap_cost_read",)

        class _DeniedUser:
            def has_group(self, _xmlid):
                return False

        class _GatedEnv(dict):
            user = _DeniedUser()

        builder = _Gated(_GatedEnv())
        envelope = builder.build(project=_FakeProject(1), context=None)
        self.assertEqual(envelope["state"], "forbidden")
        self.assertEqual(envelope["visibility"]["reason_code"], "PERMISSION_DENIED")


if __name__ == "__main__":
    unittest.main()
