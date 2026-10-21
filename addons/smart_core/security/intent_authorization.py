"""Shared REQUIRED_GROUPS semantics for intent execution and projection.

Groups remain native Odoo groups. A declaration is any-of, retaining the
existing tenant configuration administrator rule from the execution layer.
Model ACLs, record rules and request scope are separate mandatory checks.
"""
from odoo.addons.smart_core.security.platform_admin import user_is_tenant_config_admin


def user_has_required_groups(user, required_groups):
    required = list(required_groups or [])
    if not required:
        return True
    if not user or any(not isinstance(group, str) or not group.strip() for group in required):
        return False
    try:
        if user_is_tenant_config_admin(user):
            return True
    except Exception:
        pass
    for group in required:
        try:
            if user.has_group(group.strip()):
                return True
        except Exception:
            continue
    return False


def normalize_required_groups(env, required_groups):
    """Resolve native group references once; malformed declarations fail closed."""
    result = []
    for group in required_groups or []:
        if isinstance(group, str):
            xmlid = group.strip()
            if "." not in xmlid:
                return None
        else:
            group_id = group if isinstance(group, int) else getattr(group, "id", None)
            if not group_id or (not isinstance(group, int) and getattr(group, "_name", None) != "res.groups"):
                return None
            row = env["ir.model.data"].sudo().search([
                ("model", "=", "res.groups"), ("res_id", "=", group_id),
            ], limit=1)
            if not row or not row.module or not row.name:
                return None
            xmlid = f"{row.module}.{row.name}"
        result.append(xmlid)
    return result


def handler_group_decision(env, user, handler_cls, *, require_declaration=False):
    """Return one authorization decision consumed by execution and projections."""
    declared = getattr(handler_cls, "REQUIRED_GROUPS", []) or []
    groups = normalize_required_groups(env, declared)
    valid = groups is not None and (bool(groups) or not require_declaration)
    allowed = bool(valid and user_has_required_groups(user, groups))
    return {"allowed": allowed, "required_groups": groups or [],
            "reason_code": "OK" if allowed else "PERMISSION_DENIED"}


def authorize_handler(env, handler_cls, *, require_declaration=False):
    from odoo.exceptions import AccessError
    decision = handler_group_decision(env, env.user, handler_cls, require_declaration=require_declaration)
    if not decision["allowed"]:
        raise AccessError("PERMISSION_DENIED: intent REQUIRED_GROUPS not satisfied: %s" %
                          getattr(handler_cls, "INTENT_TYPE", handler_cls.__name__))
    return decision


def registered_handlers(env):
    from ..core.handler_registry import HANDLER_REGISTRY
    from ..core.extension_loader import load_extensions
    load_extensions(env, HANDLER_REGISTRY)
    return HANDLER_REGISTRY


def authorize_intent(env, intent_name, params):
    """Request-chain group gate; native model/record/scope checks remain mandatory."""
    from ..core.intent_operation_policy import is_write_intent
    registry = registered_handlers(env)
    handler_cls = registry.get(intent_name) or registry.get(intent_name.lower())
    if handler_cls is None:
        # Unknown intents are rejected by the router, never executed here.
        return None
    non_idempotent = bool(str(getattr(handler_cls, "NON_IDEMPOTENT_ALLOWED", "") or "").strip())
    return authorize_handler(env, handler_cls,
        require_declaration=is_write_intent(intent_name, params, non_idempotent=non_idempotent))
