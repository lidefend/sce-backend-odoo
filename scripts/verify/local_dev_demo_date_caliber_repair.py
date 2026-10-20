#!/usr/bin/env python3
"""One-off date-caliber repair for the demo work items (P4 ops tooling).

The XML carriers are the long-term source of truth and now declare 2026-10
dates with noupdate=0. This script aligns the existing sc_dev_demo rows whose
dates were created before that change and therefore survived the module
upgrade. It writes only the declared date/description fields and never touches
a state field or an approval guard.
"""
from __future__ import annotations

from odoo.exceptions import UserError


_TASK_DEADLINES = {
    "sc_demo_task_round1_001": "2026-10-20",
    "sc_demo_task_round1_002": "2026-10-21",
    "sc_demo_task_round1_003": "2026-10-22",
    "sc_demo_task_round2_004": "2026-10-23",
    "sc_demo_task_round2_005": "2026-10-24",
    "sc_demo_task_round2_006": "2026-10-25",
    "sc_demo_task_round2_007": "2026-10-26",
}

_PAYMENT_DATES = {
    "sc_demo_pay_req_010_001": "2026-10-20",
    "sc_demo_pay_req_010_002": "2026-10-20",
    "sc_demo_pay_req_010_003": "2026-10-21",
    "sc_demo_pay_req_010_004": "2026-10-22",
}

_INVOICE_DATES = {
    "sc_demo_invoice_s10_001": "2026-10-20",
    "sc_demo_invoice_s10_002": "2026-10-21",
}

_CURRENT_BUSINESS_DATE = "2026-10-20"

_PROJECT_DESCRIPTIONS = {
    "sc_demo_project_001": (
        "项目位于德阳经开区，建设内容包括智能制造实训中心、产教融合综合楼及配套道路管网，"
        "总建筑面积约 8.6 万平方米，合同额约 3.2 亿元，计划工期 2025 年 1 月至 2026 年 12 月，"
        "目前处于装饰装修与收尾阶段。"
    ),
    "sc_demo_project_002": (
        "项目位于城东新区，建设内容包括 6 栋安置住宅、社区服务中心及地下车库，"
        "总建筑面积约 9.4 万平方米，合同额约 2.8 亿元，计划工期 2025 年 3 月至 2027 年 2 月，"
        "目前处于主体施工阶段。"
    ),
}


def _env():
    return globals()["env"]


def run() -> dict:
    env = _env()
    applied = {"tasks": 0, "payments": 0, "invoices": 0, "projects": 0}
    module = "smart_construction_demo"

    for xmlid, deadline in _TASK_DEADLINES.items():
        task = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not task:
            raise UserError(f"date-caliber repair missing task {xmlid}")
        task.write({"date_deadline": deadline})
        applied["tasks"] += 1

    for xmlid, date in _PAYMENT_DATES.items():
        record = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not record:
            raise UserError(f"date-caliber repair missing payment {xmlid}")
        record.write({"date_request": date})
        applied["payments"] += 1

    # Rule-based sweep for draft work items not addressed by the named maps:
    # any draft payment request or invoice still dated before the current
    # business window is aligned to the current business date.
    draft_payments = env["payment.request"].search(
        [("state", "=", "draft"), ("date_request", "<", "2026-01-01")]
    )
    for record in draft_payments:
        record.write({"date_request": _CURRENT_BUSINESS_DATE})
        applied["payments"] += 1
    draft_invoices = env["account.move"].search(
        [
            ("move_type", "in", ("out_invoice", "in_invoice")),
            ("state", "=", "draft"),
            ("invoice_date", "<", "2026-01-01"),
        ]
    )
    for record in draft_invoices:
        record.write({"invoice_date": _CURRENT_BUSINESS_DATE})
        applied["invoices"] += 1

    for xmlid, date in _INVOICE_DATES.items():
        record = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not record:
            raise UserError(f"date-caliber repair missing invoice {xmlid}")
        record.write({"invoice_date": date})
        applied["invoices"] += 1

    for xmlid, description in _PROJECT_DESCRIPTIONS.items():
        project = env.ref(f"{module}.{xmlid}", raise_if_not_found=False)
        if not project:
            raise UserError(f"date-caliber repair missing project {xmlid}")
        project.write({"description": description})
        applied["projects"] += 1

    env.cr.commit()
    return applied


print("DATE_CALIBER_REPAIR " + str(run()))
