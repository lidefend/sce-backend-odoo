# -*- coding: utf-8 -*-
import base64
import os
import re

from ..registry import SeedStep, register
from ..business_roles import business_model, prepare_project
from ...tools.scenario_loader import _demo_action_record, _DEMO_APPROVAL_ACTORS


FIXTURE_NAME = "PRQ-2026-001"
FIXTURE_XMLID = "smart_construction_demo.payment_request_floorplan_demo_record"
FIXTURE_ATTACHMENT_NAME = "付款申请附件清单.txt"
FIXTURE_ATTACHMENT_XMLID = "smart_construction_demo.payment_request_floorplan_demo_attachment"


def _owned_fixture(env):
    record = env.ref(FIXTURE_XMLID, raise_if_not_found=False)
    if record and record._name != "payment.request":
        raise RuntimeError("%s points to %s" % (FIXTURE_XMLID, record._name))
    return record


def _owned_fixture_attachment(env):
    record = env.ref(FIXTURE_ATTACHMENT_XMLID, raise_if_not_found=False)
    if record and record._name != "ir.attachment":
        raise RuntimeError("%s points to %s" % (FIXTURE_ATTACHMENT_XMLID, record._name))
    if record and (
        record.name != FIXTURE_ATTACHMENT_NAME
        or record.res_model not in (False, "payment.request")
    ):
        raise RuntimeError(
            "payment request fixture refuses to delete or adopt unowned attachment %s"
            % record.display_name
        )
    return record


def _bind_fixture_xmlid(env, record):
    module, name = FIXTURE_XMLID.split(".", 1)
    model_data = env["ir.model.data"].sudo()
    row = model_data.search([("module", "=", module), ("name", "=", name)], limit=1)
    values = {"model": record._name, "res_id": record.id, "noupdate": True}
    if row:
        row.write(values)
    else:
        model_data.create({"module": module, "name": name, **values})


def _bind_fixture_attachment_xmlid(env, record):
    module, name = FIXTURE_ATTACHMENT_XMLID.split(".", 1)
    model_data = env["ir.model.data"].sudo()
    row = model_data.search([("module", "=", module), ("name", "=", name)], limit=1)
    values = {"model": record._name, "res_id": record.id, "noupdate": True}
    if row:
        row.write(values)
    else:
        model_data.create({"module": module, "name": name, **values})


def _approval_fixture_actors(env, company):
    policy = env["sc.approval.policy"].sudo().get_active_policy(
        "payment.request", company=company
    )
    if not policy or not policy.approval_required or policy.mode == "none":
        return env["res.users"]
    actors = env["res.users"]
    for step in policy.step_ids.filtered("active").sorted("sequence"):
        group = step.approve_group_id
        group_xmlid = group.get_external_id().get(group.id) if group else None
        seat = _DEMO_APPROVAL_ACTORS.get(group_xmlid)
        actor = env.ref(seat, raise_if_not_found=False) if seat else False
        if not actor or not actor.active or actor.id == 1 or not actor.has_group(group_xmlid):
            raise RuntimeError("payment fixture has no declared authorized reviewer: %s" % group_xmlid)
        actors |= actor
    return actors


def _fixture_name_series():
    match = re.match(r"^(.*?)(\d+)$", FIXTURE_NAME)
    prefix = match.group(1) if match else "%s-" % FIXTURE_NAME
    width = len(match.group(2)) if match else 3
    return prefix, width, int(match.group(2)) if match else 1


def _next_fixture_name(payment_model):
    prefix, width, highest = _fixture_name_series()
    for name in payment_model.search([("name", "=like", "%s%%" % prefix)]).mapped("name"):
        suffix = str(name or "")[len(prefix) :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return "%s%s" % (prefix, str(highest + 1).zfill(width))


def _guidance_fixture(env):
    """Owned soft-risk sample; never mutate a shared partner or severity policy."""
    def owned(name, model, create):
        xmlid = "smart_construction_demo." + name
        record = env.ref(xmlid, raise_if_not_found=False)
        if record:
            if record._name != model:
                raise RuntimeError("guidance fixture XMLID model mismatch: " + xmlid)
            return record
        record = create()
        env["ir.model.data"].sudo().create({
            "module": "smart_construction_demo", "name": name,
            "model": model, "res_id": record.id, "noupdate": True,
        })
        return record

    source = env.ref("smart_construction_demo.sc_demo_contract_in_069_payment")
    prepare_project(env, source.project_id)
    partner = owned("payment_guidance_demo_partner", "res.partner", lambda: env["res.partner"].sudo().create({
        "name": "德阳华远贸易有限公司", "sc_blacklisted": True,
        "sc_blacklist_level": "blocked", "sc_blacklist_reason": "风险提示：请核实本次交易后继续。",
    }))
    contract = owned("payment_guidance_demo_contract", "construction.contract", lambda: business_model(env, "construction.contract").create({
        "partner_id": partner.id, "subject": "德阳华远贸易有限公司材料采购合同",
        "type": source.type, "project_id": source.project_id.id,
        "company_id": source.company_id.id, "currency_id": source.currency_id.id,
        "tax_id": source.tax_id.id,
        "line_ids": [(0, 0, {"qty_contract": 1.0, "price_contract": 1000.0})],
    }))
    if contract.project_id != source.project_id or contract.partner_id != partner:
        raise RuntimeError("guidance contract ownership conflicts with its declaration")
    from .step_40_contracts_demo import _confirm_contract
    contract = business_model(env, "construction.contract").browse(contract.id)
    _confirm_contract(contract)
    baseline = env["project.funding.baseline"].sudo().search([
        ("project_id", "=", contract.project_id.id), ("state", "=", "active"),
        ("normalization_state", "=", "normalized"),
    ], limit=2)
    if len(baseline) != 1:
        raise RuntimeError("guidance fixture requires one active normalized baseline")
    record = owned("payment_guidance_demo_record", "payment.request", lambda: business_model(env, "payment.request").create({
        "name": "PRQ-2026-G01", "type": "pay", "project_id": contract.project_id.id,
        "contract_id": contract.id, "partner_id": partner.id, "amount": 100.0,
        "date_request": baseline.period_start, "payment_account_name": partner.name,
        "payment_bank_name": "中国建设银行德阳分行", "payment_account_no": "DEMO-GUIDANCE-ONLY",
    }))
    if record.state != "draft" or record.partner_id != partner or record.contract_id != contract:
        raise RuntimeError("guidance fixture identity/state changed; refuse to overwrite")
    fact = record.submit_action_guidance
    if fact["blocking"] or not fact["requires_confirmation"]:
        raise RuntimeError("guidance fixture is not a native soft-risk candidate; keep existing policy")
    return {"ok": True, "payment_request_id": record.id, "partner_id": partner.id,
            "contract_id": contract.id, "guidance": fact, "scope": "guidance"}


def run(env):
    """Reset the minimal submit-ready payment request used by product acceptance."""
    scope = os.environ.get("PAYMENT_REQUEST_FIXTURE_SCOPE", "submit")
    if scope == "guidance":
        return _guidance_fixture(env)
    if scope != "submit":
        raise RuntimeError("unsupported payment fixture scope")
    contract = env.ref("smart_construction_demo.sc_demo_contract_in_069_payment")
    prepare_project(env, contract.project_id)
    payment_model = business_model(env, "payment.request")
    ledger_model = env["payment.ledger"].sudo()
    existing = _owned_fixture(env)
    if existing:
        existing = _demo_action_record(env, existing, "action_cancel", "smart_construction_demo.user_sc_fin_mgr_01")
    existing_attachment = _owned_fixture_attachment(env)
    same_name = payment_model.search([("name", "=", FIXTURE_NAME)])
    if same_name and (not existing or same_name != existing):
        traced_ids = set(
            ledger_model.search([("payment_request_id", "in", same_name.ids)]).mapped(
                "payment_request_id"
            ).ids
        )
        if any(record.id not in traced_ids for record in same_name):
            raise RuntimeError(
                "payment request fixture refuses to delete or adopt unowned records named %s"
                % FIXTURE_NAME
            )
    fixture_name = FIXTURE_NAME
    preserved_history_id = 0
    ledger_count = (
        ledger_model.search_count([("payment_request_id", "=", existing.id)])
        if existing
        else 0
    )
    if ledger_count:
        preserved_history_id = existing.id
        fixture_name = _next_fixture_name(payment_model)
    elif existing:
        if existing_attachment:
            existing_attachment.unlink()
            existing_attachment = env["ir.attachment"]
        if existing.state not in ("draft", "cancel"):
            existing.action_cancel()
        existing.unlink()
    elif existing_attachment:
        existing_attachment.unlink()
        existing_attachment = env["ir.attachment"]
    prefix, _width, _initial = _fixture_name_series()
    if not preserved_history_id and ledger_model.search_count(
        [("payment_request_id.name", "=like", "%s%%" % prefix)]
    ):
        fixture_name = _next_fixture_name(payment_model)
    contract = env.ref("smart_construction_demo.sc_demo_contract_in_069_payment")
    funding_baseline = env["project.funding.baseline"].sudo().search(
        [
            ("project_id", "=", contract.project_id.id),
            ("state", "=", "active"),
            ("normalization_state", "=", "normalized"),
        ],
        limit=2,
    )
    if len(funding_baseline) != 1 or not funding_baseline.period_start:
        raise RuntimeError(
            "payment request floorplan fixture requires one active normalized funding baseline"
        )
    approval_actors = _approval_fixture_actors(env, contract.company_id)
    if approval_actors:
        contract.project_id.sudo().message_subscribe(
            partner_ids=approval_actors.mapped("partner_id").ids
        )
    record = payment_model.create(
        {
            "name": fixture_name,
            "type": "pay",
            "project_id": contract.project_id.id,
            "contract_id": contract.id,
            "partner_id": contract.partner_id.id,
            "amount": 10000.0,
            "date_request": funding_baseline.period_start,
            "payment_account_name": "德阳市城市建设投资集团有限公司结算账户",
            "payment_bank_name": "中国建设银行德阳分行",
            "payment_account_no": "DEMO-PAYEE-0001",
            "payer_unit": "德阳建科建材有限公司基本户",
            # The request owns the immutable payer/payee account snapshot that a
            # payment execution inherits verbatim (``_payment_request_values``).
            # The payer side lives on the legacy_* carriers, so an incomplete
            # snapshot would force the finance operator to retype the payer
            # account on every 实付登记 create form.
            "legacy_payment_account_name": "德阳建科建材有限公司基本户",
            "legacy_payment_account_no": "DEMO-PAYER-0001",
            "note": "受管付款申请黄金页面提交闭环 fixture",
        }
    )
    attachment = payment_model.env["ir.attachment"].create(
        {
            "name": FIXTURE_ATTACHMENT_NAME,
            "type": "binary",
            "datas": base64.b64encode(b"Governed synthetic M2M relation fixture.\n"),
            "mimetype": "text/plain",
            "res_model": "payment.request",
            "res_id": record.id,
            "company_id": record.company_id.id,
        }
    )
    record.write({"attachment_ids": [(4, attachment.id)]})
    _bind_fixture_xmlid(env, record)
    _bind_fixture_attachment_xmlid(env, attachment)
    return {
        "ok": True,
        "created": 1,
        "payment_request_id": record.id,
        "attachment_id": attachment.id,
        "approval_actor_ids": approval_actors.ids,
        "preserved_history_id": preserved_history_id,
    }


register(
    SeedStep(
        name="payment_request_floorplan_demo",
        description="Reset one contract-backed draft payment request for Floorplan acceptance.",
        run=run,
    )
)
