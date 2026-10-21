"""P1 readiness intent; authorization uses the platform handler service."""
from odoo.addons.smart_core.core.base_handler import BaseIntentHandler
from ..services.baseline_readiness import build_readiness


class BaselineReadinessHandler(BaseIntentHandler):
    INTENT_TYPE = "baseline.readiness"
    DESCRIPTION = "项目与付款提交前的只读就绪检查"
    VERSION = "1.0.0"
    REQUIRED_GROUPS = ["base.group_user"]
    ETAG_ENABLED = False
    SOURCE_KIND = "native_submission_readiness_projection"
    SOURCE_AUTHORITIES = ("project.project", "payment.request", "ir.model.access", "ir.rule")

    def handle(self, payload=None, ctx=None):
        params = payload if isinstance(payload, dict) else {}
        if isinstance(params.get("params"), dict):
            params = params["params"]
        try:
            data = build_readiness(self.env, params.get("model"), params.get("record_id"))
        except ValueError as exc:
            return {"ok": False, "code": 400,
                    "error": {"code": "INVALID_PARAMS", "message": str(exc)}}
        return {"ok": True, "data": data}
