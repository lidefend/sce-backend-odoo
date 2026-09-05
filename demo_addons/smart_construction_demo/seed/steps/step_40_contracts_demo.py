# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare

from ..registry import SeedStep, register
from ..tier_flow import approve_tier_chain


PROJECT_EXEC_CODE = "DEMO-PJ-EXEC"
STAGE_PROJECT_CODES = [
    "DEMO-PJ-STAGE-DRAFT",
    "DEMO-PJ-STAGE-RUN",
    "DEMO-PJ-STAGE-PAUSE",
    "DEMO-PJ-STAGE-CLOSING",
    "DEMO-PJ-STAGE-DONE",
    "DEMO-PJ-STAGE-WARRANTY",
    "DEMO-PJ-STAGE-CLOSED",
]
DEMO_INVOICE_RATIO_BY_STATE = {
    "draft": 0.0,
    "in_progress": 0.7,
    "paused": 0.7,
    "closing": 0.95,
    "done": 1.0,
    "warranty": 1.0,
    "closed": 1.0,
}
DEMO_INVOICE_WARN_RATIO_BY_STATE = {
    "draft": 0.0,
    "in_progress": 0.5,
    "paused": 0.5,
    "closing": 0.8,
    "done": 0.9,
    "warranty": 0.9,
    "closed": 0.9,
}
DEMO_WARN_PROJECT_CODES = {
    "DEMO-PJ-INIT",
    "DEMO-PJ-TENDER",
}
DEMO_FUNDING_AMOUNT = 2000000.0


def _annual_control_period(env):
    today = fields.Date.context_today(env.user)
    return today.replace(month=1, day=1), today.replace(month=12, day=31)


def _ensure_funding_baseline(env, project):
    Funding = env["project.funding.baseline"].sudo()
    project.sudo().write({"funding_enabled": True})
    if not project.company_id:
        # Defensive: projects created with a name-only payload (showroom
        # style) carry no company because project.company_id is a stored
        # compute without a default; the standard funding baseline requires
        # an explicit company/currency owner.
        company = env.company or env["res.company"].sudo().search([], limit=1)
        project.sudo().write({"company_id": company.id})
    baseline = Funding.search(
        [("project_id", "=", project.id), ("state", "=", "active")], limit=1
    )
    if baseline:
        rounding = baseline.currency_id.rounding or 0.01
        if not float_compare(
            baseline.total_amount, DEMO_FUNDING_AMOUNT, precision_rounding=rounding
        ):
            return baseline
        period_start, period_end = _annual_control_period(env)
        revision = baseline.action_create_revision(
            "演示事实基线修订",
            period_start=period_start,
            period_end=period_end,
        )
        if revision.state != "draft":
            raise UserError("演示资金基线修订必须保持草稿后再生效。")
        revision.write(
            {
                "total_amount": DEMO_FUNDING_AMOUNT,
                "line_ids": [
                    (5, 0, 0),
                    (
                        0,
                        0,
                        {
                            "sequence": 10,
                            "name": "演示年度资金计划",
                            "planned_amount": DEMO_FUNDING_AMOUNT,
                        },
                    ),
                ],
            }
        )
        revision.action_activate()
        return revision
    period_start, period_end = _annual_control_period(env)
    baseline = Funding.create(
        {
            "project_id": project.id,
            "total_amount": DEMO_FUNDING_AMOUNT,
            "period_start": period_start,
            "period_end": period_end,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "sequence": 10,
                        "name": "演示年度资金计划",
                        "planned_amount": DEMO_FUNDING_AMOUNT,
                    },
                )
            ],
        }
    )
    baseline.action_activate()
    return baseline


def _ensure_settlement(env, project, contract):
    Settlement = env["sc.settlement.order"].sudo()
    Line = env["sc.settlement.order.line"].sudo()
    settlement = Settlement.search(
        [
            ("project_id", "=", project.id),
            ("contract_id", "=", contract.id),
            ("state", "!=", "cancel"),
        ],
        limit=1,
    )
    vals = {
        "name": f"SET-{project.project_code}-01",
        "project_id": project.id,
        "contract_id": contract.id,
        "partner_id": contract.partner_id.id,
        "settlement_type": "out" if contract.type == "in" else "in",
        "date_settlement": fields.Date.context_today(env.user),
    }
    if settlement:
        if settlement.state == "draft":
            settlement.write(vals)
    else:
        settlement = Settlement.create(vals)

    line_vals = [
        {"settlement_id": settlement.id, "name": "结算项A", "qty": 1, "price_unit": 260000.0},
        {"settlement_id": settlement.id, "name": "结算项B", "qty": 1, "price_unit": 140000.0},
    ]
    if settlement.state == "draft":
        for vals in line_vals:
            existing = Line.search(
                [("settlement_id", "=", settlement.id), ("name", "=", vals["name"])],
                limit=1,
            )
            if existing:
                existing.write(vals)
            else:
                Line.create(vals)
    elif not settlement.line_ids:
        raise UserError("已进入流程的演示结算单缺少不可变结算明细。")
    return settlement


def _approve_settlement(env, settlement):
    if settlement.state == "draft":
        settlement.action_submit()
    if settlement.state == "submit":
        if approve_tier_chain(settlement) and settlement.state == "submit":
            settlement.action_on_tier_approved()
    if settlement.state not in ("approve", "done"):
        raise UserError("演示结算单未能通过正式审批状态机。")
    return settlement


def _ensure_purchase_order(env, settlement, split_first_line=False):
    Purchase = env["purchase.order"].sudo()
    PurchaseLine = env["purchase.order.line"].sudo()
    Product = env["product.product"].sudo()
    uom_unit = env.ref("uom.product_uom_unit", raise_if_not_found=False)
    if not uom_unit:
        uom_unit = env["uom.uom"].sudo().search([], limit=1)

    product = Product.search([("name", "=", "演示采购服务")], limit=1)
    if not product:
        product = Product.create(
            {
                "name": "演示采购服务",
                "type": "service",
                "uom_id": uom_unit.id if uom_unit else False,
                "uom_po_id": uom_unit.id if uom_unit else False,
                "purchase_ok": True,
                "sale_ok": False,
            }
        )

    po = Purchase.search(
        [
            ("partner_id", "=", settlement.partner_id.id),
            ("origin", "=", settlement.name),
        ],
        limit=1,
    )
    if not po:
        po = Purchase.create(
            {
                "partner_id": settlement.partner_id.id,
                "date_order": fields.Datetime.now(),
                "origin": settlement.name,
            }
        )

    total = settlement.amount_total or sum(settlement.line_ids.mapped("amount")) or 0.0
    desired_lines = []
    settlement_lines = settlement.line_ids
    if not settlement_lines:
        desired_lines.append(
            {
                "name": "演示采购行",
                "amount": total,
                "split": False,
            }
        )
    else:
        for idx, sline in enumerate(settlement_lines):
            amount = sline.amount or 0.0
            if split_first_line and idx == 0:
                desired_lines.append(
                    {
                        "name": f"{sline.name}-批次1",
                        "amount": round(amount * 0.6, 2),
                        "split": True,
                    }
                )
                desired_lines.append(
                    {
                        "name": f"{sline.name}-批次2",
                        "amount": amount - round(amount * 0.6, 2),
                        "split": True,
                    }
                )
            else:
                desired_lines.append(
                    {
                        "name": sline.name,
                        "amount": amount,
                        "split": False,
                    }
                )
    desired_by_name = {spec["name"]: spec for spec in desired_lines}
    current_lines = PurchaseLine.search([("order_id", "=", po.id)])
    current_amounts = {
        line.name: (line.product_qty or 0.0) * (line.price_unit or 0.0)
        for line in current_lines
    }
    rounding = settlement.currency_id.rounding or 0.01
    lines_match = set(current_amounts) == set(desired_by_name) and all(
        not float_compare(
            current_amounts[name], desired_by_name[name]["amount"], precision_rounding=rounding
        )
        for name in desired_by_name
    )
    if settlement.state != "draft":
        if po not in settlement.purchase_order_ids or po.state not in ("purchase", "done"):
            raise UserError("已审批演示结算单缺少不可变采购依据。")
        if not lines_match:
            raise UserError("已审批演示结算单的采购依据金额与结算事实不一致。")
        return po
    if po.state != "draft":
        if not lines_match:
            raise UserError("已确认采购单与待提交演示结算事实不一致，禁止回退改写。")
        settlement.write({"purchase_order_ids": [(4, po.id)]})
        return po

    for spec in desired_lines:
        line_vals = {
            "order_id": po.id,
            "name": spec["name"],
            "product_id": product.id,
            "product_qty": 1.0,
            "product_uom": uom_unit.id if uom_unit else product.uom_po_id.id,
            "price_unit": spec["amount"],
            "date_planned": fields.Datetime.now(),
        }
        existing = PurchaseLine.search(
            [("order_id", "=", po.id), ("name", "=", spec["name"])], limit=1
        )
        if existing:
            existing.write(line_vals)
        else:
            PurchaseLine.create(line_vals)

    desired_names = {spec["name"] for spec in desired_lines}
    stale_lines = PurchaseLine.search([("order_id", "=", po.id), ("name", "not in", list(desired_names))])
    if stale_lines:
        stale_lines.unlink()

    po.button_confirm()
    po.invalidate_recordset()
    if po.state in ("draft", "sent"):
        # An active approval policy routes the purchase confirmation through
        # the unified tier validation chain (button_confirm only submits the
        # reviews; the one2many cache is stale until invalidated). Complete
        # the chain with per-review actors so the settlement approval finds
        # a confirmed purchase order.
        approve_tier_chain(
            po,
            fallback_xmlid="smart_construction_demo.user_sc_purchase_manager_cap",
        )
    if po.state in ("draft", "sent") and po.validation_status == "validated":
        # Defensive: the final tier level normally fires the server action
        # callback that confirms the order; finish it directly if not.
        po.button_confirm()
    settlement.write({"purchase_order_ids": [(4, po.id)]})
    return po


def _ensure_invoice_info(env, settlement, ratio):
    total = settlement.amount_total or sum(settlement.line_ids.mapped("amount")) or 0.0
    invoice_amount = round(total * ratio, 2)
    if settlement.state != "draft":
        rounding = settlement.currency_id.rounding or 0.01
        if (
            not settlement.invoice_ref
            or not settlement.invoice_date
            or float_compare(
                settlement.invoice_amount or 0.0,
                invoice_amount,
                precision_rounding=rounding,
            )
        ):
            raise UserError("已审批演示结算单的发票快照与标准样本不一致。")
        return
    settlement.write(
        {
            "invoice_ref": settlement.invoice_ref or f"INV-{settlement.name}",
            "invoice_amount": invoice_amount,
            "invoice_date": fields.Date.context_today(env.user),
        }
    )


def _approve_payment(env, payment):
    if payment.state in ("approved", "done"):
        return payment
    if payment.state in ("draft", "rejected"):
        payment.action_submit()
    if payment.state == "submit":
        if approve_tier_chain(
            payment,
            fallback_xmlid="smart_construction_demo.user_sc_finance_mgr_test",
        ) and payment.state == "submit":
            payment.action_on_tier_approved()
    if payment.state == "approve" and payment.validation_status == "validated":
        payment.action_set_approved()
    if payment.state != "approved":
        raise UserError("演示付款申请未能通过正式审批状态机。")
    return payment


def _ensure_payments(env, project, pay_contract, receive_contract, settlement):
    Payment = env["payment.request"].sudo()
    pay = Payment.search(
        [
            ("project_id", "=", project.id),
            ("type", "=", "pay"),
            ("contract_id", "=", pay_contract.id),
            ("state", "!=", "cancel"),
        ],
        limit=1,
    )
    pay_vals = {
        "type": "pay",
        "project_id": project.id,
        "partner_id": pay_contract.partner_id.id,
        "contract_id": pay_contract.id,
        "settlement_id": settlement.id,
        "amount": 160000.0,
    }
    if not pay:
        pay = Payment.create(pay_vals)
    elif pay.state in ("draft", "rejected"):
        pay.write(pay_vals)
    receive = Payment.search(
        [
            ("project_id", "=", project.id),
            ("type", "=", "receive"),
            ("contract_id", "=", receive_contract.id),
            ("state", "!=", "cancel"),
        ],
        limit=1,
    )
    receive_vals = {
        "type": "receive",
        "project_id": project.id,
        "partner_id": receive_contract.partner_id.id,
        "contract_id": receive_contract.id,
        "amount": 120000.0,
    }
    if not receive:
        receive = Payment.create(receive_vals)
    elif receive.state in ("draft", "rejected"):
        receive.write(receive_vals)

    _approve_payment(env, pay)
    _approve_payment(env, receive)


def _cleanup_paused_showroom_settlement(env, project):
    Settlement = env["sc.settlement.order"].sudo()
    Payment = env["payment.request"].sudo()

    settlements = Settlement.search(
        [
            ("project_id", "=", project.id),
            ("name", "=", f"SET-{project.project_code}-01"),
        ]
    )
    if not settlements:
        return

    payments = Payment.search(
        [
            ("project_id", "=", project.id),
            ("settlement_id", "in", settlements.ids),
        ]
    )
    removable_payments = payments.filtered(lambda record: record.state in ("draft", "cancel"))
    if removable_payments:
        removable_payments.unlink()
    removable_settlements = settlements.filtered(lambda record: record.state == "draft")
    if removable_settlements:
        removable_settlements.mapped("line_ids").unlink()
        removable_settlements.unlink()


def _get_project(env, code):
    return env["project.project"].sudo().search([("project_code", "=", code)], limit=1)


def _get_showroom_projects(env):
    Project = env["project.project"].sudo()
    domain = [
        "|",
        "|",
        ("name", "ilike", "展厅-"),
        ("name", "ilike", "演示项目"),
        ("project_code", "ilike", "DEMO-"),
    ]
    return Project.search(domain)


def _get_or_create_partner(env, name):
    Partner = env["res.partner"].sudo()
    partner = Partner.search([("name", "=", name)], limit=1)
    if partner:
        if partner.company_type != "company":
            partner.company_type = "company"
        return partner
    return Partner.create({"name": name, "company_type": "company"})


def _get_dictionary(env, xmlid, domain):
    rec = env.ref(xmlid, raise_if_not_found=False)
    if rec:
        return rec
    return env["sc.dictionary"].sudo().search(domain, limit=1)


def _ensure_contract(env, vals):
    Contract = env["construction.contract"].sudo()
    contract = Contract.search(
        [("project_id", "=", vals["project_id"]), ("subject", "=", vals["subject"])], limit=1
    )
    if contract:
        contract.write(vals)
    else:
        contract = Contract.create(vals)
    return contract


def _ensure_tender(env, project, owner):
    Tender = env["tender.bid"].sudo()
    TenderLine = env["tender.bid.line"].sudo()
    uom_unit = env.ref("uom.product_uom_unit", raise_if_not_found=False)
    if not uom_unit:
        uom_unit = env["uom.uom"].sudo().search([], limit=1)

    bid_name = f"TB-{project.project_code or project.id}-01"
    tender = Tender.search([("project_id", "=", project.id), ("name", "=", bid_name)], limit=1)
    vals = {
        "name": bid_name,
        "tender_name": f"{project.name} 投标",
        "project_id": project.id,
        "tender_round": 1,
        "owner_id": owner.id if owner else False,
        "bid_amount": 680000.0,
        "deadline": fields.Datetime.now(),
        "open_date": fields.Datetime.now(),
        "state": "prepare",
    }
    if tender:
        tender.write(vals)
    else:
        tender = Tender.create(vals)

    line_vals = {
        "bid_id": tender.id,
        "sequence": 10,
        "code": f"{project.project_code or project.id}-BID-01",
        "name": "投标清单项",
        "uom_id": uom_unit.id if uom_unit else False,
        "quantity": 80,
        "price": 1200,
    }
    line = TenderLine.search([("bid_id", "=", tender.id), ("code", "=", line_vals["code"])], limit=1)
    if line:
        line.write(line_vals)
    else:
        TenderLine.create(line_vals)


def run(env):
    projects = [
        _get_project(env, PROJECT_EXEC_CODE),
    ]
    for code in STAGE_PROJECT_CODES:
        projects.append(_get_project(env, code))
    projects.extend(_get_showroom_projects(env))
    projects = list({p.id: p for p in projects if p}.values())

    owner = _get_or_create_partner(env, "演示业主 · 城市建设集团")
    subcontract = _get_or_create_partner(env, "演示分包 · 桥梁施工队")

    contract_category = _get_dictionary(
        env,
        "smart_construction_seed.seed_dict_contract_category_build",
        [("type", "=", "contract_category")],
    )
    contract_type_out = _get_dictionary(
        env,
        "smart_construction_seed.seed_dict_contract_type_out",
        [("type", "=", "contract_type")],
    )
    contract_type_in = _get_dictionary(
        env,
        "smart_construction_seed.seed_dict_contract_type_in",
        [("type", "=", "contract_type")],
    )

    sale_tax = env.ref("smart_construction_seed.tax_sale_9", raise_if_not_found=False)
    purchase_tax = env.ref("smart_construction_seed.tax_purchase_13", raise_if_not_found=False)

    today = fields.Date.context_today(env.user)
    ContractLine = env["construction.contract.line"].sudo()
    Contract = env["construction.contract"].sudo()
    Tender = env["tender.bid"].sudo()
    warn_codes = DEMO_WARN_PROJECT_CODES
    split_codes = {"DEMO-PJ-TENDER"}

    for project in projects:
        is_core_demo = bool(project.project_code and project.project_code.startswith("DEMO-"))
        if not is_core_demo and project.lifecycle_state == "paused":
            _cleanup_paused_showroom_settlement(env, project)
            continue

        has_contract = Contract.search_count([("project_id", "=", project.id)]) > 0
        has_tender = Tender.search_count([("project_id", "=", project.id)]) > 0
        if (not is_core_demo and
                project.lifecycle_state in ("draft", "in_progress", "paused") and
                not has_contract):
            if not has_tender:
                _ensure_tender(env, project, owner)
            continue

        out_vals = {
            "subject": f"{project.name}-收入合同",
            "type": "out",
            "project_id": project.id,
            "partner_id": owner.id,
            "category_id": contract_category.id if contract_category else False,
            "contract_type_id": contract_type_out.id if contract_type_out else False,
            "date_contract": today,
            "date_start": today,
            "date_end": today,
            "state": "confirmed",
        }
        if sale_tax:
            out_vals["tax_id"] = sale_tax.id
        out_contract = _ensure_contract(env, out_vals)

        in_vals = {
            "subject": f"{project.name}-分包合同",
            "type": "in",
            "project_id": project.id,
            "partner_id": subcontract.id,
            "category_id": contract_category.id if contract_category else False,
            "contract_type_id": contract_type_in.id if contract_type_in else False,
            "date_contract": today,
            "date_start": today,
            "date_end": today,
            "state": "confirmed",
        }
        if purchase_tax:
            in_vals["tax_id"] = purchase_tax.id
        in_contract = _ensure_contract(env, in_vals)

        for contract, lines in [
            (
                out_contract,
                [
                    {"sequence": 10, "qty_contract": 1, "price_contract": 880000.0},
                    {"sequence": 20, "qty_contract": 1, "price_contract": 320000.0},
                ],
            ),
            (
                in_contract,
                [
                    {"sequence": 10, "qty_contract": 1, "price_contract": 240000.0},
                    {"sequence": 20, "qty_contract": 1, "price_contract": 160000.0},
                ],
            ),
        ]:
            for vals in lines:
                existing = ContractLine.search(
                    [("contract_id", "=", contract.id), ("sequence", "=", vals["sequence"])],
                    limit=1,
                )
                payload = dict(vals)
                payload["contract_id"] = contract.id
                payload["price_contract"] = vals["price_contract"]
                if existing:
                    existing.write(payload)
                else:
                    ContractLine.create(payload)

        _ensure_funding_baseline(env, project)
        settlement = _ensure_settlement(env, project, in_contract)
        split_first = project.project_code in split_codes
        _ensure_purchase_order(env, settlement, split_first_line=split_first)
        if project.project_code in warn_codes:
            ratio = DEMO_INVOICE_WARN_RATIO_BY_STATE.get(project.lifecycle_state, 1.0)
        else:
            ratio = DEMO_INVOICE_RATIO_BY_STATE.get(project.lifecycle_state, 1.0)
        _ensure_invoice_info(env, settlement, ratio)
        _approve_settlement(env, settlement)
        _ensure_payments(env, project, in_contract, out_contract, settlement)


register(
    SeedStep(
        name="demo_40_contracts",
        description="Seed contract records for demo project.",
        run=run,
    )
)
