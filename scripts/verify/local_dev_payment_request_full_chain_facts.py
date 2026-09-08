"""Resolve authoritative facts for the governed local.dev payment full-chain fixture."""

import json


request = env.ref("smart_construction_demo.payment_request_floorplan_demo_record")
executions = env["sc.payment.execution"].sudo().with_context(active_test=False).search(
    [("payment_request_id", "=", request.id)], order="id"
)
ledgers = env["payment.ledger"].sudo().with_context(active_test=False).search(
    [("payment_request_id", "=", request.id)], order="id"
)
payload = {
    "database": env.cr.dbname,
    "request": {
        "id": int(request.id),
        "name": str(request.name or ""),
        "state": str(request.state or ""),
        "validation_status": str(request.validation_status or ""),
        "amount": float(request.amount or 0.0),
        "paid_amount_total": float(request.paid_amount_total or 0.0),
        "unpaid_amount": float(request.unpaid_amount or 0.0),
        "is_fully_paid": bool(request.is_fully_paid),
        "has_active_payment_execution": bool(request.has_active_payment_execution),
        "account_complete": bool(request.payment_account_name and request.payment_bank_name and request.payment_account_no),
    },
    "executions": [
        {
            "id": int(row.id),
            "state": str(row.state or ""),
            "validation_status": str(row.validation_status or ""),
            "paid_amount": float(row.paid_amount or 0.0),
            "active": bool(row.active),
            "review_ids": [int(review.id) for review in row.review_ids],
        }
        for row in executions
    ],
    "ledgers": [
        {
            "id": int(row.id),
            "state": str(row.state or ""),
            "amount": float(row.amount or 0.0),
            "payment_execution_id": int(row.payment_execution_id.id or 0),
        }
        for row in ledgers
    ],
}
print("LOCAL_DEV_PAYMENT_FULL_CHAIN_FACTS_JSON=%s" % json.dumps(payload, ensure_ascii=True, separators=(",", ":")))
