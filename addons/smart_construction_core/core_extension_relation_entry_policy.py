# -*- coding: utf-8 -*-
from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def _sc_text(value) -> str:
    return str(value or "").strip()


def smart_core_relation_entry_policy(env, payload):
    payload = payload if isinstance(payload, dict) else {}
    model = _sc_text(payload.get("model"))
    field_name = _sc_text(payload.get("field_name"))
    relation = _sc_text(payload.get("relation"))
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    record = payload.get("record") if isinstance(payload.get("record"), dict) else {}
    if relation == "account.tax" and field_name == "tax_id" and model in {"construction.contract", "sc.general.contract"}:
        default_vals = {
            "type_tax_use": "none",
            "amount_type": "percent",
            "price_include": False,
        }
        try:
            company = env.company
            helper = env["construction.contract"].sudo().with_company(company)
            group = helper._sc_contract_tax_group(company)
            country = company.account_fiscal_country_id or company.partner_id.country_id or env.ref(
                "base.cn",
                raise_if_not_found=False,
            )
            default_vals.update({
                "company_id": company.id,
                "tax_group_id": group.id,
            })
            if country:
                default_vals["country_id"] = country.id
        except Exception:
            _logger.debug("Unable to resolve contract tax quick-create defaults.", exc_info=True)
        return {
            "has_page": False,
            "can_open": False,
            "can_create": True,
            "quick_create": True,
            "display_field": "name",
            "order": "amount asc, id asc",
            "default_vals": default_vals,
            "domain": [
                ["type_tax_use", "=", "none"],
                ["amount_type", "=", "percent"],
                ["price_include", "=", False],
            ],
            "ui_labels": {
                "quick_create": "新增税率...",
                "create_and_edit": "新增税率...",
                "missing_name": "请输入税率百分比，例如：3%、9%、13%",
                "quick_create_prompt": "请输入税率百分比，例如：3%、9%、13%",
                "quick_create_failed": "新增税率失败，请输入 0 到 100 之间的百分比",
                "inline_create": "新增税率“%s”",
                "inline_create_failed": "创建税率失败，请检查百分比格式",
            },
        }
    if relation == "res.partner" and model == "sc.self.funding.registration" and field_name == "partner_id":
        category_code = _sc_text(context.get("current_business_category_code") or context.get("default_business_category_code"))
        if category_code == "finance.self_funding.refund":
            contractor_ids = []
            try:
                summaries = env["sc.company.contractor.responsibility.summary"].sudo().search([
                    ("partner_id", "!=", False),
                    ("self_funding_balance", ">", 0.01),
                ])
                partners = summaries.mapped("partner_id").filtered(
                    lambda partner: partner.supplier_rank > 0 or partner.customer_rank > 0
                )
                contractor_ids = sorted(set(partners.ids))
            except Exception:
                contractor_ids = []
            return {
                "has_page": False,
                "can_create": False,
                "display_field": "display_name",
                "order": "name asc, id asc",
                "domain": [["id", "in", contractor_ids or [0]]],
                "ui_labels": {
                    "search_more": "搜索承包人...",
                    "dialog_title": "承包人：搜索更多",
                    "search_placeholder": "输入承包人名称搜索",
                    "create_and_edit": "",
                    "quick_create": "",
                },
            }
    if relation == "res.partner" and model == "sc.expense.claim" and field_name == "partner_id":
        category_code = _sc_text(context.get("current_business_category_code") or context.get("default_business_category_code"))
        if category_code == "finance.deduction.bill":
            partner_ids = []
            try:
                summaries = env["sc.company.contractor.responsibility.summary"].sudo().search([("partner_id", "!=", False)])
                partners = summaries.mapped("partner_id").filtered(
                    lambda partner: partner.supplier_rank > 0 or partner.customer_rank > 0
                )
                partner_ids = sorted(set(partners.ids))
            except Exception:
                partner_ids = []
            return {
                "has_page": False,
                "can_create": False,
                "display_field": "display_name",
                "order": "name asc, id asc",
                "domain": [["id", "in", partner_ids or [0]]],
                "ui_labels": {
                    "search_more": "搜索责任方...",
                    "dialog_title": "责任方：搜索更多",
                    "search_placeholder": "输入责任方名称搜索",
                    "create_and_edit": "",
                    "quick_create": "",
                },
            }
    if relation == "construction.contract" and model == "construction.contract" and field_name == "original_contract_id":
        category_code = _sc_text(context.get("current_business_category_code") or context.get("default_business_category_code"))
        contract_type = _sc_text(context.get("default_type") or context.get("type") or record.get("type"))
        domain = []
        if category_code == "contract.income.supplement":
            domain = [["type", "=", "out"]]
        elif category_code == "contract.expense.supplement":
            domain = [["type", "=", "in"]]
        elif contract_type in {"out", "in"}:
            domain = [["type", "=", contract_type]]
        if not domain:
            return None
        return {
            "has_page": False,
            "can_open": False,
            "can_create": False,
            "create_mode": "disabled",
            "display_field": "display_name",
            "order": "id desc",
            "domain": domain,
            "ui_labels": {
                "search_more": "搜索原合同...",
                "dialog_title": "原合同：搜索更多",
                "search_placeholder": "输入原合同名称、编号、项目或往来单位搜索",
                "create_and_edit": "",
                "quick_create": "",
            },
        }
    return None
