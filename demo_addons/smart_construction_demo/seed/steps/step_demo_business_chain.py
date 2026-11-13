# -*- coding: utf-8 -*-
"""Complete the single DEMO-01 execution project business story."""

from odoo import fields
from odoo.exceptions import UserError

from ..registry import SeedStep, register
from ...tools.scenario_loader import _bind_generated_demo_xmlid
from .step_40_contracts_demo import (
    PROJECT_EXEC_CODE,
    _ensure_actionable_payment_draft,
    _ensure_complete_payment_request,
    _ensure_payment_execution,
    _fixed_demo01_payment_request,
)


def _one(records, message):
    if len(records) != 1:
        raise UserError(message)
    return records


def _ensure_project_context(project):
    expected = {
        "start_date": fields.Date.to_date("2026-10-19"),
        "end_date": fields.Date.to_date("2027-10-18"),
        "description": (
            "东环路城市快速路提升工程位于德阳经开区，建设内容包括道路拓宽、"
            "桥梁结构、管网迁改及交通附属工程。当前处于在建阶段，项目资料、"
            "WBS、清单、预算和成本事实共同支撑合同结算与付款执行演示。"
        ),
    }
    changes = {
        name: value
        for name, value in expected.items()
        if project[name] != value
    }
    if changes:
        project.write(changes)


def run(env):
    project = env["project.project"].sudo().search(
        [("project_code", "=", PROJECT_EXEC_CODE)], limit=2
    )
    project = _one(project, "DEMO-01 主项目必须唯一存在。")
    _ensure_project_context(project)

    expense_contract = env.ref(
        "smart_construction_demo.sc_demo_exec_expense_contract",
        raise_if_not_found=False,
    )
    if expense_contract:
        if (
            expense_contract._name != "construction.contract"
            or expense_contract.project_id != project
            or expense_contract.type != "in"
        ):
            raise UserError("DEMO-01 固定分包合同身份冲突。")
    else:
        expense_contract = _one(
            env["construction.contract"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("type", "=", "in"),
                    ("subject", "=", f"{project.name}-分包合同"),
                ]
            ),
            "DEMO-01 分包合同必须唯一存在。",
        )

    income_contract = env.ref(
        "smart_construction_demo.sc_demo_exec_income_contract",
        raise_if_not_found=False,
    )
    if income_contract:
        if (
            income_contract._name != "construction.contract"
            or income_contract.project_id != project
            or income_contract.type != "out"
        ):
            raise UserError("DEMO-01 固定收入合同身份冲突。")
    else:
        income_contract = _one(
            env["construction.contract"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("type", "=", "out"),
                    ("subject", "=", f"{project.name}-收入合同"),
                ]
            ),
            "DEMO-01 收入合同必须唯一存在。",
        )

    settlement = env.ref(
        "smart_construction_demo.sc_demo_exec_settlement",
        raise_if_not_found=False,
    )
    if settlement:
        if (
            settlement._name != "sc.settlement.order"
            or settlement.project_id != project
            or settlement.contract_id != expense_contract
            or settlement.state == "cancel"
        ):
            raise UserError("DEMO-01 固定结算单身份冲突。")
    else:
        settlement = _one(
            env["sc.settlement.order"].sudo().search(
                [
                    ("project_id", "=", project.id),
                    ("contract_id", "=", expense_contract.id),
                    ("state", "!=", "cancel"),
                ]
            ),
            "DEMO-01 结算单必须唯一存在。",
        )
    Request = env["payment.request"].sudo()
    pay_request = _one(
        _fixed_demo01_payment_request(
            env, project, expense_contract, settlement
        ),
        "DEMO-01 固定付款申请必须唯一存在。",
    )
    receipt_request = env.ref(
        "smart_construction_demo.sc_demo_exec_receipt_request",
        raise_if_not_found=False,
    )
    if receipt_request:
        if (
            receipt_request._name != "payment.request"
            or receipt_request.project_id != project
            or receipt_request.contract_id != income_contract
            or receipt_request.type != "receive"
            or receipt_request.state == "cancel"
        ):
            raise UserError("DEMO-01 固定收款申请身份冲突。")
    else:
        receipt_request = _one(
            Request.search(
                [
                    ("project_id", "=", project.id),
                    ("type", "=", "receive"),
                    ("contract_id", "=", income_contract.id),
                    ("amount", "=", 120000.0),
                    ("state", "!=", "cancel"),
                ]
            ),
            "DEMO-01 收款申请必须唯一存在。",
        )
    pay_request = _ensure_complete_payment_request(env, pay_request)

    bindings = (
        ("sc_demo_exec_expense_contract", expense_contract),
        ("sc_demo_exec_income_contract", income_contract),
        ("sc_demo_exec_settlement", settlement),
        ("sc_demo_exec_payment_request", pay_request),
        ("sc_demo_exec_receipt_request", receipt_request),
    )
    for name, record in bindings:
        _bind_generated_demo_xmlid(env, name, record)

    execution, ledger = _ensure_payment_execution(env, pay_request)
    draft = _ensure_actionable_payment_draft(
        env, project, expense_contract, settlement
    )
    if draft.state == "cancel":
        raise UserError("DEMO-01 可操作付款草稿已被取消，请按受管演示重建恢复。")
    if execution.project_id != project or ledger.project_id != project:
        raise UserError("DEMO-01 执行或台账与其他业务事实跨项目。")
    return True


register(
    SeedStep(
        name="demo_01_business_chain",
        description="Complete the DEMO-01 project contract-to-ledger story.",
        run=run,
    )
)
