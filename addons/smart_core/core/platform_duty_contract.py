# -*- coding: utf-8 -*-
"""Declared platform-administration duty surface (ADR-007 D6).

The platform administrator's identity domain, capability list and default
landing are declared here once and consumed by the startup identity projection
and by ``GET /api/ops/platform-duty``.  Nothing in this module inspects the
database it happens to run in: platform versus tenant is decided by the caller
from the three checks in ``security/platform_admin.py`` (trusted instance,
token audience, current permission) and passed in as booleans.

The projection never exposes a physical database name.  Callers may pass the
immutable logical ``namespace_id`` (``ns_<12 hex>``); the database stays inside
the backend verification path.
"""

from __future__ import annotations

CONTRACT_VERSION = "1.0.0"

AUDIENCE_PLATFORM_CONTROL = "platform-admin"
AUDIENCE_TENANT = "tenant"
AUDIENCE_NONE = "none"

SOURCE = "platform_duty_contract"

PLATFORM_DUTIES = (
    {
        "key": "platform.home",
        "label": "平台首页",
        "description": "查看平台运行概览与各职责入口。",
        "capabilities": ("platform.home.open",),
        "scene_key": "workspace.home",
        "route": "/",
        "state": "available",
        "sequence": 10,
    },
    {
        "key": "platform.tenant_registry",
        "label": "租户登记表",
        "description": "查看已登记租户、入口别名与生命周期状态。",
        "capabilities": ("platform.tenant_registry.read",),
        "action_xmlid": "smart_core.action_sc_platform_namespace",
        "state": "available",
        "sequence": 20,
    },
    {
        "key": "platform.maintenance_access",
        "label": "维护访问",
        "description": "查看受控维护授权的审批、有效期与授权范围。",
        "capabilities": ("platform.maintenance_access.read",),
        "action_xmlid": "smart_core.action_sc_platform_maintenance_access",
        "state": "available",
        "sequence": 30,
    },
    {
        "key": "platform.job_status",
        "label": "运维任务",
        "description": "查看平台运维任务及最近执行结果。",
        "capabilities": ("platform.job_status.read",),
        "action_xmlid": "smart_core.action_sc_ops_job",
        "state": "available",
        "sequence": 40,
    },
    {
        "key": "platform.release_operator",
        "label": "发布运营",
        "description": "查看并管理产品发布、候选快照与回滚。",
        "capabilities": ("platform.release_operator.read",),
        "route": "/admin/release-operator",
        "state": "available",
        "sequence": 50,
    },
    {
        "key": "platform.subscription",
        "label": "订阅实例",
        "description": "查看租户订阅套餐与授权实例。",
        "capabilities": ("platform.subscription.write",),
        "action_xmlid": "smart_core.action_sc_subscription",
        "state": "available",
        "sequence": 60,
    },
)

TENANT_DUTIES = (
    {
        "key": "tenant.config.usage",
        "label": "用量分析",
        "capabilities": ("tenant.config.usage.read",),
        "route": "/admin/usage-analytics",
        "state": "available",
        "sequence": 10,
    },
    {
        "key": "tenant.config.catalogue",
        "label": "场景包管理",
        "capabilities": ("tenant.config.catalogue.read",),
        "route": "/admin/scene-packages",
        "state": "available",
        "sequence": 20,
    },
    {
        "key": "tenant.config.health",
        "label": "场景健康",
        "capabilities": ("tenant.config.health.read",),
        "route": "/admin/scene-health",
        "state": "available",
        "sequence": 30,
    },
)

DUTY_STATE_LABELS = {
    "available": "可用",
    "available_unverified": "待验证",
    "blocked": "不可用",
}

DEFAULT_LANDING = {
    "scene_key": "workspace.home",
    "route": "/",
    "source": SOURCE,
}

FORBIDDEN_PROJECTION_KEYS = ("db_name", "database_name", "trusted_instance", "trusted_instance_database")


def _duty_keys(duties) -> list[str]:
    return sorted(str(duty["key"]) for duty in duties)


def _capability_keys(duties) -> list[str]:
    return sorted({str(cap) for duty in duties for cap in duty.get("capabilities") or ()})


def declared_platform_duty_keys() -> list[str]:
    return _duty_keys(PLATFORM_DUTIES)


def declared_platform_capabilities() -> list[str]:
    return _capability_keys(PLATFORM_DUTIES)


def declared_tenant_duty_keys() -> list[str]:
    return _duty_keys(TENANT_DUTIES)


def declared_tenant_capabilities() -> list[str]:
    return _capability_keys(TENANT_DUTIES)


def declared_platform_action_xmlids() -> list[str]:
    """Window actions the platform duties bind to, resolved by the caller."""
    return sorted({str(duty["action_xmlid"]) for duty in PLATFORM_DUTIES if duty.get("action_xmlid")})


def build_platform_duty_route_authority_entries(*, env, surface: dict | None) -> list[dict]:
    """Project declared duty actions into executable route-authority entries.

    The platform-control instance publishes only the minimum navigation surface,
    so a duty that opens a window action has no native menu/action pair in the
    startup navigation.  The duty declaration is the authority for that route:
    when (and only when) the surface is the verified platform audience, resolve
    its declared ``action_xmlid`` and publish an ``ADMIN_ROUTE`` entry.  The
    entry carries ``menu_id = 0`` because the duty is not a navigation menu.

    Fail closed: an unresolvable or non-window action is skipped, leaving the
    duty without a route instead of inventing an action id or a fallback menu.
    """

    if not isinstance(surface, dict) or surface.get("audience") != AUDIENCE_PLATFORM_CONTROL:
        return []
    if env is None:
        return []
    entries: list[dict] = []
    seen: set[int] = set()
    for duty in surface.get("duties") or []:
        if not isinstance(duty, dict):
            continue
        action_xmlid = str(duty.get("action_xmlid") or "").strip()
        if not action_xmlid:
            continue
        try:
            action = env.ref(action_xmlid, raise_if_not_found=False)
        except Exception:
            action = None
        if not action or str(getattr(action, "_name", "")) != "ir.actions.act_window":
            continue
        action_id = int(getattr(action, "id", 0) or 0)
        if action_id <= 0 or action_id in seen:
            continue
        raw_view_modes = str(getattr(action, "view_mode", "") or "")
        view_modes = [item.strip() for item in raw_view_modes.split(",") if item.strip()]
        if not view_modes:
            continue
        seen.add(action_id)
        entries.append(
            {
                "route_kind": "ADMIN_ROUTE",
                "menu_id": 0,
                "menu_xmlid": "",
                "action_id": action_id,
                "action_xmlid": action_xmlid,
                "name": str(getattr(action, "name", "") or action_xmlid),
                "action_name": str(getattr(action, "name", "") or action_xmlid),
                "model": str(getattr(action, "res_model", "") or ""),
                "view_modes": view_modes,
                "view_id": int(getattr(getattr(action, "view_id", None), "id", 0) or 0),
                "domain": str(getattr(action, "domain", "") or "[]"),
                "context": str(getattr(action, "context", "") or "{}"),
                "route": "/a/%s" % action_id,
                "allowed_operation": "read",
                "required_capability": "platform_control",
                "context_requirements": {},
                "source": SOURCE,
            }
        )
    return entries


def merge_platform_duty_route_authority(authority: dict | None, *, env, surface: dict | None) -> dict:
    """Add declared platform duty actions to the executable admin-authority bucket."""

    if not isinstance(authority, dict):
        return authority or {}
    entries = build_platform_duty_route_authority_entries(env=env, surface=surface)
    if not entries:
        return authority
    merged = dict(authority)
    admin_actions = list(merged.get("admin_actions") or [])
    existing = {
        int(row.get("action_id") or 0)
        for row in admin_actions
        if isinstance(row, dict)
    }
    merged["admin_actions"] = admin_actions + [
        entry for entry in entries if entry["action_id"] not in existing
    ]
    return merged


def default_landing() -> dict:
    return dict(DEFAULT_LANDING)


def _project_duties(duties, action_routes=None) -> list[dict]:
    action_routes = action_routes or {}
    rows = []
    for duty in sorted(duties, key=lambda item: (int(item.get("sequence") or 0), str(item["key"]))):
        state = str(duty.get("state") or "available")
        row = {
            "key": str(duty["key"]),
            "label": str(duty.get("label") or duty["key"]),
            "description": str(duty.get("description") or ""),
            "capabilities": sorted(str(cap) for cap in duty.get("capabilities") or ()),
            "state": state,
            "state_label": DUTY_STATE_LABELS.get(state, state),
        }
        action_xmlid = str(duty.get("action_xmlid") or "")
        resolved_route = str(action_routes.get(action_xmlid) or "")
        route = resolved_route or str(duty.get("route") or "")
        if route:
            row["route"] = route
        if action_xmlid:
            row["action_xmlid"] = action_xmlid
        if duty.get("intent"):
            row["intent"] = str(duty["intent"])
        if duty.get("scene_key"):
            row["scene_key"] = str(duty["scene_key"])
        rows.append(row)
    return rows


def build_platform_duty_surface(
    *,
    is_platform_control_admin: bool,
    is_tenant_config_admin: bool,
    namespace_id: str | None = None,
    action_routes: dict | None = None,
) -> dict:
    """Project the declared duties for one verified identity (fail-closed).

    The two responsibilities are mutually exclusive: a platform-control
    identity holds the platform duties, a tenant configuration identity holds
    the tenant duties.  No caller can receive both.
    """

    if is_platform_control_admin:
        audience = AUDIENCE_PLATFORM_CONTROL
        duties = tuple(PLATFORM_DUTIES)
    elif is_tenant_config_admin:
        audience = AUDIENCE_TENANT
        duties = tuple(TENANT_DUTIES)
    else:
        audience = AUDIENCE_NONE
        duties = ()

    surface = {
        "audience": audience,
        "duty_keys": _duty_keys(duties),
        "capabilities": _capability_keys(duties),
        "duties": _project_duties(duties, action_routes=action_routes),
        "default_landing": default_landing() if is_platform_control_admin else None,
        "contract_version": CONTRACT_VERSION,
        "source": SOURCE,
        "trusted_instance_verified": bool(is_platform_control_admin),
        "namespace_id": str(namespace_id) if namespace_id else None,
    }
    return validate_surface(surface)


def validate_surface(surface: dict) -> dict:
    """Reject undeclared capabilities and physical identifiers (fail-closed)."""

    if not isinstance(surface, dict):
        raise ValueError("platform duty surface must be a mapping")
    for key in FORBIDDEN_PROJECTION_KEYS:
        if key in surface:
            raise ValueError("platform duty surface must not expose %s" % key)
    declared = set(declared_platform_capabilities()) | set(declared_tenant_capabilities())
    undeclared = sorted(set(surface.get("capabilities") or []) - declared)
    if undeclared:
        raise ValueError("undeclared platform capabilities: %s" % ",".join(undeclared))
    if str(surface.get("audience")) == AUDIENCE_PLATFORM_CONTROL and not surface.get("capabilities"):
        raise ValueError("platform-control surface must not be empty")
    return surface


PLATFORM_CAPABILITY_GROUP_KEY = "platform_control"
PLATFORM_CAPABILITY_GROUP_LABEL = "平台管理"
PLATFORM_CAPABILITY_GROUP_ICON = "shield"


def build_capability_rows(surface: dict) -> list[dict]:
    """Raw capability rows for the platform duty surface.

    The rows use the same field names as the product capability catalogue, so
    the caller normalises them with the existing capability helpers instead of
    inventing a second schema.  Only a platform-control audience produces rows;
    a tenant surface can never leak a ``platform.*`` capability this way.
    """

    if not isinstance(surface, dict) or surface.get("audience") != AUDIENCE_PLATFORM_CONTROL:
        return []
    rows = []
    for duty in surface.get("duties") or []:
        if not isinstance(duty, dict):
            continue
        state = str(duty.get("state") or "available")
        for capability in duty.get("capabilities") or []:
            row = {
                "key": str(capability),
                "name": str(duty.get("label") or duty.get("key") or ""),
                "ui_label": str(duty.get("label") or duty.get("key") or ""),
                "status": "ga" if state == "available" else "beta",
                "group_key": PLATFORM_CAPABILITY_GROUP_KEY,
                "group_label": PLATFORM_CAPABILITY_GROUP_LABEL,
                "group_icon": PLATFORM_CAPABILITY_GROUP_ICON,
                "group_sequence": 1,
                "state": "READY" if state == "available" else "PREVIEW",
                "tags": ["platform_duty"],
                "duty_key": str(duty.get("key") or ""),
            }
            payload = {}
            if duty.get("route"):
                payload["route"] = str(duty["route"])
            if duty.get("action_xmlid"):
                payload["action_xmlid"] = str(duty["action_xmlid"])
            if duty.get("intent"):
                payload["intent"] = str(duty["intent"])
            if duty.get("scene_key"):
                payload["scene_key"] = str(duty["scene_key"])
            if payload:
                row["default_payload"] = payload
            entry_target = {}
            if duty.get("scene_key"):
                entry_target["scene_key"] = str(duty["scene_key"])
                entry_target["route"] = str(duty.get("route") or "/")
            elif duty.get("route"):
                entry_target["route"] = str(duty["route"])
            if entry_target:
                row["entry_target"] = entry_target
            rows.append(row)
    return rows
