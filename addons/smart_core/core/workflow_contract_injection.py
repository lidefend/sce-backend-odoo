# -*- coding: utf-8 -*-
"""Inject the canonical platform workflow contract into ui.contract.v2."""

from __future__ import annotations

import logging

_logger = logging.getLogger(__name__)


def _text(value) -> str:
    return str(value or "").strip()


def inject_workflow_contract(env, contract, source, *, model, view_type):
    if view_type != "form" or not model:
        return
    if env is None or not getattr(env, "registry", None) or "smart_core.workflow.contract" not in env:
        return
    record_id = (
        source.get("record_id")
        or source.get("recordId")
        or ((source.get("head") or {}).get("record_id") if isinstance(source.get("head"), dict) else None)
    )
    try:
        record_id = int(record_id or 0)
    except Exception:
        record_id = 0
    try:
        service = env["smart_core.workflow.contract"]
        if model not in env.registry:
            return
        if record_id <= 0:
            workflow_contract = service.describe_model_actions(model)
        else:
            record = env[model].browse(record_id).exists()
            workflow_contract = service.describe_record(record) if record else {}
    except Exception:
        _logger.exception(
            "Failed to produce platform workflow contract for %s,%s", model, record_id
        )
        return
    if not isinstance(workflow_contract, dict) or not workflow_contract:
        return

    contract["workflowContract"] = workflow_contract
    status = contract.get("statusContract") if isinstance(contract.get("statusContract"), dict) else {}
    global_status = status.get("globalStatus") if isinstance(status.get("globalStatus"), dict) else {}
    if _text(workflow_contract.get("editability")) in {"readonly", "locked"}:
        global_status["pageAuth"] = "read"
        capabilities = global_status.get("effectiveRecordCapabilities")
        if isinstance(capabilities, dict):
            capabilities["write"] = False
        global_status["effectiveRenderProfile"] = "readonly"
    global_status["workflowPhase"] = workflow_contract.get("businessPhase")
    global_status["approvalPhase"] = workflow_contract.get("approvalPhase")
    status["globalStatus"] = global_status
    contract["statusContract"] = status
