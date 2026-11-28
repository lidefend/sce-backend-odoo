"""Seal native action rows with the same authority used by execution."""

from __future__ import annotations

from typing import Any

try:
    from odoo.exceptions import AccessError
except ImportError:  # pragma: no cover - host-runnable contract guards stub odoo
    class AccessError(Exception):
        pass


_REVIEW_DECISION_METHODS = {
    "action_approval_decision",
    "action_approval_reject",
    "reject_tier",
    "validate_tier",
}


def button_access_mode(env_model, method_name: str) -> str:
    """One access-mode authority shared by execution and contract production."""
    readonly_methods = getattr(env_model, "_sc_readonly_navigation_button_methods", ())
    if method_name in set(readonly_methods or ()):
        return "read"
    return "write"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _row_has_declared_verdict(row: dict[str, Any]) -> bool:
    if isinstance(row.get("authorizationAllowed"), bool):
        return True
    if row.get("entitlementEvaluated") is True:
        return True
    source_channel = _text(row.get("sourceChannel"))
    if source_channel in {"runtime_business_action", "product_contract"} and any(
        key in row
        for key in (
            "businessAvailable",
            "allowed",
            "enabled",
            "disabled",
        )
    ):
        return True
    return any(
        isinstance(trace, dict) and trace.get("entitlementEvaluated") is True
        for trace in row.get("sourceTrace") or []
    )


def _sync_status_contract(
    contract: dict[str, Any],
    row: dict[str, Any],
    *,
    allowed: bool,
    reason_code: str = "",
    reason_message: str = "",
) -> None:
    backend_identity = _text(row.get("backendIdentity"))
    action_key = _text(row.get("actionKey"))
    btn_id = f"btn.{action_key}" if action_key else ""
    statuses = _dict(contract.get("statusContract")).get("buttonStatus")
    if not isinstance(statuses, list):
        return
    status = next(
        (
            item
            for item in statuses
            if isinstance(item, dict)
            and (
                (backend_identity and _text(item.get("backendIdentity")) == backend_identity)
                or (btn_id and _text(item.get("btnId")) == btn_id)
            )
        ),
        None,
    )
    if status is None:
        status = {"btnId": btn_id} if btn_id else {}
        if not status:
            return
        statuses.append(status)
    if backend_identity:
        status["backendIdentity"] = backend_identity
    status["visible"] = bool(allowed)
    status["disabled"] = not allowed
    if reason_code:
        status["reasonCode"] = reason_code
    else:
        status.pop("reasonCode", None)
    if reason_message:
        status["reasonMessage"] = reason_message
    else:
        status.pop("reasonMessage", None)


def _record_rule_allows(model, record_id: int, access_mode: str) -> tuple[bool, str]:
    if record_id <= 0:
        return True, ""
    try:
        record = model.browse(record_id)
        if not record.exists():
            return False, "ACTION_RECORD_NOT_FOUND"
        record.check_access_rule(access_mode)
    except AccessError:
        return False, "ACTION_RECORD_PERMISSION_DENIED"
    except Exception:
        return False, "ACTION_RECORD_AUTHORITY_UNRESOLVED"
    return True, ""


def apply_native_action_permission_verdicts(
    env,
    contract: dict[str, Any],
    *,
    model: str,
    record_id: Any = 0,
) -> None:
    """Add explicit verdicts without overriding declared business actions.

    Missing or malformed native authority is denied. Record rules remain runtime
    ORM facts and are checked against the current record when one is supplied.
    """
    if not isinstance(contract, dict) or not model:
        return
    try:
        env_model = env[model]
    except Exception:
        return
    try:
        record_id = int(record_id or 0)
    except (TypeError, ValueError):
        record_id = 0

    action_contract = _dict(contract.get("actionContract"))
    rows = action_contract.get("actionRuleList")
    if not isinstance(rows, list):
        return
    model_access_cache: dict[str, bool] = {}
    record_rule_cache: dict[str, tuple[bool, str]] = {}
    for row in rows:
        if not isinstance(row, dict) or _row_has_declared_verdict(row):
            continue
        button = _dict(row.get("button"))
        button_type = _text(button.get("type") or button.get("buttonType")).lower() or "object"
        method_name = _text(
            button.get("name")
            or button.get("method")
            or _dict(row.get("target")).get("method")
        )
        if not method_name:
            row.update(
                authorizationAllowed=False,
                entitlementEvaluated=True,
                allowed=False,
                enabled=False,
                disabled=True,
                reasonCode="ACTION_IDENTITY_UNRESOLVED",
            )
            _sync_status_contract(
                contract,
                row,
                allowed=False,
                reason_code="ACTION_IDENTITY_UNRESOLVED",
            )
            continue

        if button_type == "server" or button_type == "server_action":
            access_mode = "write"
        elif button_type == "action":
            access_mode = "read"
        elif button_type == "object":
            if not callable(getattr(env_model, method_name, None)):
                row.update(
                    authorizationAllowed=False,
                    entitlementEvaluated=True,
                    allowed=False,
                    enabled=False,
                    disabled=True,
                    reasonCode="ACTION_METHOD_NOT_CALLABLE",
                )
                _sync_status_contract(
                    contract,
                    row,
                    allowed=False,
                    reason_code="ACTION_METHOD_NOT_CALLABLE",
                )
                continue
            access_mode = (
                "read"
                if method_name in _REVIEW_DECISION_METHODS
                else button_access_mode(env_model, method_name)
            )
        else:
            row.update(
                authorizationAllowed=False,
                entitlementEvaluated=True,
                allowed=False,
                enabled=False,
                disabled=True,
                reasonCode="ACTION_TYPE_UNRESOLVED",
            )
            _sync_status_contract(
                contract,
                row,
                allowed=False,
                reason_code="ACTION_TYPE_UNRESOLVED",
            )
            continue

        if access_mode not in model_access_cache:
            try:
                model_access_cache[access_mode] = bool(
                    env_model.check_access_rights(
                        access_mode,
                        raise_exception=False,
                    )
                )
            except Exception:
                model_access_cache[access_mode] = False
        allowed = model_access_cache[access_mode]
        reason_code = "" if allowed else "ACTION_PERMISSION_DENIED"
        if allowed:
            if access_mode not in record_rule_cache:
                record_rule_cache[access_mode] = _record_rule_allows(
                    env_model,
                    record_id,
                    access_mode,
                )
            allowed, reason_code = record_rule_cache[access_mode]
        row.update(
            authorizationAllowed=allowed,
            entitlementEvaluated=True,
            allowed=allowed,
            enabled=allowed,
            disabled=not allowed,
            **({"reasonCode": reason_code} if reason_code else {}),
        )
        _sync_status_contract(
            contract,
            row,
            allowed=allowed,
            reason_code=reason_code,
        )
