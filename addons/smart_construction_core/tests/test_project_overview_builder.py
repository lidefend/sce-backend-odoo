# -*- coding: utf-8 -*-
"""G7.4-B ProjectOverviewBuilder 单元测试（桩加载模式，零 Odoo 运行时）。

builder 引用 ``..overview_rich_text_patch_service``（纯函数层，无 Odoo 依赖），
需伪造「services 根包 + builders 子包」双层包上下文后
spec_from_file_location 加载（模式仿 test_project_boq_preview_builder）。
"""
from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
import unittest
from pathlib import Path


SERVICES_DIR = Path(__file__).resolve().parents[1] / "services"
BUILDERS_DIR = SERVICES_DIR / "project_dashboard_builders"

ROOT_PKG = "sc_test_overview_builders"
BUILDERS_PKG = ROOT_PKG + ".project_dashboard_builders"

_root = types.ModuleType(ROOT_PKG)
_root.__path__ = [str(SERVICES_DIR)]
sys.modules[ROOT_PKG] = _root

_pkg = types.ModuleType(BUILDERS_PKG)
_pkg.__path__ = [str(BUILDERS_DIR)]
sys.modules[BUILDERS_PKG] = _pkg


def _load(dotted_name, relpath):
    spec = importlib.util.spec_from_file_location(dotted_name, Path(relpath))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted_name] = module
    spec.loader.exec_module(module)
    return module


service_mod = _load(
    ROOT_PKG + ".overview_rich_text_patch_service",
    SERVICES_DIR / "overview_rich_text_patch_service.py",
)
base_mod = _load(BUILDERS_PKG + ".base", BUILDERS_DIR / "base.py")
builder_mod = _load(
    BUILDERS_PKG + ".project_overview_builder",
    BUILDERS_DIR / "project_overview_builder.py",
)


class _FakeParamApi:
    def __init__(self, raw):
        self._raw = raw

    def sudo(self):
        return self

    def get_param(self, key):
        return self._raw if key == service_mod.FLAG_KEY else None


class _FakeUser:
    def __init__(self, in_group):
        self._in_group = bool(in_group)

    def has_group(self, xmlid):
        return self._in_group and xmlid == builder_mod.RICH_TEXT_EDITOR_GROUP


class _FakeEnv:
    def __init__(self, flag_raw=None, in_group=False):
        self._params = _FakeParamApi(flag_raw)
        self.user = _FakeUser(in_group)

    def get(self, model_name):
        return self._params if model_name == "ir.config_parameter" else None


class _FakeProject:
    def __init__(self, pid, content=""):
        self.id = int(pid)
        self.overview_html = content


def _digest(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


class TestProjectOverviewBuilder(unittest.TestCase):
    def _builder(self, env=None):
        return builder_mod.ProjectOverviewBuilder(env or _FakeEnv())

    def _build(self, env=None, project="unset"):
        builder = self._builder(env)
        if project == "unset":
            project = _FakeProject(2, "<p>概况</p>")
        return builder.build(project=project, context={})

    def test_envelope_structure(self):
        block = self._build()
        self.assertEqual(block["block_key"], "block.project.overview")
        self.assertEqual(block["block_type"], "rich_text_overview")
        self.assertEqual(block["title"], "项目概况")
        self.assertEqual(block["state"], "ready")
        self.assertTrue(block["visibility"]["allowed"])
        self.assertTrue(block["source_authority"]["projection_only"])
        self.assertEqual(block["error"]["code"], "")

    def test_no_project_empty_state(self):
        block = self._build(project=None)
        self.assertEqual(block["state"], "empty")
        self.assertEqual(block["data"]["content"], "")
        self.assertEqual(block["data"]["overview_digest"], _digest(""))
        self.assertFalse(block["data"]["can_edit"])
        self.assertNotIn("project_id", block["data"])

    def test_content_projection_and_digest(self):
        content = "<h2>标题</h2><p>段落</p>"
        block = self._build(project=_FakeProject(7, content))
        self.assertEqual(block["state"], "ready")
        self.assertEqual(block["data"]["content"], content)
        self.assertEqual(block["data"]["overview_digest"], _digest(content))
        self.assertEqual(block["data"]["content_length"], len(content))
        self.assertEqual(block["data"]["max_length"], service_mod.MAX_LENGTH)
        self.assertEqual(block["data"]["project_id"], 7)
        self.assertEqual(block["data"]["patch_intent"], "project.overview.rich_text.patch")

    def test_can_edit_requires_flag_and_group(self):
        cases = [
            (None, False, False),      # flag 缺席（fail-closed）
            ("false", True, False),    # flag 显式关
            ("0", True, False),
            ("yes", True, True),       # flag 开 + 组在
            ("on", False, False),      # flag 开 + 无组
        ]
        for flag_raw, in_group, expected in cases:
            block = self._build(env=_FakeEnv(flag_raw=flag_raw, in_group=in_group))
            self.assertEqual(block["data"]["can_edit"], expected)

    def test_param_model_absent_fail_closed(self):
        class _NoModelEnv(_FakeEnv):
            def get(self, model_name):
                return None

        block = self._build(env=_NoModelEnv(flag_raw="true", in_group=True))
        self.assertFalse(block["data"]["can_edit"])

    def test_env_exception_fail_closed(self):
        class _BrokenEnv(_FakeEnv):
            def get(self, model_name):
                raise RuntimeError("boom")

        block = self._build(env=_BrokenEnv())
        self.assertFalse(block["data"]["can_edit"])

    def test_empty_content_is_empty_state(self):
        block = self._build(project=_FakeProject(9, ""))
        self.assertEqual(block["state"], "empty")
        self.assertEqual(block["data"]["overview_digest"], _digest(""))


class TestProjectOverviewEntrySpec(unittest.TestCase):
    """钉住场景 enter 契约接线：overview 块必须进入驾驶舱 entry_blocks。

    BaseSceneEntryOrchestrator 依据 hook facts spec 的 entry_blocks 生成
    blocks + runtime_fetch_hints（前端 hydrateDeferredBlocks 的消费源），
    缺失该声明时新块不会出现在 enter 契约（G7.4-B 断点回归钉子）。
    """

    def test_dashboard_entry_spec_includes_overview_block(self):
        facts = _load(
            ROOT_PKG + ".core_extension_hook_facts",
            Path(__file__).resolve().parents[1] / "core_extension_hook_facts.py",
        )
        spec = facts.scene_entry_orchestrator_specs()["ProjectDashboardSceneOrchestrator"]
        entry_keys = [key for key, _title, _state in spec["entry_blocks"]]
        self.assertIn("overview", entry_keys)
        block_titles = {key: title for key, title, _state in spec["entry_blocks"]}
        self.assertEqual(block_titles.get("overview"), "项目概况")
        # 拉块 intent 与别名表必须兼容 overview 短名（RUNTIME_BLOCK_MAP 已注册）
        self.assertEqual(spec["block_fetch_intent"], "project.dashboard.block.fetch")
        self.assertNotIn("overview", spec.get("block_alias_map") or {})

    def test_dashboard_entry_spec_includes_chart_blocks(self):
        """G6 图表块 enter 契约接线钉子（PR #446 浏览器走查缺口回归）。

        G6.1/G6.2 四处接线（builder/BUILDERS/ZONE_BLOCKS/RUNTIME_BLOCK_MAP/
        scene_content zone_blocks）未覆盖 hook facts entry_blocks 时，
        enter 契约不下发图表块 stub，前端 hydrateDeferredBlocks 无从拉取，
        dashboard 图表整体不可见——须钉住短名与标题防回退。
        """
        facts = _load(
            ROOT_PKG + ".core_extension_hook_facts",
            Path(__file__).resolve().parents[1] / "core_extension_hook_facts.py",
        )
        spec = facts.scene_entry_orchestrator_specs()["ProjectDashboardSceneOrchestrator"]
        entry_keys = [key for key, _title, _state in spec["entry_blocks"]]
        self.assertIn("chart", entry_keys)
        self.assertIn("chart_payment", entry_keys)
        block_titles = {key: title for key, title, _state in spec["entry_blocks"]}
        self.assertEqual(block_titles.get("chart"), "成本结构图表")
        self.assertEqual(block_titles.get("chart_payment"), "付款执行图表")
        # 短名直连 RUNTIME_BLOCK_MAP（chart/chart_payment 均已注册），
        # 不得进入 block_alias_map（alias 仅用于历史不一致命名收口）。
        alias_map = spec.get("block_alias_map") or {}
        self.assertNotIn("chart", alias_map)
        self.assertNotIn("chart_payment", alias_map)
        # 块状态必须 deferred（enter 契约 stub 语义，前端据此触发运行时拉取）
        block_states = {key: state for key, _title, state in spec["entry_blocks"]}
        self.assertEqual(block_states.get("chart"), "deferred")
        self.assertEqual(block_states.get("chart_payment"), "deferred")


if __name__ == "__main__":
    unittest.main()
