# -*- coding: utf-8 -*-
"""Product-layer contract normalizers for the construction industry module.

This layer owns two facts and nothing else:

* *what a field means* for the fields it declares (``FIELD_SEMANTIC_DECLARATIONS``);
* *the delivery vocabulary* its control hands to the frontend
  (``SEMANTIC_PRESENTATION_VOCABULARY``).

It never names a component.  ``contracts/registry/semantic.yaml`` plus
``contracts/registry/component.yaml`` are the only place a semantic turns into a
component key, and the contract runtime resolves it, so a new business field
needs one declaration line here and no new mapping code on either side.  A
declared semantic the registry does not carry is refused and logged instead of
being rendered as something else (FE-CONTRACT-RUNTIME-01).

Both tables are keyed by *meaning*: this module cannot name a renderer even by
accident, which is what its previous model+field branch did with a literal
component key.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from typing import Any

from odoo.addons.smart_core.core.contract_runtime import semantic_resolver as _semantic_resolver
from odoo.addons.smart_construction_core import core_extension_contract_helpers as _contract_helpers

_sc_text = _contract_helpers.sc_text
_sc_collect_field_nodes = _contract_helpers.sc_collect_field_nodes
_sc_set_v2_container_tree = _contract_helpers.sc_set_v2_container_tree
_sc_set_v2_widget_status = _contract_helpers.sc_set_v2_widget_status
_sc_set_v2_governance_patch = _contract_helpers.sc_set_v2_governance_patch
_sc_replace_contract_content = _contract_helpers.sc_replace_contract_content
_sc_form_layout_governance = _contract_helpers.sc_form_layout_governance
_sc_apply_form_layout_governance_to_group = _contract_helpers.sc_apply_form_layout_governance_to_group

_logger = logging.getLogger(__name__)

# ``model -> field code -> declared semantic``.  The product layer declares the
# meaning of a field the registry's derivation rules cannot read from its type
# alone; the registry names the component that renders that meaning.
FIELD_SEMANTIC_DECLARATIONS: dict[str, dict[str, str]] = {
    "payment.request": {
        # "从结算单引入明细" and an amount bound to the detail sum are product
        # decisions about this collection, not something ``one2many`` implies.
        "outflow_line_ids": "payment_settlement_detail_collection",
    },
}

# ``semantic -> delivery vocabulary`` handed to that semantic's control.  Every
# word, payload key and server action identity the control uses is declared
# here; the frontend fails closed when one is missing instead of guessing.
SEMANTIC_PRESENTATION_VOCABULARY: dict[str, dict[str, Any]] = {
    "payment_settlement_detail_collection":     {
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
                },
}


def _declared_semantic(declarations: dict[str, str], field_code: str, widget_id: str) -> str:
    semantic = _sc_text(declarations.get(field_code))
    if semantic:
        return semantic
    if widget_id:
        for code, declared in declarations.items():
            if widget_id.startswith(f"field.{code}"):
                return _sc_text(declared)
    return ""


def _is_widget_node(node: dict[str, Any]) -> bool:
    """Whether the node is the shape ``$defs/widget`` describes.

    ``widgetType`` is required by that definition and absent from
    ``nativeLayoutNode``, so it is the discriminator the schema itself uses.
    """
    return bool(_sc_text(node.get("widgetType")))


def _apply_declared_semantic(node: dict[str, Any], semantic: str) -> str:
    """Declare the meaning on the field fact and let the registry name its component.

    Returns the component key the node now renders through (``""`` when the
    declaration was refused), so the caller publishes the identity the page
    actually uses.
    """
    component_key = _semantic_resolver.component_key_for_semantic(semantic)
    if not component_key:
        _logger.error(
            "contract_semantic_undeclared semantic=%s declared_by=%s; the field keeps the component "
            "its facts resolve to. Fix the declaration in contracts/registry/semantic.yaml.",
            semantic,
            _sc_text(node.get("fieldCode") or node.get("name") or node.get("field")) or "<unnamed field>",
        )
        return ""
    # The v2 schema lets a *widget* node carry a field descriptor and forbids it
    # on a native layout node, while the component identity is legal on both.  The
    # meaning is therefore written only on the node kind that can hold it: a
    # native layout node keeps the identity and nothing the schema rejects.
    if _is_widget_node(node):
        descriptor = node.get("fieldDescriptor") if isinstance(node.get("fieldDescriptor"), dict) else {}
        descriptor["semantic"] = semantic
        node["fieldDescriptor"] = descriptor
    node["componentKey"] = component_key
    vocabulary = SEMANTIC_PRESENTATION_VOCABULARY.get(semantic)
    if vocabulary:
        config = node.get("componentConfig") if isinstance(node.get("componentConfig"), dict) else {}
        config.update(deepcopy(vocabulary))
        node["componentConfig"] = config
    return component_key


def normalize_declared_field_presentation(
    contract: dict[str, Any],
    *,
    model: str,
    view_type: str,
) -> None:
    """Apply the product layer's declared field semantics to one contract.

    Generic by construction: the model only selects a declaration table and the
    component identity is resolved through the registry, so this function holds
    no model branch and no component key.
    """
    declarations = FIELD_SEMANTIC_DECLARATIONS.get(_sc_text(model))
    if not declarations or _sc_text(view_type) != "form":
        return
    layout = contract.get("layoutContract") if isinstance(contract.get("layoutContract"), dict) else {}
    tree = layout.get("containerTree") if isinstance(layout.get("containerTree"), list) else []
    resolved: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                visit(item)
            return
        if not isinstance(value, dict):
            return
        field_code = _sc_text(value.get("fieldCode") or value.get("name") or value.get("field"))
        semantic = _declared_semantic(declarations, field_code, _sc_text(value.get("widgetId")))
        if semantic:
            component_key = _apply_declared_semantic(value, semantic)
            if component_key:
                resolved.add(component_key)
        for key in ("children", "tabs", "pages", "nodes", "items", "widgetList"):
            visit(value.get(key))

    visit(tree)
    if not resolved:
        return
    registry = layout.get("componentRegistry") if isinstance(layout.get("componentRegistry"), dict) else {}
    registry.update(_semantic_resolver.component_registry(resolved))
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
            # The registry names the component for this field's facts.  The
            # previous literal was a key no carrier declared, so the frontend
            # fell back silently.
            "componentKey": _semantic_resolver.component_key("many2one", {"ttype": "many2one"}),
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


def restrict_plan_node_structure(data: dict[str, Any]) -> dict[str, Any]:
    """Restrict native relation capabilities from the hydrated parent facts."""
    record = data.get("record") if isinstance(data.get("record"), dict) else {}
    if not record.get("id"):
        return data
    allowed = record.get("state") == "draft" and record.get("validation_status") not in ("waiting", "pending", "validated")
    projected = deepcopy(data)

    def restrict(subview):
        if not isinstance(subview, dict):
            return
        policies = subview.get("policies")
        if not isinstance(policies, dict):
            return
        for key in ("can_create", "can_unlink"):
            policies[key] = policies.get(key) is True and allowed
        if not allowed:
            policies["reason_code"] = "PLAN_NODE_BASELINE_LOCKED"

    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if value.get("name") == "line_ids":
                restrict(value.get("subview"))
            if isinstance(value.get("line_ids"), dict):
                restrict(value["line_ids"])
                restrict(value["line_ids"].get("subview"))
            for item in value.values():
                visit(item)

    visit(projected)
    return projected
