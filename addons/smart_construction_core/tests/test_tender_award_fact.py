# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.smart_core.handlers.ui_contract_v2 import UiContractV2Handler


@tagged("post_install", "-at_install", "tender_award_fact")
class TestTenderAwardFact(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create(
            {
                "name": "中标事实确认测试项目",
                "company_id": cls.env.company.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "中标事实测试业主"})

    def _bid(self, name="中标事实测试投标", **values):
        values.update(
            {
                "tender_name": name,
                "project_id": self.project.id,
                "owner_id": self.partner.id,
            }
        )
        return self.env["tender.bid"].create(values)

    def _opening(self, bid, result="won", win_price=900.0):
        return self.env["tender.opening"].create(
            {
                "bid_id": bid.id,
                "result": result,
                "win_price": win_price,
            }
        )

    def _prepare_confirmation(self, bid, opening, **values):
        confirmation = {
            "state": "waiting",
            "award_opening_id": opening.id,
            "award_tax_basis": "unknown",
            "award_source_kind": "final_quote",
            "award_source_reference": "最终报价文件-TEST-001",
        }
        confirmation.update(values)
        bid.write(confirmation)

    def test_explicit_winning_opening_is_snapshotted_without_creating_contract(self):
        bid = self._bid(
            bid_amount=1200.0,
            line_ids=[(0, 0, {"name": "清单合计", "quantity": 1, "price": 1000.0})],
        )
        self._opening(bid, result="lost", win_price=1100.0)
        winning = self._opening(bid, result="won", win_price=900.0)
        self._prepare_confirmation(bid, winning)

        contract_count = self.env["construction.contract"].search_count([])
        bid.action_mark_won()

        self.assertEqual(bid.state, "won")
        self.assertEqual(bid.bid_amount, 1200.0)
        self.assertEqual(bid.amount_total, 1000.0)
        self.assertEqual(bid.award_amount, 900.0)
        self.assertEqual(bid.award_currency_id, winning.currency_id)
        self.assertEqual(bid.award_tax_basis, "unknown")
        self.assertEqual(bid.award_source_kind, "final_quote")
        self.assertEqual(bid.award_source_reference, "最终报价文件-TEST-001")
        self.assertEqual(bid.award_confirmed_by_id, self.env.user)
        self.assertTrue(bid.award_confirmed_at)
        self.assertEqual(bid.award_confirmation_state, "confirmed")
        self.assertFalse(bid.contract_id)
        self.assertEqual(
            self.env["construction.contract"].search_count([]), contract_count
        )
        self.assertIn("合同尚未生成", bid.award_contract_handoff_message)
        self.assertIn("900.00", winning.display_name)

        winning.write({"win_price": 850.0})
        bid.invalidate_recordset(["award_amount"])
        self.assertEqual(bid.award_amount, 900.0)

    def test_opening_must_belong_to_bid_and_record_a_winning_result(self):
        bid = self._bid("归属校验投标")
        other_bid = self._bid("其他投标")
        foreign_opening = self._opening(other_bid)
        self._prepare_confirmation(bid, foreign_opening)
        with self.assertRaisesRegex(UserError, "不属于当前投标"):
            bid.action_mark_won()

        losing = self._opening(bid, result="lost")
        bid.write({"award_opening_id": losing.id})
        with self.assertRaisesRegex(UserError, "结果不是中标"):
            bid.action_mark_won()

    def test_repeated_confirmation_is_idempotent_and_snapshot_is_immutable(self):
        bid = self._bid("防重确认投标")
        opening = self._opening(bid)
        self._prepare_confirmation(bid, opening)
        bid.action_mark_won()
        confirmed_at = bid.award_confirmed_at

        bid.action_mark_won()
        self.assertEqual(bid.award_confirmed_at, confirmed_at)
        self.assertEqual(bid.award_amount, 900.0)
        self.assertFalse(bid.contract_id)
        with self.assertRaisesRegex(UserError, "快照已确认"):
            bid.write({"award_amount": 901.0})
        with self.assertRaisesRegex(UserError, "不能直接更改状态"):
            bid.write({"state": "waiting"})

    def test_source_reference_is_required_while_unknown_tax_basis_is_allowed(self):
        bid = self._bid("未知税口径投标")
        opening = self._opening(bid)
        self._prepare_confirmation(bid, opening, award_source_reference="")
        with self.assertRaisesRegex(UserError, "编号或名称"):
            bid.action_mark_won()

        bid.write({"award_source_reference": "中标通知未载明税口径"})
        bid.action_mark_won()
        self.assertEqual(bid.award_tax_basis, "unknown")
        self.assertEqual(bid.award_amount, 900.0)

    def test_historical_won_record_is_not_backfilled(self):
        bid = self._bid("历史待核实投标", state="won")

        self.assertFalse(bid.award_confirmed_at)
        self.assertFalse(bid.award_amount)
        self.assertEqual(bid.award_confirmation_state, "legacy_unverified")
        self.assertIn("来源待核实", bid.award_contract_handoff_message)

    def test_direct_state_write_cannot_bypass_award_confirmation(self):
        bid = self._bid("禁止绕过确认动作")

        with self.assertRaisesRegex(UserError, "确认中标事实"):
            bid.write({"state": "won"})

    def test_form_declares_explicit_award_source_and_non_clickable_status(self):
        arch = self.env.ref("smart_construction_core.view_tender_bid_form").arch_db
        for field_name in (
            "award_opening_id",
            "award_tax_basis",
            "award_source_kind",
            "award_source_reference",
            "award_amount",
            "award_confirmation_state",
            "award_contract_handoff_message",
        ):
            self.assertIn('name="%s"' % field_name, arch)
        self.assertIn('string="确认中标事实"', arch)
        self.assertNotIn("'clickable': '1'", arch)
        contract = self.env.ref(
            "smart_construction_core.business_config_contract_tender_bid_registration_productized_form_v1"
        )
        formal_menu = self.env.ref("smart_construction_core.menu_sc_project_tender")
        formal_action = self.env.ref("smart_construction_core.action_tender_bid")
        self.assertTrue(formal_menu.active)
        self.assertEqual(formal_menu.action, formal_action)
        self.assertEqual(contract.action_id, formal_action)
        form_contract = contract.contract_json["view_orchestration"]["views"]["form"]
        self.assertEqual(form_contract["title"], "投标项目")
        configured_fields = {row["name"] for row in form_contract["fields"]}
        for field_name in (
            "award_opening_id",
            "award_amount",
            "award_tax_basis",
            "award_source_reference",
        ):
            self.assertIn(field_name, configured_fields)

    def test_formal_entry_contract_exposes_award_fact_fields(self):
        action = self.env.ref("smart_construction_core.action_tender_bid")
        menu = self.env.ref("smart_construction_core.menu_sc_project_tender")
        result = UiContractV2Handler(
            self.env,
            su_env=self.env["ir.model"].sudo().env,
        ).handle(
            {
                "model": "tender.bid",
                "view_type": "form",
                "record_id": "new",
                "action_id": action.id,
                "menu_id": menu.id,
                "client_type": "web_pc",
                "render_profile": "create",
            }
        )
        envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(envelope.get("ok", True), envelope)
        contract = envelope["data"]

        def collect_field_codes(value):
            if isinstance(value, dict):
                codes = [value["fieldCode"]] if value.get("fieldCode") else []
                for nested in value.values():
                    codes.extend(collect_field_codes(nested))
                return codes
            if isinstance(value, list):
                codes = []
                for nested in value:
                    codes.extend(collect_field_codes(nested))
                return codes
            return []

        field_codes = collect_field_codes(contract["layoutContract"]["containerTree"])
        for field_name in (
            "award_opening_id",
            "award_tax_basis",
            "award_source_reference",
            "award_confirmation_state",
            "award_contract_handoff_message",
        ):
            self.assertIn(field_name, field_codes)

    def test_formal_entry_contract_keeps_confirmation_action_available(self):
        bid = self._bid("正式入口动作投标", state="submitted")
        self._opening(bid)
        action = self.env.ref("smart_construction_core.action_tender_bid")
        menu = self.env.ref("smart_construction_core.menu_sc_project_tender")
        result = UiContractV2Handler(
            self.env,
            su_env=self.env["ir.model"].sudo().env,
        ).handle(
            {
                "model": "tender.bid",
                "view_type": "form",
                "record_id": bid.id,
                "action_id": action.id,
                "menu_id": menu.id,
                "client_type": "web_pc",
                "render_profile": "edit",
            }
        )
        envelope = result.to_legacy_dict() if hasattr(result, "to_legacy_dict") else result
        self.assertTrue(envelope.get("ok", True), envelope)
        contract = envelope["data"]
        rules = [
            row
            for row in contract["actionContract"]["actionRuleList"]
            if (row.get("button") or {}).get("name") == "action_mark_won"
        ]
        self.assertEqual(len(rules), 1, rules)
        rule = rules[0]
        self.assertEqual(rule["label"], "确认中标事实")
        self.assertTrue(rule["allowed"], rule)
        self.assertTrue(rule["enabled"], rule)
        self.assertTrue(rule["entitlementEvaluated"], rule)
        self.assertIn("edit", rule["visibleProfiles"])
        self.assertEqual(
            sum(
                candidate.get("actionId") == rule["actionId"]
                for candidate in contract["actionContract"]["actionRuleList"]
            ),
            1,
        )
        self.assertEqual(
            sum(
                candidate.get("backendIdentity") == rule["backendIdentity"]
                for candidate in contract["actionContract"]["actionRuleList"]
            ),
            1,
        )
        statuses = [
            row
            for row in contract["statusContract"]["buttonStatus"]
            if row.get("backendIdentity") == rule["backendIdentity"]
        ]
        self.assertEqual(len(statuses), 1, statuses)
        status = statuses[0]
        self.assertTrue(status["visible"], status)
        self.assertFalse(status["disabled"], status)
        self.assertIn("award_confirmed_at", contract["dataContract"]["mainData"])
        self.assertFalse(contract["dataContract"]["mainData"]["award_confirmed_at"])

        award_widget_ids = {}

        def collect_award_widgets(value):
            if isinstance(value, dict):
                field_code = value.get("fieldCode")
                widget_id = value.get("widgetId")
                if field_code and widget_id and field_code.startswith("award_"):
                    award_widget_ids.setdefault(field_code, []).append(widget_id)
                for nested in value.values():
                    collect_award_widgets(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_award_widgets(nested)

        collect_award_widgets(contract["layoutContract"]["containerTree"])
        widget_statuses = {
            row["widgetId"]: row
            for row in contract["statusContract"]["widgetStatus"]
        }
        award_container_paths = []

        def collect_award_container_paths(value, path=()):
            if isinstance(value, dict):
                container_id = value.get("containerId")
                next_path = path + ((container_id,) if container_id else ())
                if value.get("fieldCode") == "award_opening_id":
                    award_container_paths.append(next_path)
                for nested in value.values():
                    collect_award_container_paths(nested, next_path)
            elif isinstance(value, list):
                for nested in value:
                    collect_award_container_paths(nested, path)

        collect_award_container_paths(contract["layoutContract"]["containerTree"])
        container_statuses = {
            row["containerId"]: row
            for row in contract["statusContract"].get("containerStatus", [])
        }
        self.assertTrue(award_container_paths, contract["layoutContract"]["containerTree"])
        for container_id in award_container_paths[0]:
            status = container_statuses.get(container_id)
            if status:
                self.assertIsNot(status.get("visible"), False, status)
        for field_name in (
            "award_opening_id",
            "award_source_kind",
            "award_source_reference",
            "award_source_attachment_id",
            "award_tax_basis",
        ):
            statuses = [
                widget_statuses[widget_id]
                for widget_id in award_widget_ids.get(field_name, [])
            ]
            self.assertTrue(statuses, (field_name, award_widget_ids))
            self.assertTrue(any(row.get("visible") is True for row in statuses), statuses)
            self.assertTrue(any(row.get("readonly") is False for row in statuses), statuses)
