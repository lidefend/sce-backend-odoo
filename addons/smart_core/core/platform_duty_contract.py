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
        "capabilities": ("platform.home.open",),
        "scene_key": "workspace.home",
        "route": "/",
        "state": "available",
        "sequence": 10,
    },
    {
        "key": "platform.tenant_registry",
        "label": "租户登记表",
        "capabilities": ("platform.tenant_registry.read",),
        "route": "/api/ops/tenants",
        "state": "available",
        "sequence": 20,
    },
    {
        "key": "platform.maintenance_access",
        "label": "维护访问",
        "capabilities": ("platform.maintenance_access.read",),
        "route": "/api/ops/maintenance/access",
        "state": "available",
        "sequence": 30,
    },
    {
        "key": "platform.job_status",
        "label": "运维任务",
        "capabilities": ("platform.job_status.read",),
        "route": "/api/ops/job/status",
        "state": "available",
        "sequence": 40,
    },
    {
        "key": "platform.release_operator",
        "label": "发布运营",
        "capabilities": ("platform.release_operator.read",),
        "intent": "release.operator.surface",
        "state": "available",
        "sequence": 50,
    },
    {
        "key": "platform.subscription",
        "label": "订阅管理",
        "capabilities": ("platform.subscription.write",),
        "route": "/api/ops/subscription/set",
        "state": "available_unverified",
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


def default_landing() -> dict:
    return dict(DEFAULT_LANDING)


def _project_duties(duties) -> list[dict]:
    rows = []
    for duty in sorted(duties, key=lambda item: (int(item.get("sequence") or 0), str(item["key"]))):
        row = {
            "key": str(duty["key"]),
            "label": str(duty.get("label") or duty["key"]),
            "capabilities": sorted(str(cap) for cap in duty.get("capabilities") or ()),
            "state": str(duty.get("state") or "available"),
        }
        if duty.get("route"):
            row["route"] = str(duty["route"])
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
        "duties": _project_duties(duties),
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
