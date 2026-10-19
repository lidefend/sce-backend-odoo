# -*- coding: utf-8 -*-
import importlib.util
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def _load_module(module_name: str, relative_path: str):
    target = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, target)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


STATE_EXPLAIN_MODULE = _load_module(
    "odoo.addons.smart_construction_core.services.project_state_explain_service",
    "addons/smart_construction_core/services/project_state_explain_service.py",
)
PROJECT_CONTEXT_MODULE = _load_module(
    "odoo.addons.smart_construction_core.services.project_context_contract",
    "addons/smart_construction_core/services/project_context_contract.py",
)
CONTRACT_GOVERNANCE_MODULE = _load_module(
    "smart_core_contract_governance_test_module",
    "addons/smart_core/utils/contract_governance.py",
)

build_project_context = PROJECT_CONTEXT_MODULE.build_project_context
ProjectStateExplainService = STATE_EXPLAIN_MODULE.ProjectStateExplainService
lifecycle_state_label = STATE_EXPLAIN_MODULE.lifecycle_state_label
apply_project_form_domain_override = CONTRACT_GOVERNANCE_MODULE.apply_project_form_domain_override


# ScStateMachine.PROJECT_STATES 的声明选择项是 lifecycle_state 唯一标签真源。
# 本测试不 import odoo，因此把声明值固化为此测试的期望事实（反例）而非产品映射。
PROJECT_LIFECYCLE_SELECTION = [
    ("draft", "草稿"),
    ("in_progress", "在建"),
    ("paused", "停工"),
    ("done", "竣工"),
    ("closing", "结算中"),
    ("warranty", "保修期"),
    ("closed", "关闭"),
]


def _project_fields():
    """Odoo Selection 字段的离线替身：声明通过 _description_selection(env) 消费。"""
    return {
        "lifecycle_state": SimpleNamespace(
            _description_selection=lambda env: PROJECT_LIFECYCLE_SELECTION
        )
    }


class TestProjectSemanticCarriers(unittest.TestCase):
    def test_build_project_context_adds_explicit_execution_stage_and_condition_aliases(self):
        project = SimpleNamespace(
            id=7,
            display_name="项目-A",
            name="项目-A",
            lifecycle_state="in_progress",
            sc_execution_state="ready",
            sc_execution_state_label="准备完成",
            health_state="attention",
            state="legacy",
            _fields=_project_fields(), env=SimpleNamespace(lang="zh_CN"),
        )

        result = build_project_context(project)

        self.assertEqual(result.get("execution_stage"), "in_progress")
        self.assertEqual(result.get("execution_stage_label"), "在建")
        self.assertEqual(result.get("stage"), "in_progress")
        self.assertEqual(result.get("stage_label"), "在建")
        self.assertEqual(result.get("project_condition"), "attention")
        self.assertEqual(result.get("status"), "attention")

    def test_state_explain_adds_execution_stage_and_project_condition_aliases(self):
        project = SimpleNamespace(
            lifecycle_state="closing",
            health_state="risk",
            state="legacy",
            _fields=_project_fields(), env=SimpleNamespace(lang="zh_CN"),
        )

        result = ProjectStateExplainService(env=None).build(project)

        self.assertEqual(result.get("execution_stage_label"), "结算中")
        self.assertEqual(result.get("stage_label"), "结算中")
        self.assertIn("结算中阶段", result.get("execution_stage_explain") or "")
        self.assertEqual(result.get("execution_stage_explain"), result.get("stage_explain"))
        self.assertEqual(result.get("project_condition_explain"), "risk")
        self.assertEqual(result.get("status_explain"), "risk")

    def test_state_explain_empty_case_keeps_compat_and_new_fields(self):
        result = ProjectStateExplainService(env=None).build(None)

        self.assertEqual(result.get("execution_stage_label"), "未选择项目")
        self.assertEqual(result.get("stage_label"), "未选择项目")
        self.assertEqual(result.get("project_condition_explain"), "请先选择项目或创建项目。")
        self.assertEqual(result.get("status_explain"), "请先选择项目或创建项目。")

    def test_project_ledger_list_view_declares_f02_f03_fields(self):
        """项目台账 list view 是 F02/F03 的 P1 声明载体。

        旧断言依赖 P0 contract_governance._PROJECT_LIST_COLUMN_LABELS——把生命周期
        列文案「项目执行阶段」硬编码在 P0 层，该 P0 行业常量已移除，不再恢复。
        现状归属层是 P1 视图声明：项目台账树视图声明 operation_strategy/lifecycle_state
        两列及其中文标签，前端卡片消费的正是这两列（经营方式/状态）。
        """
        ledger_tree = ET.parse(
            ROOT / "addons/smart_construction_core/views/core/project_list_views.xml"
        ).getroot()
        columns = {field.get("name"): field.get("string") for field in ledger_tree.iter("field")}
        self.assertEqual(columns.get("operation_strategy"), "经营方式")
        self.assertEqual(columns.get("lifecycle_state"), "项目状态")

    def test_request_environment_and_translation_failure_are_authoritative(self):
        request_env = SimpleNamespace(lang="zh_CN")
        observed = []
        def describe(env):
            observed.append(env)
            return [("closing", "请求语言标签")]
        field = SimpleNamespace(_description_selection=describe, selection=[("closing", "错误兜底")])
        record = SimpleNamespace(lifecycle_state="closing", env=request_env, _fields={"lifecycle_state": field})
        self.assertEqual(lifecycle_state_label(record), "请求语言标签")
        self.assertIs(observed[0], request_env)
        def fail(env):
            raise RuntimeError("translation failed")
        field._description_selection = fail
        with self.assertRaisesRegex(RuntimeError, "translation failed"):
            lifecycle_state_label(record)
        field._description_selection = lambda env: [("closing", " ")]
        with self.assertRaises(ValueError):
            lifecycle_state_label(record)

    def test_lifecycle_label_consumes_declared_selection(self):
        # Odoo 支持路径：field._description_selection(record.env)。
        record = SimpleNamespace(
            lifecycle_state="closing",
            _fields=_project_fields(), env=SimpleNamespace(lang="zh_CN"),
        )
        self.assertEqual(lifecycle_state_label(record), "结算中")

        expected = dict(PROJECT_LIFECYCLE_SELECTION)
        for code, label in PROJECT_LIFECYCLE_SELECTION:
            project = SimpleNamespace(
                lifecycle_state=code,
                _fields=_project_fields(), env=SimpleNamespace(lang="zh_CN"),
            )
            self.assertEqual(
                lifecycle_state_label(project),
                label,
                "lifecycle_state_label must consume the declared selection",
            )

        # 反例：与声明不一致的旧私有映射值不得再作为标签输出（draft/paused/done/closing/warranty）。
        for code in ("draft", "paused", "done", "closing", "warranty"):
            project = SimpleNamespace(
                lifecycle_state=code,
                _fields=_project_fields(), env=SimpleNamespace(lang="zh_CN"),
            )
            self.assertEqual(lifecycle_state_label(project), expected[code])

        # Raw static/callable values cannot replace Odoo's translated interface.
        for raw in (PROJECT_LIFECYCLE_SELECTION, lambda: PROJECT_LIFECYCLE_SELECTION):
            field = SimpleNamespace(selection=raw)
            with self.assertRaises(AttributeError):
                lifecycle_state_label(SimpleNamespace(
                    lifecycle_state="draft", env=SimpleNamespace(lang="zh_CN"),
                    _fields={"lifecycle_state": field},
                ))
        # 空值按既有契约返回默认标签。
        self.assertEqual(
            lifecycle_state_label(SimpleNamespace(lifecycle_state="", _fields=_project_fields())),
            "未设置阶段",
        )
        # 非法缺声明：非空状态不得静默兜底成英文 key，必须显式报缺口。
        with self.assertRaises(ValueError):
            lifecycle_state_label("closing")
        with self.assertRaises(ValueError):
            lifecycle_state_label(SimpleNamespace(lifecycle_state="draft", _fields={}))
        with self.assertRaises(ValueError):
            lifecycle_state_label(
                SimpleNamespace(lifecycle_state="ghost", _fields=_project_fields())
            )


if __name__ == "__main__":
    unittest.main()
