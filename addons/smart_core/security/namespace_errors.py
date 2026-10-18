# -*- coding: utf-8 -*-
"""Stable, machine-readable namespace errors (ADR-007 batch C).

Every rejection carries a code the acceptance runner can assert.  The mapping
from code to HTTP status is fixed here so no controller invents its own.
"""

from __future__ import annotations


class NamespaceError(Exception):
    """Base class for every namespace rejection."""

    code = "NS_NAMESPACE_ERROR"
    http_status = 400

    def __init__(self, message: str = ""):
        super().__init__(message or self.code)
        self.message = message or self.code

    def payload(self, trace_id: str | None = None, route_version: str | None = None) -> dict:
        body = {"error": self.code, "message": self.message}
        if trace_id:
            body["trace_id"] = trace_id
        if route_version:
            body["route_version"] = route_version
        return body


class NamespaceRequired(NamespaceError):
    code = "NS_NAMESPACE_REQUIRED"
    http_status = 400


class UnknownNamespace(NamespaceError):
    code = "NS_UNKNOWN_NAMESPACE"
    http_status = 404


class NamespaceSuspended(NamespaceError):
    code = "NS_NAMESPACE_SUSPENDED"
    http_status = 403


class NamespaceConflict(NamespaceError):
    code = "NS_NAMESPACE_CONFLICT"
    http_status = 409


class NamespaceAmbiguous(NamespaceError):
    code = "NS_NAMESPACE_AMBIGUOUS"
    http_status = 409


class DatabaseHintConflict(NamespaceError):
    code = "NS_DATABASE_HINT_CONFLICT"
    http_status = 409


class EntrySignatureInvalid(NamespaceError):
    code = "NS_NAMESPACE_SIGNATURE_INVALID"
    http_status = 401


class RouteVersionMismatch(NamespaceError):
    code = "NS_ROUTE_VERSION_MISMATCH"
    http_status = 503


class TokenNamespaceMismatch(NamespaceError):
    code = "NS_TOKEN_NAMESPACE_MISMATCH"
    http_status = 401


class TokenAudienceMismatch(NamespaceError):
    code = "NS_TOKEN_AUDIENCE_MISMATCH"
    http_status = 401


class NamespaceTargetMismatch(NamespaceError):
    """The alias resolved a namespace bound to a different database than this instance."""

    code = "NS_NAMESPACE_TARGET_MISMATCH"
    http_status = 421


class PlatformAdminRequired(NamespaceError):
    code = "NS_PLATFORM_ADMIN_REQUIRED"
    http_status = 403


class UpstreamUnavailable(NamespaceError):
    code = "NS_UPSTREAM_UNAVAILABLE"
    http_status = 503
