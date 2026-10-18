# -*- coding: utf-8 -*-
"""Platform maintenance-authorization product entry (P0).

Owner ruling (2026-10-16): the authorization flow must be a product capability,
not a one-off shell substitute.  This controller is the entry for requesting,
approving, rejecting, revoking, expiring and querying a maintenance access over
``sc.platform.maintenance.access``.

Two boundaries are deliberate:

* **the decider is never taken from the request body.**  The approving identity
  is the principal verified from the authenticated session or token, and a body
  that carries a decider or a state field is refused rather than silently
  ignored.  A caller therefore cannot approve its own request by naming someone
  else, and independence stays a server-side fact;
* **the state machine is the only writer.**  This controller never writes the
  authorization record.  Requesting creates a ``requested`` row that authorizes
  nothing, and every later transition goes through the model's audited state
  machine, so no entry can rewrite the operator identity, the payload digest or
  the authorized operation set after the fact.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

from odoo import http
from odoo.exceptions import AccessDenied, AccessError, UserError, ValidationError
from odoo.http import request

from odoo.addons.smart_core.core.trace import get_trace_id
from odoo.addons.smart_core.security.auth import get_principal_from_token
from odoo.addons.smart_core.security.platform_admin import (
    user_is_platform_control_admin,
    user_is_security_admin,
)

CONTRACT_VERSION = "v1"
MODEL = "sc.platform.maintenance.access"

#: Fields a caller must never supply: the decider identity and the state are
#: server facts.  Refusing them is stronger than ignoring them, because a body
#: that names an approver is a caller trying to hand itself the authority.
FORBIDDEN_BODY_FIELDS = (
    "approved_by",
    "approved_by_id",
    "requested_by",
    "requested_by_id",
    "state",
    "valid_from",
    "valid_until",
)


def _json_response(payload: dict[str, Any], status: int = 200):
    return request.make_response(
        json.dumps(payload, ensure_ascii=False, default=str),
        headers=[("Content-Type", "application/json; charset=utf-8")],
        status=status,
    )


def _trace_id() -> str:
    """Read the trace id from the live request headers.

    ``get_trace_id`` projects the request headers and falls back to a fresh id;
    it must never be called without them, or every response - including the
    refusal envelope - would fail before it could report the actual outcome.
    """
    httprequest = getattr(request, "httprequest", None)
    headers = getattr(httprequest, "headers", None) or {}
    return get_trace_id(headers)


def _envelope(ok: bool, payload: dict[str, Any], trace_id: str) -> dict[str, Any]:
    envelope = {
        "ok": ok,
        "contract_version": CONTRACT_VERSION,
        "server_time": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "trace_id": trace_id,
        "warnings": [],
    }
    envelope.update(payload)
    return envelope


def _ok(data: Any):
    return _json_response(_envelope(True, {"data": data}, _trace_id()))


def _fail(code: str, message: str, *, http_status: int, details: dict[str, Any] | None = None):
    trace_id = _trace_id()
    return _json_response(
        _envelope(
            False,
            {
                "error": {
                    "code": str(code),
                    "message": message,
                    "details": details or {},
                    "trace_id": trace_id,
                }
            },
            trace_id,
        ),
        status=http_status,
    )


def _body() -> dict[str, Any]:
    payload = request.httprequest.get_json(force=True, silent=True) or {}
    if not isinstance(payload, dict):
        raise ValidationError("MAINTENANCE_ACCESS_BODY_NOT_AN_OBJECT")
    supplied = sorted(field for field in FORBIDDEN_BODY_FIELDS if field in payload)
    if supplied:
        raise AccessError("MAINTENANCE_ACCESS_SERVER_OWNED_FIELD:%s" % (",".join(supplied),))
    return payload


def _env(*, decider: bool):
    """Resolve the verified principal and the env it acts in.

    A caller that may only read is refused the decision entries, and the model
    re-asserts the decider identity and the independence rule on top of this, so
    the boundary does not rest on this single check.
    """
    principal = get_principal_from_token()
    user = principal["user"]
    allowed = user_is_security_admin(user) if decider else (
        user_is_platform_control_admin(user) or user_is_security_admin(user)
    )
    if not allowed:
        raise AccessDenied("insufficient permissions")
    return principal, request.env(user=user)


def _principal_facts(principal: dict) -> dict[str, Any]:
    user = principal["user"]
    # The decider identity is reported so an audit can bind it, and it is never
    # accepted as an input.
    return {
        "principal_login": user.login,
        "principal_uid": user.id,
        "auth_method": principal.get("auth_method") or "",
        "principal_type": principal.get("principal_type") or "",
        "is_security_admin": user_is_security_admin(user),
        "is_platform_admin": user_is_platform_control_admin(user),
    }


#: Governed refusals already speak in stable codes (``DBGOV1_...``,
#: ``DATABASE_GOVERNANCE_...``, ``MAINTENANCE_ACCESS_...``).  The envelope
#: reports that code verbatim so a caller can branch on the refusal instead of
#: matching prose, which would make the entry the only place the vocabulary is
#: not machine-readable.
GOVERNED_CODE = re.compile(r"[A-Z][A-Z0-9_]{3,}")


def _refusal_code(exc: Exception) -> str:
    head = str(exc).strip().split(":", 1)[0].strip()
    return head if GOVERNED_CODE.fullmatch(head) else "MAINTENANCE_ACCESS_REFUSED"


def _dispatch(handler: Callable[[dict, dict], dict], *, decider: bool):
    try:
        principal, env = _env(decider=decider)
        data = handler(env, _body()) if request.httprequest.method == "POST" else handler(env, {})
        return _ok({**data, **_principal_facts(principal)})
    except AccessDenied as exc:
        return _fail("PERMISSION_DENIED", str(exc), http_status=403)
    except (AccessError, ValidationError, UserError) as exc:
        # A governance refusal must answer with a governance code, whatever
        # layer raised it.
        return _fail(_refusal_code(exc), str(exc), http_status=400)
    except PermissionError as exc:
        # ``PermissionError`` is the standard-library form a governor may raise,
        # but it is also what an unrelated layer may raise for a defect.  Only a
        # refusal that speaks in a governed code is answered as a refusal; any
        # other one is a server error and is reported like one, without echoing
        # the internal text.
        code = _refusal_code(exc)
        if code == "MAINTENANCE_ACCESS_REFUSED":
            return _fail("SERVER_ERROR", "Internal server error", http_status=500)
        return _fail(code, str(exc), http_status=400)
    except Exception:  # noqa: BLE001 - the boundary reports, never guesses
        # The boundary never echoes internal exception text to a client: the
        # message could carry database, path or identity detail, and a caller
        # learns nothing they need from it.
        return _fail("SERVER_ERROR", "Internal server error", http_status=500)


class PlatformMaintenanceAccessController(http.Controller):
    @http.route("/api/ops/maintenance/access", type="http", auth="public", methods=["GET"], csrf=False)
    def list_access(self, **params):
        def handler(env, _body):
            records = env[MODEL].access_projection(
                db_name=params.get("db_name") or None,
                state=params.get("state") or None,
                limit=params.get("limit") or 0,
            )
            return {"accesses": records, "count": len(records)}

        return _dispatch(handler, decider=False)

    @http.route("/api/ops/maintenance/access/request", type="http", auth="public", methods=["POST"], csrf=False)
    def request_access(self, **params):
        def handler(env, body):
            readback = env[MODEL].request_access(
                body.get("db_name"),
                body.get("capability"),
                body.get("reason"),
                body.get("evidence_reference"),
                body.get("operator_identity_key") or "",
                body.get("subject_checksum") or "",
                body.get("authorized_operations"),
            )
            return {"access": readback}

        return _dispatch(handler, decider=False)

    @http.route("/api/ops/maintenance/access/approve", type="http", auth="public", methods=["POST"], csrf=False)
    def approve_access(self, **params):
        def handler(env, body):
            return {
                "access": env[MODEL].approve_access(
                    body.get("access_id"), body.get("validity_hours")
                )
            }

        return _dispatch(handler, decider=True)

    @http.route("/api/ops/maintenance/access/reject", type="http", auth="public", methods=["POST"], csrf=False)
    def reject_access(self, **params):
        def handler(env, body):
            return {
                "access": env[MODEL].reject_access(
                    body.get("access_id"), body.get("note") or ""
                )
            }

        return _dispatch(handler, decider=True)

    @http.route("/api/ops/maintenance/access/revoke", type="http", auth="public", methods=["POST"], csrf=False)
    def revoke_access(self, **params):
        def handler(env, body):
            return {
                "access": env[MODEL].revoke_access(
                    body.get("access_id"), body.get("note") or ""
                )
            }

        return _dispatch(handler, decider=True)

    @http.route("/api/ops/maintenance/access/expire", type="http", auth="public", methods=["POST"], csrf=False)
    def expire_accesses(self, **params):
        def handler(env, body):
            readbacks = env[MODEL].expire_accesses(body.get("db_name") or None)
            return {"expired": readbacks, "count": len(readbacks)}

        return _dispatch(handler, decider=True)
