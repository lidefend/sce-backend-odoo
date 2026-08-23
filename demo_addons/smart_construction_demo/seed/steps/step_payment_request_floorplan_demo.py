# -*- coding: utf-8 -*-
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


def run(env):
    """Reset the minimal submit-ready payment request used by product acceptance."""
    payment_model = env["payment.request"].sudo()
    existing = _owned_fixture(env)
    same_name = payment_model.search([("name", "=", FIXTURE_NAME)])
    if same_name and (not existing or same_name != existing):
        raise RuntimeError(
            "payment request fixture refuses to delete or adopt unowned records named %s"
            % FIXTURE_NAME
        )
    non_deletable = existing.filtered(lambda item: item.state not in ("draft", "cancel")) if existing else existing
    if non_deletable:
        non_deletable.with_context(allow_transition=True).write({"state": "cancel"})
    if existing:
        existing.unlink()
    contract = env.ref("smart_construction_demo.sc_demo_contract_in_069_payment")
    record = payment_model.create(
        {
            "name": FIXTURE_NAME,
            "type": "pay",
            "project_id": contract.project_id.id,
            "contract_id": contract.id,
            "partner_id": contract.partner_id.id,
            "amount": 10000.0,
            "date_request": "2025-08-22",
            "note": "受管付款申请黄金页面提交闭环 fixture",
        }
    )
    _bind_fixture_xmlid(env, record)
    return {"ok": True, "created": 1, "payment_request_id": record.id}


register(
    SeedStep(
        name="payment_request_floorplan_demo",
        description="Reset one contract-backed draft payment request for Floorplan acceptance.",
        run=run,
    )
)
