# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy

from odoo import api, models


SETTLEMENT_ACTION_XMLIDS = (
    "smart_construction_core.action_sc_settlement_order_income",
    "smart_construction_core.action_sc_settlement_order_expense",
)

_SETTLEMENT_CANONICAL_FIELDS = {
    "document_state": ("state", "单据状态"),
    "document_no": ("name", "单据编号"),
    "project_name": ("project_id", "项目名称"),
    "document_date": ("document_date", "单据日期"),
    "title": ("title", "标题/结算内容"),
    "partner_name": ("settlement_unit_id", "结算单位"),
    "amount": ("settlement_amount", "结算金额"),
    "paid_amount": ("paid_amount", "已付款金额"),
    "unpaid_amount": ("unpaid_amount", "未付款金额"),
    "requested_amount": ("requested_fund_amount", "申请资金金额"),
    "unrequested_amount": ("remaining_amount", "可付余额"),
    "note": ("note", "备注"),
    "attachment": ("attachment_ids", "附件"),
    "creator": ("entry_user_id", "录入人"),
    "created_at": ("create_date", "录入时间"),
}
SETTLEMENT_ACCEPTANCE_FIELD_MAP = {
    f"{prefix}{suffix}": target
    for prefix in ("user_acceptance_", "settlement_acceptance_")
    for suffix, target in _SETTLEMENT_CANONICAL_FIELDS.items()
}


class UIBusinessConfigContractSettlementFormalSync(models.Model):
    _inherit = "ui.business.config.contract"

    @api.model
    def sc_sync_settlement_formal_list_contracts(self):
        Contract = self.sudo()
        changed = 0
        for action_xmlid in SETTLEMENT_ACTION_XMLIDS:
            action = self.env.ref(action_xmlid, raise_if_not_found=False)
            if not action:
                continue
            contracts = Contract.search(
                [
                    ("model", "=", "sc.settlement.order"),
                    ("action_id", "=", action.id),
                    ("status", "=", "published"),
                    ("view_type", "in", ["tree", "list"]),
                ],
                order="id",
            )
            for contract in contracts:
                payload = deepcopy(contract.contract_json or {})
                if not isinstance(payload, dict):
                    continue
                next_payload = self._sc_settlement_formalize_contract_payload(payload)
                if next_payload == payload:
                    continue
                contract.replace_and_publish(next_payload)
                changed += 1
        return changed

    @api.model
    def _sc_settlement_formalize_contract_payload(self, payload):
        def replace_value(value):
            mapped = SETTLEMENT_ACCEPTANCE_FIELD_MAP.get(str(value or "").strip())
            return mapped[0] if mapped else value

        def replace_label(field_name, label):
            for _legacy, (formal_name, formal_label) in SETTLEMENT_ACCEPTANCE_FIELD_MAP.items():
                if field_name == formal_name:
                    return formal_label
            return label

        def visit(value):
            if isinstance(value, list):
                return [visit(item) for item in value]
            if isinstance(value, dict):
                row = {key: visit(item) for key, item in value.items()}
                for key in ("name", "field", "field_name"):
                    if key in row:
                        row[key] = replace_value(row[key])
                field_name = str(row.get("name") or row.get("field") or row.get("field_name") or "").strip()
                if field_name:
                    if "label" in row:
                        row["label"] = replace_label(field_name, row.get("label"))
                    if "string" in row:
                        row["string"] = replace_label(field_name, row.get("string"))
                return row
            if isinstance(value, str):
                return replace_value(value)
            return value

        next_payload = visit(payload)
        if not isinstance(next_payload, dict):
            return payload
        orchestration = next_payload.get("view_orchestration")
        if isinstance(orchestration, dict):
            context = dict(orchestration.get("context") or {})
            context["source"] = "smart_construction_core.formal_settlement_list_contract_sync"
            orchestration["context"] = context
        return next_payload
