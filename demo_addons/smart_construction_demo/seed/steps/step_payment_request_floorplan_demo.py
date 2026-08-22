# -*- coding: utf-8 -*-
from ..registry import SeedStep, register


FIXTURE_NAME = "DEMO-PR-FLOORPLAN-001"


def run(env):
    """Reset the minimal submit-ready payment request used by product acceptance."""
    payment_model = env["payment.request"].sudo()
    existing = payment_model.search([("name", "=", FIXTURE_NAME)])
    non_deletable = existing.filtered(lambda item: item.state not in ("draft", "cancel"))
    if non_deletable:
        non_deletable.with_context(allow_transition=True).write({"state": "cancel"})
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
    return {"ok": True, "created": 1, "payment_request_id": record.id}


register(
    SeedStep(
        name="payment_request_floorplan_demo",
        description="Reset one contract-backed draft payment request for Floorplan acceptance.",
        run=run,
    )
)
