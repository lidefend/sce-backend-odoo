# -*- coding: utf-8 -*-
"""Complete the DEMO-02 income receipt story for the primary project."""

from odoo import fields
from odoo.exceptions import UserError

from ...tools.scenario_loader import (
    _bind_generated_demo_xmlid,
    _demo_action_record,
    _generated_demo_model_data,
    drive_seeded_record,
)
from ..registry import SeedStep, register
from .step_40_contracts_demo import (
    DEMO02_ACTIONABLE_RECEIPT_NOTE,
    PROJECT_EXEC_CODE,
    _approve_payment,
    _fixed_demo01_receipt_request,
    _payment_account_vals,
)


ACTIONABLE_RECEIPT_AMOUNT = 180000.0


def _one(records, message):
    if len(records) != 1:
        raise UserError(message)
    return records


def _record_from_generated_identity(env, name, model):
    data = _generated_demo_model_data(env, name)
    if not data:
        return env[model].browse()
    if data.model != model:
        raise UserError(f"Demo identity {name} has unexpected model {data.model}.")
    return env[model].sudo().browse(data.res_id).exists()


def _fixed_income_contract(env, project):
    contract = _record_from_generated_identity(
        env, "sc_demo_exec_income_contract", "construction.contract"
    )
    if contract:
        if contract.project_id != project or contract.type != "out":
            raise UserError("DEMO-02 income contract identity conflict.")
        return contract
    contracts = env["construction.contract"].sudo().search(
        [
            ("project_id", "=", project.id),
            ("type", "=", "out"),
            ("subject", "=", f"{project.name}-收入合同"),
        ],
        limit=2,
    )
    return _one(contracts, "DEMO-02 income contract must be unique.")


def _receipt_date(project, contract):
    return (
        contract.date_start
        or project.start_date
        or fields.Date.context_today(contract.env.user)
    )


def _receipt_account_values(partner):
    account = _payment_account_vals(partner)
    return {
        "receiving_account": account["actual_payee_unit"],
        "receiving_account_name": account["payment_account_name"],
        "receiving_bank_name": account["payment_bank_name"],
        "receiving_account_no": account["payment_account_no"],
    }


def _receipt_vals(project, contract, request, note):
    return {
        "source_kind": "receipt_income",
        "source_family": "engineering_progress_receipt_visible",
        "project_id": project.id,
        "company_id": project.company_id.id,
        "partner_id": request.partner_id.id,
        "contract_id": contract.id,
        "payment_request_id": request.id,
        "amount": request.amount,
        "currency_id": request.currency_id.id,
        "date_receipt": _receipt_date(project, contract),
        "document_no": f"DEMO02-{request.id}",
        "receipt_type": "工程进度款收入",
        "income_category": "工程进度款收入",
        "payment_method": "银行转账",
        "note": note,
        **_receipt_account_values(request.partner_id),
    }


def _ensure_receipt(env, project, contract, request, xmlid, note):
    Receipt = env["sc.receipt.income"].sudo()
    receipt = _record_from_generated_identity(
        env, xmlid, "sc.receipt.income"
    )
    if receipt:
        if (
            receipt.project_id != project
            or receipt.contract_id != contract
            or receipt.payment_request_id != request
        ):
            raise UserError(f"{xmlid} business identity conflict.")
        return receipt

    candidates = Receipt.search(
        [("payment_request_id", "=", request.id)],
        limit=2,
    )
    if len(candidates) > 1:
        raise UserError(f"{xmlid} receipt identity is not unique.")
    if candidates:
        return candidates

    actor = _demo_action_record(
        env,
        env["sc.receipt.income"],
        "action_confirm",
        "smart_construction_demo.user_sc_fin_01",
    )
    return actor.create(_receipt_vals(project, contract, request, note))


def _ensure_fixed_receipt_chain(env, project, contract, request):
    if request.state not in ("approved", "done"):
        raise UserError("DEMO-02 fixed receipt request must be approved before receipt.")
    receipt = _ensure_receipt(
        env,
        project,
        contract,
        request,
        "sc_demo_exec_receipt_income",
        "DEMO-02 主业务链固定工程进度回款。",
    )
    drive_seeded_record(env, receipt, "received")
    receipt.invalidate_recordset()
    request.invalidate_recordset()

    if receipt.state != "received":
        raise UserError("DEMO-02 fixed receipt did not reach received.")
    if request.state != "done":
        raise UserError("DEMO-02 fixed request did not reach done.")
    ledger = receipt.treasury_ledger_id
    if not ledger:
        raise UserError("DEMO-02 fixed receipt has no treasury ledger.")
    if (
        ledger.direction != "in"
        or ledger.state != "posted"
        or ledger.payment_request_id != request
        or ledger.project_id != project
    ):
        raise UserError("DEMO-02 fixed receipt treasury identity mismatch.")
    if abs((receipt.amount or 0.0) - (request.amount or 0.0)) > 0.01:
        raise UserError("DEMO-02 fixed receipt amount differs from its request.")
    if abs((ledger.amount or 0.0) - (request.amount or 0.0)) > 0.01:
        raise UserError("DEMO-02 fixed treasury amount differs from its request.")

    _bind_generated_demo_xmlid(
        env, "sc_demo_exec_receipt_request", request
    )
    _bind_generated_demo_xmlid(
        env, "sc_demo_exec_receipt_income", receipt
    )
    _bind_generated_demo_xmlid(
        env, "sc_demo_exec_receipt_treasury_ledger", ledger
    )
    return receipt, ledger


def _ensure_actionable_receipt_request(env, project, contract):
    Request = env["payment.request"].sudo()
    request = _record_from_generated_identity(
        env,
        "sc_demo_exec_actionable_receipt_request",
        "payment.request",
    )
    if request:
        if (
            request.project_id != project
            or request.contract_id != contract
            or request.type != "receive"
        ):
            raise UserError("DEMO-02 actionable receipt request identity conflict.")
        return request

    candidates = Request.search(
        [
            ("project_id", "=", project.id),
            ("contract_id", "=", contract.id),
            ("type", "=", "receive"),
            ("note", "=", DEMO02_ACTIONABLE_RECEIPT_NOTE),
        ],
        limit=2,
    )
    if len(candidates) > 1:
        raise UserError("DEMO-02 actionable receipt request is not unique.")
    if not candidates:
        actor = _demo_action_record(
            env,
            env["payment.request"],
            "action_submit",
            "smart_construction_demo.user_demo_role_project_a_member",
        )
        candidates = actor.create(
            {
                "type": "receive",
                "project_id": project.id,
                "partner_id": contract.partner_id.id,
                "contract_id": contract.id,
                "amount": ACTIONABLE_RECEIPT_AMOUNT,
                "currency_id": contract.currency_id.id,
                "date_request": _receipt_date(project, contract),
                "note": DEMO02_ACTIONABLE_RECEIPT_NOTE,
            }
        )
    request = _approve_payment(env, candidates)
    _bind_generated_demo_xmlid(
        env, "sc_demo_exec_actionable_receipt_request", request
    )
    return request


def _ensure_actionable_receipt_draft(env, project, contract, request):
    Receipt = env["sc.receipt.income"].sudo()
    receipt = _record_from_generated_identity(
        env,
        "sc_demo_exec_actionable_receipt_draft",
        "sc.receipt.income",
    )
    if receipt:
        if (
            receipt.project_id != project
            or receipt.contract_id != contract
            or receipt.payment_request_id != request
        ):
            raise UserError("DEMO-02 actionable receipt draft identity conflict.")
        return receipt

    candidates = Receipt.search(
        [("payment_request_id", "=", request.id)],
        limit=2,
    )
    if len(candidates) > 1:
        raise UserError("DEMO-02 actionable receipt draft is not unique.")
    if not candidates:
        actor = _demo_action_record(
            env,
            env["sc.receipt.income"],
            "action_confirm",
            "smart_construction_demo.user_sc_fin_01",
        )
        candidates = actor.create(
            _receipt_vals(
                project,
                contract,
                request,
                "DEMO-02 可操作收款登记草稿：第二期进度回款。",
            )
        )
    receipt = candidates
    _bind_generated_demo_xmlid(
        env, "sc_demo_exec_actionable_receipt_draft", receipt
    )
    return receipt


def run(env):
    project = _one(
        env["project.project"].sudo().search(
            [("project_code", "=", PROJECT_EXEC_CODE)], limit=2
        ),
        "DEMO-02 project must be unique.",
    )
    contract = _fixed_income_contract(env, project)
    fixed_request = _one(
        _fixed_demo01_receipt_request(env, project, contract),
        "DEMO-02 fixed receipt request must be unique.",
    )
    if abs((fixed_request.amount or 0.0) - 120000.0) > 0.01:
        raise UserError("DEMO-02 fixed receipt request amount must be 120000.")

    _ensure_fixed_receipt_chain(env, project, contract, fixed_request)
    actionable_request = _ensure_actionable_receipt_request(
        env, project, contract
    )
    _ensure_actionable_receipt_draft(
        env, project, contract, actionable_request
    )
    return True


register(
    SeedStep(
        name="demo_02_receipt_chain",
        description="Complete the DEMO-02 fixed receipt chain and actionable sample.",
        run=run,
    )
)
