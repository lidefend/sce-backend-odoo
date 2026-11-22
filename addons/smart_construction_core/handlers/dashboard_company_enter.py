# -*- coding: utf-8 -*-
from __future__ import annotations

import time

from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from odoo.addons.smart_core.core.contract_version_negotiation import (
    ContractNegotiationError,
    PAGE_BLOCK_DATA_CAPABILITY,
    carrier_enabled,
    negotiate_payload,
)
from odoo.addons.smart_construction_core.services.dashboard_contract_builder import DashboardContractBuilder


class DashboardCompanyEnterHandler(BaseIntentHandler):
    INTENT_TYPE = "dashboard.company.enter"
    DESCRIPTION = "返回公司驾驶舱 scene contract"
    VERSION = "1.0.0"
    ETAG_ENABLED = False
    REQUIRED_GROUPS = ["base.group_user"]

    def handle(self, payload=None, ctx=None):
        ts0 = time.time()
        try:
            negotiation = negotiate_payload(payload)
        except ContractNegotiationError as exc:
            return {
                "ok": False,
                "error": {
                    "code": 409,
                    "message": str(exc),
                    "reason_code": exc.reason_code,
                },
                "meta": {"intent": self.INTENT_TYPE},
            }
        builder = DashboardContractBuilder(self.env)
        contract = builder.build(
            page_block_data_enabled=carrier_enabled(negotiation, PAGE_BLOCK_DATA_CAPABILITY),
            timezone=str((ctx or {}).get("tz") or getattr(self.env.user, "tz", "") or "UTC"),
        )
        return {
            "ok": True,
            "data": contract,
            "meta": {
                "intent": self.INTENT_TYPE,
                "elapsed_ms": int((time.time() - ts0) * 1000),
                "source_authority": builder.source_authority_contract(),
                "contract_negotiation": negotiation,
            },
        }
