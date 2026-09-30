# -*- coding: utf-8 -*-
from __future__ import annotations

from copy import deepcopy
from typing import Any

from odoo.addons.smart_construction_core import core_extension_contract_helpers as _contract_helpers

_sc_text = _contract_helpers.sc_text
_sc_collect_field_nodes = _contract_helpers.sc_collect_field_nodes
_sc_set_v2_container_tree = _contract_helpers.sc_set_v2_container_tree
_sc_set_v2_widget_status = _contract_helpers.sc_set_v2_widget_status
_sc_set_v2_governance_patch = _contract_helpers.sc_set_v2_governance_patch
_sc_replace_contract_content = _contract_helpers.sc_replace_contract_content
_sc_form_layout_governance = _contract_helpers.sc_form_layout_governance
_sc_apply_form_layout_governance_to_group = _contract_helpers.sc_apply_form_layout_governance_to_group

PAYMENT_SETTLEMENT_DETAIL_COMPONENT_KEY = "sc.payment.settlement_detail_collection"


def normalize_payment_settlement_detail_component(
    contract: dict[str, Any],
    *,
    model: str,
    view_type: str,
) -> None:
    if model != "payment.request" or view_type != "form":
        return
    layout = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    tree = layout.get("containerTree") if isinstance(layout.get("containerTree"), list) else []
    changed = False

    def visit(value: Any) -> None:
        nonlocal changed
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        field_code = _sc_text(value.get("fieldCode") or value.get("name") or value.get("field"))
        widget_id = _sc_text(value.get("widgetId"))
        if field_code == "outflow_line_ids" or widget_id.startswith("field.outflow_line_ids"):
            value["componentKey"] = PAYMENT_SETTLEMENT_DETAIL_COMPONENT_KEY
            config = value.get("componentConfig") if isinstance(value.get("componentConfig"), dict) else {}
            config.update({
                "fieldType": "one2many",
                "introduceLabel": "从结算单引入",
                "optionalDetails": {
                    "entryLabel": "按明细填写",
                    "populatedLabel": "付款申请明细",
                    "directAmountMessage": "可直接填写申请金额；添加有效明细后，申请金额按明细合计生成。",
                    "linkedAmountMessage": "申请金额由有效明细的“本次申请”合计生成。",
                    "lastRowRemovalActionLabel": "取消按明细填写",
                    "lastRowRemovalMessage": (
                        "删除最后一条明细后将切回直接填写申请金额；"
                        "最后一次明细合计会保留在申请金额中，请确认后继续。"
                    ),
                },
                "amountBinding": {
                    "mode": "sum_when_nonempty",
                    "sourceField": "current_pay_amount",
                    "targetField": "amount",
                    "activeField": "active",
                    "stateField": "amount_uses_details",
                    "rounding": "currency",
                    "emptyBehavior": "preserve_last_total",
                },
                "actionRefs": {
                    "search": "payment.request.settlement.search",
                    "preview": "payment.request.settlement.preview",
                    "introduce": "payment.request.add.settlement.lines",
                },
                "introduceDialog": {
                    "purpose": "payment-settlement-introduce",
                    "title": "从结算单引入明细",
                    "description": "选择结算单，勾选结算行并设置申请金额，确认后引入为付款申请明细",
                    "searchPlaceholder": "搜索结算单号 / 名称",
                    "searchActionLabel": "搜索",
                    "searchLoadingLabel": "正在搜索结算单",
                    "searchEmptyLabel": "未找到结算单，请输入关键词搜索",
                    "resultContractLabel": "合同",
                    "resultAmountLabel": "金额",
                    "resultLineCountLabel": "明细",
                    "resultLineCountSuffix": "行",
                    "switchSourceLabel": "换一个结算单",
                    "selectAllLabel": "全选未完全申请的行",
                    "summarySelectedPrefix": "选中",
                    "summaryLineCountSuffix": "行",
                    "summarySettlementAmountLabel": "结算金额",
                    "summaryApplicableAmountLabel": "可申请",
                    "columnLabels": {
                        "name": "名称",
                        "contract": "合同",
                        "settlementAmount": "结算金额",
                        "applied": "已申请",
                        "remaining": "可申请",
                        "state": "状态",
                    },
                    "stateAppliedLabel": "已申请完",
                    "stateApplicableLabel": "可申请",
                    "allAppliedLabel": "该结算单所有明细均已申请完毕",
                    "historyTitle": "历史申请记录",
                    "historyCountSuffix": "笔",
                    "historyExpandLabel": "展开",
                    "historyCollapseLabel": "收起",
                    "ratioModeLabel": "按比例",
                    "amountModeLabel": "按总金额",
                    "ratioPlaceholder": "申请比例 %",
                    "totalPlaceholder": "总申请金额",
                    "ratioHint": "每行申请 = 可申请 * 比例",
                    "amountHint": "按各结算行可申请占比分配",
                    "applyTotalLabel": "本次申请合计",
                    "cancelLabel": "取消",
                    "confirmLabel": "确认引入",
                    "recordRequiredMessage": "请先保存付款申请后再引入明细",
                    "payloadFields": {
                        "record": "payment_request_id",
                        "source": "settlement_id",
                        "sourceLines": "settlement_line_ids",
                        "applyMode": "apply_mode",
                        "ratio": "ratio",
                        "totalAmount": "total_amount",
                        "searchKeyword": "keyword",
                    },
                },
            })
            value["componentConfig"] = config
            changed = True
        for key in ("children", "tabs", "pages", "nodes", "items", "widgetList"):
            visit(value.get(key))

    visit(tree)
    if not changed:
        return
    registry = layout.get("componentRegistry") if isinstance(layout.get("componentRegistry"), dict) else {}
    registry[PAYMENT_SETTLEMENT_DETAIL_COMPONENT_KEY] = {
        "version": "1.0",
        "adapter": {
            "web_pc": "PaymentSettlementDetailCollectionControl",
            "wx_mini": "WxTable",
            "harmony_h5": "H5Table",
        },
        "fallback": "PaymentSettlementDetailCollectionControl",
    }
    layout["componentRegistry"] = registry
    contract["layoutContract"] = layout

def general_contract_tax_contract(contract: dict[str, Any], source_contract: dict[str, Any] | None = None) -> None:
    if not isinstance(contract, dict):
        return
    model = _sc_text(
        contract.get("model")
        or (source_contract or {}).get("model")
        or ((contract.get("head") or {}).get("model") if isinstance(contract.get("head"), dict) else "")
    )
    field_map = contract.get("fields") if isinstance(contract.get("fields"), dict) else {}
    source_fields = (source_contract or {}).get("fields") if isinstance((source_contract or {}).get("fields"), dict) else {}
    if model != "sc.general.contract" or ("tax_id" not in field_map and "tax_id" not in source_fields):
        return

    def is_tax_rate_node(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        name = _sc_text(value.get("name") or value.get("field") or value.get("fieldCode"))
        widget_id = _sc_text(value.get("widgetId") or value.get("id"))
        return name == "tax_rate" or widget_id == "field.tax_rate"

    def is_tax_id_node(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        name = _sc_text(value.get("name") or value.get("field") or value.get("fieldCode"))
        widget_id = _sc_text(value.get("widgetId") or value.get("id"))
        return name == "tax_id" or widget_id == "field.tax_id"

    tax_field = field_map.get("tax_id") if isinstance(field_map.get("tax_id"), dict) else {}
    if not tax_field and isinstance(source_fields.get("tax_id"), dict):
        tax_field = source_fields.get("tax_id") or {}

    def tax_id_field_node(source_node: dict[str, Any]) -> dict[str, Any]:
        role = source_node.get("formStructureRole") if isinstance(source_node.get("formStructureRole"), dict) else {
            "role": "amount",
            "slot": "amount_progress",
            "group": "amounts",
        }
        descriptor = dict(tax_field or {})
        descriptor.update({"name": "tax_id", "label": "税率", "string": "税率", "type": "many2one", "widget": "many2one"})
        return {
            "type": "field",
            "name": "tax_id",
            "formStructureRole": role,
            "string": "税率",
            "label": "税率",
            "fieldInfo": descriptor,
            "widget": "many2one",
            "componentKey": "sc.input.many2one",
            "componentConfig": {"readonly": False, "required": False, "fieldType": "many2one"},
            "widgetId": "field.tax_id",
            "field_info": descriptor,
            "children": [],
            "widgetList": [],
        }

    def is_form_field_node(value: dict[str, Any]) -> bool:
        return _sc_text(value.get("type")) == "field" or isinstance(value.get("fieldInfo"), dict) or isinstance(value.get("field_info"), dict)

    def clean(value: Any):
        if isinstance(value, list):
            return [item for item in (clean(item) for item in value) if item is not None]
        if isinstance(value, dict):
            if is_tax_rate_node(value):
                return tax_id_field_node(value) if is_form_field_node(value) else None
            copied = {}
            for key, item in value.items():
                if key == "tax_rate":
                    continue
                copied[key] = clean(item)
            return copied
        return value

    cleaned = clean(contract)
    if isinstance(cleaned, dict):
        _sc_replace_contract_content(contract, cleaned)

    status_contract = contract.get("statusContract") if isinstance(contract.get("statusContract"), dict) else {}
    widget_status = status_contract.get("widgetStatus") if isinstance(status_contract.get("widgetStatus"), list) else []
    tax_status_rows = [
        row for row in widget_status
        if isinstance(row, dict) and _sc_text(row.get("widgetId")) == "field.tax_id"
    ]
    if not tax_status_rows:
        tax_status_rows = [{"widgetId": "field.tax_id", "visible": True, "readonly": False, "required": False, "disabled": False, "auth": "edit"}]
        widget_status.extend(tax_status_rows)
    for row in tax_status_rows:
        row["visible"] = True
        row["readonly"] = False
        row["disabled"] = False
        row["auth"] = "edit"
    if widget_status:
        _sc_set_v2_widget_status(contract, [
            row for row in widget_status
            if not (isinstance(row, dict) and _sc_text(row.get("widgetId")) == "field.tax_rate")
        ])

    def has_tax_id_layout_node(value: Any) -> bool:
        if is_tax_id_node(value) and (_sc_text((value or {}).get("type")) == "field" or isinstance((value or {}).get("fieldInfo"), dict) or isinstance((value or {}).get("field_info"), dict)):
            return True
        if isinstance(value, list):
            return any(has_tax_id_layout_node(item) for item in value)
        if isinstance(value, dict):
            return any(has_tax_id_layout_node(item) for item in value.values())
        return False

    if has_tax_id_layout_node(contract):
        return
    layout_contract = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    container_tree = layout_contract.get("containerTree") if isinstance(layout_contract.get("containerTree"), list) else []
    if not container_tree:
        return
    target_field_names = {"contract_amount", "amount_total", "amount_untaxed", "settlement_amount"}

    def append_after_amount_node(rows: list[Any]) -> bool:
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            name = _sc_text(row.get("name") or row.get("field") or row.get("fieldCode"))
            widget_id = _sc_text(row.get("widgetId"))
            if name in target_field_names or widget_id in {f"field.{name}" for name in target_field_names}:
                rows.insert(index + 1, tax_id_field_node(row))
                return True
            for key in ("children", "pages", "tabs", "nodes", "items", "widgetList"):
                children = row.get(key)
                if isinstance(children, list) and append_after_amount_node(children):
                    return True
        return False

    if append_after_amount_node(container_tree):
        _sc_set_v2_container_tree(contract, container_tree)

def model_specific_form_contract_policy(payload: dict[str, Any] | None) -> dict[str, list[str]] | None:
    safe_payload = payload if isinstance(payload, dict) else {}
    model = _sc_text(safe_payload.get("model"))
    fields_map = safe_payload.get("fields") if isinstance(safe_payload.get("fields"), dict) else {}
    if model == "sc.general.contract" and "tax_id" in fields_map and "tax_rate" in fields_map:
        return {"remove_fields": ["tax_rate"]}
    return None

def form_field_aliases(payload: dict[str, Any] | None) -> dict[str, str] | None:
    safe_payload = payload if isinstance(payload, dict) else {}
    model = _sc_text(safe_payload.get("model"))
    source = safe_payload.get("source_contract") if isinstance(safe_payload.get("source_contract"), dict) else {}
    fields_map = source.get("fields") if isinstance(source.get("fields"), dict) else {}
    if model == "sc.general.contract" and "tax_id" in fields_map:
        return {"tax_rate": "tax_id"}
    return None
