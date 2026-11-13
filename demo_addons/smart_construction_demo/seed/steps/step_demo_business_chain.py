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

    Contract = env["construction.contract"].sudo()
    expense_contract = _one(
        Contract.search(
            [
                ("project_id", "=", project.id),
                ("type", "=", "in"),
                ("subject", "=", f"{project.name}-分包合同"),
            ]
        ),
        "DEMO-01 分包合同必须唯一存在。",
    )
    income_contract = _one(
        Contract.search(
            [
                ("project_id", "=", project.id),
                ("type", "=", "out"),
                ("subject", "=", f"{project.name}-收入合同"),
            ]
        ),
        "DEMO-01 收入合同必须唯一存在。",
    )
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
        Request.search(
            [
                ("project_id", "=", project.id),
                ("type", "=", "pay"),
                ("contract_id", "=", expense_contract.id),
                ("settlement_id", "=", settlement.id),
                ("amount", "=", 160000.0),
                ("state", "!=", "cancel"),
            ]
        ),
        "DEMO-01 已审批付款申请必须唯一存在。",
    )
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
