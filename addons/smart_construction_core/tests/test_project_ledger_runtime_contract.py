# -*- coding: utf-8 -*-
"""项目台账唯一入口：运行契约承载 lock（声明 -> 投影 -> 受管修复）。

把承载要求从"声明"层钉到"运行契约"层，并按「先确认未注入的基线正常，才能
证明注入被检出」给出负例：基线运行契约已承载退役页完整字段；注入与退役遗留
同形的 legacy 字段策略后承载确实丢失(问题可复现)；受管修复退役该遗留策略后
承载恢复(修复被检出)。锁的是声明消费与实际投影行为，不依赖选择器字符串或
文本出现。
"""

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("core_extension_v2_finalize")
class TestProjectLedgerRuntimeContract(TransactionCase):
    # --- 项目台账唯一入口：运行契约承载 lock（声明 -> 投影 -> 受管修复） -------
    #
    # 上面的锁证明"声明"层承载完整；这一组把同样的要求钉到"运行契约"层，并按
    # 「先确认未注入的基线正常，才能证明注入被检出」给出负例：基线运行契约已
    # 承载退役页完整字段；注入与退役遗留同形的 legacy 字段策略后承载确实丢失
    # (问题可复现)；受管修复退役该遗留策略后承载恢复(修复被检出)。锁的是声明
    # 消费与实际投影行为，不依赖选择器字符串或文本出现。

    _LEDGER_ACTION_XMLID = "smart_construction_core.action_sc_project_list"
    _LEDGER_FORM_VIEW_XMLID = "smart_construction_core.view_project_overview_form"
    _RETIRED_FORM_VIEW_XMLID = (
        "smart_construction_core.view_sc_product_project_information_edit_form_v1"
    )

    def _runtime_form_field_names(self, *, action_id=None, view_id=None, record_id=None):
        from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler

        params = {
            "op": "model",
            "model": "project.project",
            "view_type": "form",
            "render_profile": "edit",
            "client_type": "web_pc",
        }
        if action_id:
            params["action_id"] = int(action_id)
        if view_id:
            params["view_id"] = int(view_id)
        if record_id:
            params["record_id"] = int(record_id)
        result = UiContractV2Handler(
            self.env, su_env=self.env["ir.model"].sudo().env
        ).handle(params)
        result = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(result.get("ok", True), result.get("error"))

        names: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                if node.get("fieldName"):
                    names.add(node["fieldName"])
                if node.get("name") and node.get("widget"):
                    names.add(node["name"])
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk((result["data"] or {}).get("layoutContract"))
        return names

    def test_project_ledger_runtime_contract_carries_the_retired_form_composition(self):
        project = self.env["project.project"].create({"name": "台账运行契约承载 lock"})
        ledger = self._runtime_form_field_names(
            action_id=self.env.ref(self._LEDGER_ACTION_XMLID).id,
            record_id=project.id,
        )
        retired = self._runtime_form_field_names(
            view_id=self.env.ref(self._RETIRED_FORM_VIEW_XMLID).id,
            record_id=project.id,
        )
        self.assertTrue(retired, "retired 项目信息编辑 form must still resolve")
        self.assertEqual(
            sorted(retired - ledger),
            [],
            "项目台账 runtime contract must carry every 项目信息编辑 field",
        )
        self.assertIn(
            "project_code",
            ledger,
            "项目编号 must render on the unified ledger runtime contract",
        )

    def test_stale_ledger_field_overlay_is_detected_and_repaired(self):
        from odoo.addons.smart_construction_core.services import (
            project_ledger_field_overlay_repair as repair,
        )

        action = self.env.ref(self._LEDGER_ACTION_XMLID)
        project = self.env["project.project"].create({"name": "台账字段投影修复 lock"})
        baseline = self._runtime_form_field_names(
            action_id=action.id, record_id=project.id
        )
        self.assertIn(
            "project_code",
            baseline,
            "clean baseline must already carry the declared composition",
        )

        required = repair.ledger_required_field_names(self.env)
        self.assertIn("project_code", required)
        stale = self.env["ui.form.field.policy"].sudo().create(
            {
                "model": "project.project",
                "action_id": action.id,
                "field_name": "project_code",
                "label": "项目编号",
                "visible": False,
                "active": True,
            }
        )
        self.env.flush_all()
        suppressed = self._runtime_form_field_names(
            action_id=action.id, record_id=project.id
        )
        self.assertNotIn(
            "project_code",
            suppressed,
            "the injected stale overlay must be observable before it can be repaired",
        )

        report = repair.retire_stale_ledger_field_overlay(self.env, dry_run=False)
        self.assertEqual(report["status"], "applied")
        self.assertFalse(stale.active)
        self.env.flush_all()
        restored = self._runtime_form_field_names(
            action_id=action.id, record_id=project.id
        )
        self.assertIn(
            "project_code",
            restored,
            "the governed repair must restore the declared composition",
        )
