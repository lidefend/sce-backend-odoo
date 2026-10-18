# -*- coding: utf-8 -*-
"""Path namespace resolution and entry-contract verification (ADR-007 batch C).

Two layers, one authority:

* the entry (nginx) turns the path prefix into ``X-SC-Namespace`` and strips any
  client database hint, then stamps the shared-secret and route-version headers;
* Odoo verifies those headers, resolves the alias to an immutable
  ``namespace_id``, and refuses any request whose claimed namespace disagrees
  with the instance it actually reached.

Nothing here reads ``X-Odoo-DB`` / ``X-DB`` / ``?db``: those are client hints and
must never select a database again.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from .namespace_errors import (
    EntrySignatureInvalid,
    NamespaceRequired,
    NamespaceTargetMismatch,
    RouteVersionMismatch,
)

PATH_NAMESPACE = re.compile(r"^/t/(?P<alias>[a-z0-9][a-z0-9-]{0,62})(?:/|$)")
PLATFORM_PATH = re.compile(r"^/platform-admin(?:/|$)")

AUDIENCE_PLATFORM = "platform-admin"
AUDIENCE_TENANT = "tenant"

HEADER_NAMESPACE = "X-SC-Namespace"
HEADER_AUDIENCE = "X-SC-Audience"
HEADER_ROUTE_VERSION = "X-SC-Route-Version"
HEADER_ENTRY_SECRET = "X-SC-Entry-Secret"

SHARED_SECRET_PARAM = "sc.entry.shared_secret"
ROUTE_VERSION_PARAM = "sc.entry.route_version"
SHARED_SECRET_ENV = "SC_ENTRY_SHARED_SECRET"
ROUTE_VERSION_ENV = "SC_ENTRY_ROUTE_VERSION"


@dataclass(frozen=True)
class EntryContext:
    alias: str
    audience: str
    route_version: str


@dataclass(frozen=True)
class NamespaceRef:
    namespace_id: str
    alias: str
    database_name: str
    duty_key: str
    audience: str
    lifecycle_state: str


def parse_path_namespace(path: str) -> str:
    """Return the namespace alias a public path names, or "" when it names none."""

    value = str(path or "")
    platform = PLATFORM_PATH.match(value)
    if platform:
        return "platform"
    match = PATH_NAMESPACE.match(value)
    return match.group("alias") if match else ""


def audience_for_alias(alias: str) -> str:
    return AUDIENCE_PLATFORM if str(alias or "") == "platform" else AUDIENCE_TENANT


def _header(headers, name: str) -> str:
    if not headers:
        return ""
    try:
        value = headers.get(name)
    except AttributeError:
        value = None
    if value:
        return str(value).strip()
    lowered = name.lower()
    try:
        for key, candidate in headers.items():
            if str(key).lower() == lowered:
                return str(candidate or "").strip()
    except AttributeError:
        pass
    return ""


def declared_namespace(headers) -> str:
    """The namespace alias the entry stamped on this request, or ""."""

    return _header(headers, HEADER_NAMESPACE)


def _config(env, param: str, envvar: str) -> str:
    if env is not None:
        try:
            value = str(env["ir.config_parameter"].sudo().get_param(param, "") or "").strip()
        except Exception:
            value = ""
        if value:
            return value
    return str(os.environ.get(envvar, "") or "").strip()


def verify_entry_headers(headers, *, expected_secret: str, expected_version: str) -> EntryContext:
    """Validate the entry stamp; every missing piece is a hard rejection."""

    alias = declared_namespace(headers)
    if not alias:
        raise NamespaceRequired("the entry did not resolve a namespace for this path")
    secret = _header(headers, HEADER_ENTRY_SECRET)
    if not expected_secret:
        raise EntrySignatureInvalid("entry shared secret is not configured")
    if secret != expected_secret:
        raise EntrySignatureInvalid("entry shared secret mismatch")
    supplied_version = _header(headers, HEADER_ROUTE_VERSION)
    if expected_version and supplied_version != expected_version:
        raise RouteVersionMismatch(
            "route version %s does not match %s" % (supplied_version or "<unset>", expected_version)
        )
    audience = _header(headers, HEADER_AUDIENCE) or audience_for_alias(alias)
    if audience != audience_for_alias(alias):
        raise EntrySignatureInvalid("entry audience disagrees with the namespace")
    return EntryContext(alias=alias, audience=audience, route_version=supplied_version)


def entry_context_from_headers(env, headers) -> EntryContext:
    return verify_entry_headers(
        headers,
        expected_secret=_config(env, SHARED_SECRET_PARAM, SHARED_SECRET_ENV),
        expected_version=_config(env, ROUTE_VERSION_PARAM, ROUTE_VERSION_ENV),
    )


def _to_ref(record, alias: str) -> NamespaceRef:
    return NamespaceRef(
        namespace_id=str(record.namespace_id),
        alias=alias,
        database_name=str(record.database_name),
        duty_key=str(record.duty_key),
        audience=str(record.audience),
        lifecycle_state=str(record.lifecycle_state),
    )


def _instance_database(env) -> str:
    try:
        return str(env.cr.dbname or "")
    except Exception:
        return ""


def _assert_target(env, record) -> None:
    """Fail closed when the resolved namespace does not belong to this instance.

    The registry seed may describe every namespace in every database.  Without
    this check a demo instance that receives the platform alias could resolve a
    row naming ``sc_platform_control`` and then open that registry.  The
    instance identity is therefore always compared against the binding.
    """

    instance_database = _instance_database(env)
    bound_database = str(getattr(record, "database_name", "") or "")
    if not instance_database or bound_database != instance_database:
        raise NamespaceTargetMismatch(
            "namespace %s binds %s but this instance serves %s"
            % (
                str(getattr(record, "namespace_id", "") or "<unknown>"),
                bound_database or "<unset>",
                instance_database or "<unset>",
            )
        )


def resolve_entry(env, headers) -> NamespaceRef:
    """Entry-driven resolution: header alias -> immutable namespace."""

    context = entry_context_from_headers(env, headers)
    record = env["sc.platform.namespace"].sudo().resolve_alias(context.alias)
    if str(record.audience) != context.audience:
        raise EntrySignatureInvalid("namespace audience does not match the entry audience")
    _assert_target(env, record)
    return _to_ref(record, context.alias)


def resolve_instance(env) -> NamespaceRef:
    """Instance-driven resolution for internal callers without entry headers."""

    database = _instance_database(env)
    record = env["sc.platform.namespace"].sudo().resolve_for_database(database)
    _assert_target(env, record)
    return _to_ref(record, "instance")
