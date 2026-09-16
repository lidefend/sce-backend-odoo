# -*- coding: utf-8 -*-
import re
from typing import Any, Dict


WRITE_INTENT_TOKENS = {
    "approve",
    "batch",
    "cancel",
    "complete",
    "create",
    "delete",
    "done",
    "execute",
    "freeze",
    "import",
    "patch",
    "pin",
    "promote",
    "publish",
    "reject",
    "revoke",
    "rollback",
    "rotate",
    "save",
    "schedule",
    "set",
    "submit",
    "sync",
    "track",
    "unlink",
    "update",
    "upload",
    "write",
}

WRITE_MODES = {"create", "write", "unlink"}


def nested_params(params: Dict[str, Any] | None) -> Dict[str, Any]:
    root = params if isinstance(params, dict) else {}
    nested = root.get("params")
    if isinstance(nested, dict):
        return nested
    payload = root.get("payload")
    if isinstance(payload, dict):
        return payload
    return root


def normalize_intent_operation(intent_name: str, params: Dict[str, Any] | None = None) -> str:
    intent = str(intent_name or "").strip().lower()
    business_params = nested_params(params)
    op = str((business_params or {}).get("op") or "").strip().lower()
    action = str((business_params or {}).get("action") or "").strip().lower()

    if intent == "api.data":
        return op or "read"
    if intent == "api.data.batch":
        if action:
            return action
        if op:
            return op
        return "batch"
    if intent.startswith("api.data."):
        suffix = intent.split(".", 2)[-1].strip().lower()
        return suffix or op or "read"
    if op:
        return op
    tokens = [token for token in re.split(r"[._:-]+", intent) if token]
    if "create" in tokens:
        return "create"
    if "unlink" in tokens or "delete" in tokens:
        return "unlink"
    if any(token in WRITE_INTENT_TOKENS for token in tokens):
        return "write"
    return "read"


def access_mode_for_operation(operation: str) -> str:
    op = str(operation or "").strip().lower()
    if op in {"create", "new"}:
        return "create"
    if op in {
        "write",
        "update",
        "set",
        "archive",
        "activate",
        "assign",
        "unarchive",
        "batch",
        "batch.write",
        "batch.update",
    }:
        return "write"
    if op in {"unlink", "delete", "remove", "batch.unlink", "batch.delete"}:
        return "unlink"
    return "read"


def access_mode_for_intent(intent_name: str, params: Dict[str, Any] | None = None) -> str:
    return access_mode_for_operation(normalize_intent_operation(intent_name, params))


def is_write_intent(intent_name: str, params: Dict[str, Any] | None = None, *, non_idempotent: bool = False) -> bool:
    if non_idempotent:
        return True
    intent = str(intent_name or "").strip().lower()
    if not intent:
        return False
    return access_mode_for_intent(intent, params) in WRITE_MODES


def preview_write_error(intent_name, params=None, context=None, *, non_idempotent=False):
    """Preview context is restrictive only, including legacy handlers overriding run()."""
    params = params if isinstance(params, dict) else {}
    contexts = [params, params.get("context"), context]
    preview = any(isinstance(item, dict) and (item.get("business_config_preview_token") or item.get("preview_token")) for item in contexts)
    if preview and is_write_intent(intent_name, params, non_idempotent=non_idempotent):
        return {"ok": False, "error": {"code": "CONFIG_PREVIEW_READ_ONLY", "reason_code": "CONFIG_PREVIEW_READ_ONLY", "message": "未发布配置预览不允许业务写入，请返回正式业务页面办理。"}}
    return None
