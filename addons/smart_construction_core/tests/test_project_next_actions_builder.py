# -*- coding: utf-8 -*-
"""G3.3-B 驾驶舱 zone 覆盖缺口：ProjectNextActionsBuilder 单元测试（桩加载，零 Odoo 运行时）。

builder 与 base 均无 Odoo 运行时依赖；base 含相对导入，需伪造包上下文后
spec_from_file_location 加载（模式仿 test_project_boq_preview_builder.py）。
决策引擎经 env["sc.evidence.action.engine"].decide(project) 获取动作；
无目标字符串时以「下一步动作」空项兜底，保证不出现未注册块 fallback。
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


BUILDERS_DIR = Path(
    __file__).resolve().parents[1] / "services" / "project_dashboard_builders"

PKG = "sc_test_dash_builders"

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
builder_mod = _load(f"{PKG}.project_next_actions_builder", "project_next_actions_builder.py")


class _FakeDecisionEngine:
    def __init__(self, actions=None, raise_exc=False):
        self._actions = actions or []
        self._raise_exc = raise_exc

    def decide(self, project):
        if self._raise_exc:
            raise RuntimeError("engine exploded")
        return {"actions": list(self._actions)}


class _FakeEnv(dict):
    pass


class _FakeProject:
    def __init__(self, pid):
        self.id = int(pid)


class TestProjectNextActionsBuilder(unittest.TestCase):
    def _builder(self, actions=None, raise_exc=False):
        env = _FakeEnv({"sc.evidence.action.engine": _FakeDecisionEngine(actions, raise_exc)})
        return builder_mod.ProjectNextActionsBuilder(env), env

    def test_block_identity(self):
        builder, _ = self._builder()
        self.assertEqual(builder.block_key, "block.project.next_actions")
        self.assertEqual(builder.block_type, "todo_list")

    def test_empty_when_no_project(self):
        builder, _ = self._builder()
        envelope = builder.build(project=None, context=None)
        self.assertEqual(envelope["state"], "empty")
        self.assertEqual(envelope["data"]["items"], [])

    def test_ready_with_actions(self):
        actions = [
            {"action_key": "execute_entry", "label": "进入执行推进", "intent": "project.execution.enter", "reason": "fallback action"},
        ]
        builder, _ = self._builder(actions=actions)
        envelope = builder.build(project=_FakeProject(7), context=None)
        self.assertEqual(envelope["state"], "ready")
        self.assertEqual(envelope["block_type"], "todo_list")
        data = envelope["data"]
        self.assertIsInstance(data, dict)
        items = data["items"]
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["action_key"], "execute_entry")
        self.assertEqual(item["title"], "进入执行推进")
        self.assertEqual(item["target"], {"type": "intent", "intent": "project.execution.enter"})
        self.assertEqual(item["source"], "decision_engine")

    def test_fallback_item_when_no_actions(self):
        builder, _ = self._builder(actions=[])
        envelope = builder.build(project=_FakeProject(3), context=None)
        self.assertEqual(envelope["state"], "ready")
        items = envelope["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "no_next_action")
        self.assertEqual(items[0]["source"], "capability_fallback")
        self.assertEqual(items[0]["action_key"], "open_dashboard")

    def test_engine_raise_is_contained(self):
        builder, _ = self._builder(raise_exc=True)
        envelope = builder.build(project=_FakeProject(4), context=None)
        self.assertEqual(envelope["state"], "ready")
        self.assertEqual(envelope["data"]["items"][0]["id"], "no_next_action")

    def test_cap_item_count(self):
        actions = [{"action_key": f"k{i}", "label": f"动作{i}", "intent": f"intent{i}"} for i in range(10)]
        builder, _ = self._builder(actions=actions)
        envelope = builder.build(project=_FakeProject(5), context=None)
        self.assertEqual(len(envelope["data"]["items"]), builder.MAX_ITEMS)

    def test_visibility_allowed_for_internal_user(self):
        builder, _ = self._builder()
        envelope = builder.build(project=_FakeProject(1), context=None)
        self.assertEqual(envelope["visibility"]["allowed"], True)

    def test_forbidden_when_group_missing(self):
        class _Gated(builder_mod.ProjectNextActionsBuilder):
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
