# -*- coding: utf-8 -*-
"""Administration responsibility checks owned by smart_core.

Two distinct responsibilities live here and must not be conflated:

``user_is_tenant_config_admin``
    Configuration administration inside the database the request already runs
    against.  This is the pre-batch-B group decision and it is what every
    product, industry, navigation, write-intent and portal surface must use.

``user_is_platform_control_admin``
    ADR-007 D6 platform-administration identity: group **and** the declared
    platform-control instance **and** the batch-C audience seam.  Only platform
    control APIs and the platform data plane may use it.
"""

from __future__ import annotations

import os

PLATFORM_ADMIN_GROUP = "smart_core.group_smart_core_admin"
PLATFORM_CONFIGURATION_ADMIN_GROUP = PLATFORM_ADMIN_GROUP
SECURITY_ADMIN_GROUP = "smart_core.group_smart_core_security_admin"
SYSTEM_ADMIN_GROUP = "base.group_system"
BREAK_GLASS_TECHNICAL_ADMIN_GROUP = SYSTEM_ADMIN_GROUP

# ADR-007 D6: a platform-administration identity only exists inside the
# declared platform-control instance.  The declaration is a governance fact
# (``docs/governance/database_architecture_policy.md``), not something inferred
# from whichever database the request happens to reach.
DECLARED_PLATFORM_CONTROL_DB = "sc_platform_control"
PLATFORM_CONTROL_DB_PARAM = "sc.platform.control_db"
PLATFORM_CONTROL_DB_ENV = "SC_PLATFORM_CONTROL_DB"

# Batch C hook: once the namespace resolver exists, the platform-admin token
# audience is bound here.  It stays unbound in batch B on purpose so that no
# caller can mistake group membership for a namespace-scoped identity.
PLATFORM_ADMIN_IDENTITY_AUDIENCE = None

CAPABILITY_DISCOVERY_ADMIN_GROUPS = (
    PLATFORM_CONFIGURATION_ADMIN_GROUP,
)


def platform_admin_group_xmlids(*, include_system: bool = False) -> list[str]:
    xmlids = [PLATFORM_ADMIN_GROUP]
    if include_system:
        xmlids.append(SYSTEM_ADMIN_GROUP)
    return xmlids


def _database_name(env) -> str:
    """Return the database this environment is bound to, or an empty string."""

    if env is None:
        return ""
    try:
        return str(env.cr.dbname or "").strip()
    except Exception:
        return ""


def declared_platform_control_dbname(env=None) -> str:
    """Return the declared platform-control database name.

    Precedence: database parameter -> process environment -> governance
    constant.  The value is a declaration, never a guess derived from the
    connected database.
    """

    if env is not None:
        try:
            value = str(
                env["ir.config_parameter"].sudo().get_param(PLATFORM_CONTROL_DB_PARAM, "") or ""
            ).strip()
        except Exception:
            value = ""
        if value:
            return value
    value = str(os.environ.get(PLATFORM_CONTROL_DB_ENV, "") or "").strip()
    return value or DECLARED_PLATFORM_CONTROL_DB


def is_declared_platform_control_database(dbname, env=None) -> bool:
    """Return whether ``dbname`` is the declared platform-control database."""

    current = str(dbname or "").strip()
    if not current:
        return False
    return current == declared_platform_control_dbname(env)


def platform_instance_scope(env=None) -> dict:
    """Describe the instance a request is running against."""

    database = _database_name(env)
    declared = declared_platform_control_dbname(env)
    return {
        "database": database,
        "declared_platform_control_db": declared,
        "is_platform_control_instance": bool(database) and database == declared,
    }


def _identity_audience_allows(identity_audience) -> bool:
    """Batch C seam for token identity-domain/audience checks.

    ``None`` means the caller did not supply an audience: batch B keeps the
    group+instance checks and does not pretend an audience was verified.  A
    supplied audience is only accepted once a declared audience exists.
    """

    if identity_audience is None:
        return True
    declared = PLATFORM_ADMIN_IDENTITY_AUDIENCE
    if not declared:
        return False
    return str(identity_audience).strip() == str(declared).strip()


def platform_control_scope(
    user,
    *,
    include_system: bool = False,
    env=None,
    identity_audience=None,
) -> dict:
    """Return every component of the platform-control decision.

    Platform control requires the group check **and** the declared
    platform-control instance.  Namespace isolation is not implemented in this
    batch: ``identity_audience`` is only a seam for batch C.
    """

    resolved_env = env if env is not None else getattr(user, "env", None)
    group_ok = _user_has_any_group(user, platform_admin_group_xmlids(include_system=include_system))
    instance = platform_instance_scope(resolved_env)
    audience_ok = _identity_audience_allows(identity_audience)
    return {
        "user_id": getattr(user, "id", None) if user else None,
        "group_ok": group_ok,
        "instance_ok": instance["is_platform_control_instance"],
        "database": instance["database"],
        "declared_platform_control_db": instance["declared_platform_control_db"],
        "identity_audience": identity_audience,
        "declared_identity_audience": PLATFORM_ADMIN_IDENTITY_AUDIENCE,
        "audience_ok": audience_ok,
        "is_platform_control_admin": bool(
            group_ok and instance["is_platform_control_instance"] and audience_ok
        ),
    }


# Historical name kept for callers that have not migrated; identical contract.
platform_admin_scope = platform_control_scope


def user_is_platform_control_admin(
    user,
    *,
    include_system: bool = False,
    env=None,
    identity_audience=None,
) -> bool:
    """Return whether ``user`` holds platform control on this instance."""

    if not user:
        return False
    scope = platform_control_scope(
        user,
        include_system=include_system,
        env=env,
        identity_audience=identity_audience,
    )
    return bool(scope["is_platform_control_admin"])


def tenant_config_scope(user, *, include_system: bool = False, env=None) -> dict:
    """Describe tenant-scoped configuration administration.

    ``has_group`` is answered by the database the user's environment is bound
    to, so the decision is inherently scoped to the current tenant database.
    It grants no platform-control authority (ADR-007 D6).
    """

    resolved_env = env if env is not None else getattr(user, "env", None)
    group_ok = _user_has_any_group(
        user, platform_admin_group_xmlids(include_system=include_system)
    )
    return {
        "user_id": getattr(user, "id", None) if user else None,
        "group_ok": group_ok,
        "database": _database_name(resolved_env),
        "is_tenant_config_admin": group_ok,
    }


def user_is_tenant_config_admin(user, *, include_system: bool = False, env=None) -> bool:
    """Return whether ``user`` configures the current tenant instance.

    This is the pre-batch-B semantics, restored explicitly: the group check
    evaluated in the current database.  It must not be used as evidence of
    platform-control authority.
    """

    if not user:
        return False
    return bool(tenant_config_scope(user, include_system=include_system, env=env)["is_tenant_config_admin"])


def user_is_platform_admin(
    user,
    *,
    include_system: bool = False,
    env=None,
    identity_audience=None,
) -> bool:
    """Deprecated explicit alias of :func:`user_is_platform_control_admin`.

    Kept only for historical imports from the industry facade module and from
    older callers.  It never means "group means platform administrator".
    """

    return user_is_platform_control_admin(
        user,
        include_system=include_system,
        env=env,
        identity_audience=identity_audience,
    )


def platform_admin_groups(env, *, include_system: bool = False):
    groups = []
    for xmlid in platform_admin_group_xmlids(include_system=include_system):
        group = env.ref(xmlid, raise_if_not_found=False)
        if group:
            groups.append(group)
    return groups


def _user_has_any_group(user, group_xmlids) -> bool:
    if not user:
        return False
    for xmlid in group_xmlids:
        try:
            if user.has_group(xmlid):
                return True
        except Exception:
            continue
    return False


def can_discover_platform_capabilities(user) -> bool:
    """Return whether the user may discover installed product capabilities.

    This is a navigation/configuration visibility decision only.  It must not
    be used as evidence of customer business-record access.
    """

    return _user_has_any_group(user, CAPABILITY_DISCOVERY_ADMIN_GROUPS)


def can_manage_system_configuration(user) -> bool:
    """Return whether system configuration entry points should be visible."""

    return _user_has_any_group(user, CAPABILITY_DISCOVERY_ADMIN_GROUPS)


def user_is_security_admin(user) -> bool:
    """Return whether the user has the independent security-admin identity."""

    return _user_has_any_group(user, (SECURITY_ADMIN_GROUP,))


def user_is_break_glass_technical_admin(user) -> bool:
    """Return whether the user holds Odoo's controlled technical-admin role."""

    return _user_has_any_group(user, (BREAK_GLASS_TECHNICAL_ADMIN_GROUP,))


def has_customer_business_data_scope(user) -> bool:
    """Fail closed for scope inferred only from an administrator identity.

    Customer data scope is established by model ACLs, record rules, company
    scope and explicit business membership, never by these administrator
    identity groups alone.
    """

    del user
    return False
