# -*- coding: utf-8 -*-
"""Server-owned platform database selection contract.

The platform is a logical product boundary.  A separate physical database is
only enabled by an explicit non-production configuration; production is
fail-closed and colocated with the current business registry.
"""

from __future__ import annotations

import os
from typing import Any


PLATFORM_RELEASE_DB_PARAM = "smart_core.platform_release_db"
PRODUCTION_ENVIRONMENT = "production"


class PlatformDatabaseContractError(ValueError):
    """Raised when server-side platform database configuration is unsafe."""


def _text(value: Any) -> str:
    return str(value or "").strip()


def current_database_name(env) -> str:
    database = _text(getattr(getattr(env, "cr", None), "dbname", ""))
    if not database:
        raise PlatformDatabaseContractError("CURRENT_DATABASE_REQUIRED")
    return database


def configured_platform_database(env) -> str:
    try:
        return _text(env["ir.config_parameter"].sudo().get_param(PLATFORM_RELEASE_DB_PARAM, ""))
    except PlatformDatabaseContractError:
        raise
    except Exception as exc:
        raise PlatformDatabaseContractError("PLATFORM_RELEASE_DB_CONFIGURATION_UNAVAILABLE") from exc


def resolve_platform_database(
    env,
    *,
    environment: str | None = None,
    require_explicit: bool | None = None,
) -> str:
    """Resolve the platform database without accepting request-controlled input.

    Missing configuration never guesses a database name.  Development/test
    runtimes safely colocate with the current registry unless an independent
    database is explicitly configured.  Production requires an explicit value
    and rejects every cross-database target.
    """

    current = current_database_name(env)
    configured = configured_platform_database(env)
    runtime_environment = _text(environment if environment is not None else os.environ.get("SC_ENVIRONMENT"))
    production = runtime_environment == PRODUCTION_ENVIRONMENT
    explicit_required = production if require_explicit is None else bool(require_explicit)
    if not configured:
        if explicit_required:
            raise PlatformDatabaseContractError("PLATFORM_RELEASE_DB_REQUIRED")
        return current
    if production and configured != current:
        raise PlatformDatabaseContractError(
            f"PLATFORM_RELEASE_DB_MUST_MATCH_CURRENT:{current}"
        )
    return configured


def is_colocated_platform_database(env, *, environment: str | None = None) -> bool:
    return resolve_platform_database(env, environment=environment) == current_database_name(env)
