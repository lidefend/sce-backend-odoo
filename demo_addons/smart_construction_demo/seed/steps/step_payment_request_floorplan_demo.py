# -*- coding: utf-8 -*-
import re

from ..registry import SeedStep, register


FIXTURE_NAME = "DEMO-PR-FLOORPLAN-001"
FIXTURE_XMLID = "smart_construction_demo.payment_request_floorplan_demo_record"


def _owned_fixture(env):
    record = env.ref(FIXTURE_XMLID, raise_if_not_found=False)
    if record and record._name != "payment.request":
        raise RuntimeError("%s points to %s" % (FIXTURE_XMLID, record._name))
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


def _approval_fixture_actors(env, company):
    policy = env["sc.approval.policy"].sudo().get_active_policy(
        "payment.request", company=company
    )
    if not policy or not policy.approval_required or policy.mode == "none":
        return env["res.users"]
    actors = env["res.users"]
    for step in policy.step_ids.filtered("active").sorted("sequence"):
        group = step.approve_group_id
        xmlids = group.sudo().users.get_external_id() if group else {}
        candidates = group.sudo().users.filtered(
            lambda user: user.active
            and not user.share
            and user.login
            and xmlids.get(user.id, "").startswith("smart_construction_demo.")
        ).sorted("id")
        if not candidates:
            raise RuntimeError(
                "payment request fixture approval step %s has no governed demo reviewer"
                % step.display_name
            )
        actors |= candidates[0]
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


def run(env):
    """Reset the minimal submit-ready payment request used by product acceptance."""
    payment_model = env["payment.request"].sudo()
    ledger_model = env["payment.ledger"].sudo()
    existing = _owned_fixture(env)
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
        if existing.state not in ("draft", "cancel"):
            existing.with_context(allow_transition=True).write({"state": "cancel"})
        existing.unlink()
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
            "payment_account_name": "演示收款单位结算账户",
            "payment_bank_name": "演示建设银行",
            "payment_account_no": "DEMO-PAYEE-0001",
            "payer_unit": "演示付款单位基本户",
            "note": "受管付款申请黄金页面提交闭环 fixture",
        }
    )
    _bind_fixture_xmlid(env, record)
    return {
        "ok": True,
        "created": 1,
        "payment_request_id": record.id,
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
