# -*- coding: utf-8 -*-
import logging
import time

from odoo import fields
from odoo.exceptions import AccessDenied, AccessError, ValidationError

from ..core.base_handler import BaseIntentHandler
from ..core.handler_registry import HANDLER_REGISTRY
from ..security.auth import (
    _get_secret_key,
    generate_token,
    get_principal_from_token,
)
from ..security.credential_service import (
    AUTH_METHOD_PASSWORD,
    MACHINE_TOKEN_TTL_SECONDS,
    authenticate_api_key,
    issue_machine_api_key,
    record_machine_token_issued,
    revoke_machine_api_key,
    rotate_machine_api_key,
    synchronize_expired_policies,
)

_logger = logging.getLogger(__name__)


def _datetime_text(value):
    return fields.Datetime.to_string(value) if value else False


def _trace_id(ctx):
    if isinstance(ctx, dict):
        return str(ctx.get("trace_id") or "")
    return str(getattr(ctx, "trace_id", "") or "") if ctx else ""


def _policy_payload(policy):
    return {
        "credential_id": policy.credential_id,
        "name": policy.name,
        "state": policy.state,
        "scope": list(policy.scope_values()),
        "company_ids": policy.company_ids.ids,
        "expires_at": _datetime_text(policy.expires_at),
        "last_used_at": _datetime_text(policy.last_used_at),
        "usage_count": int(policy.usage_count or 0),
        "created_at": _datetime_text(policy.create_date),
        "rotated_from_credential_id": policy.rotated_from_id.credential_id if policy.rotated_from_id else "",
    }


class _CredentialManagementBase(BaseIntentHandler):
    REQUIRED_GROUPS = ["base.group_user"]
    ACL_MODE = "explicit_check"

    def _current_human(self):
        principal = get_principal_from_token()
        if principal.get("auth_method") != AUTH_METHOD_PASSWORD or principal.get("principal_type") != "human":
            raise AccessError("machine credentials cannot manage credentials")
        return principal["user"]

    def _policy(self, credential_id):
        policy = self.env["sc.auth.credential.policy"].search([
            ("credential_id", "=", str(credential_id or "").strip()),
            ("user_id", "=", self.env.user.id),
        ], limit=1)
        if not policy:
            raise AccessError("credential is unavailable")
        return policy


class AuthCredentialListHandler(_CredentialManagementBase):
    INTENT_TYPE = "auth.credential.list"
    DESCRIPTION = "List non-secret API-key policy projections"

    def handle(self, payload=None, ctx=None):
        user = self._current_human()
        synchronize_expired_policies(
            self.env,
            user_id=user.id,
            trace_id=_trace_id(ctx),
        )
        rows = self.env["sc.auth.credential.policy"].search([("user_id", "=", user.id)])
        return {
            "ok": True,
            "data": {"credentials": [_policy_payload(row) for row in rows], "secret_returned": False},
            "meta": {},
        }


class AuthCredentialCreateHandler(_CredentialManagementBase):
    INTENT_TYPE = "auth.credential.create"
    DESCRIPTION = "Create an Odoo-native machine API key and restrictive policy"

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        confirmation = params.get("credential") if isinstance(params.get("credential"), dict) else {}
        if confirmation.get("type") != "password":
            return self.err(400, "credential.type 必须为 password")
        password = confirmation.get("secret")
        try:
            policy, secret = issue_machine_api_key(
                self.env,
                actor_user=self._current_human(),
                password=password,
                name=params.get("name"),
                scopes=params.get("scope"),
                company_ids=params.get("company_ids"),
                expires_at=params.get("expires_at"),
                trace_id=_trace_id(ctx),
            )
        except (AccessDenied, AccessError, ValidationError):
            return self.err(403, "凭据创建被拒绝")
        return {
            "ok": True,
            "data": {
                "credential": _policy_payload(policy),
                "api_key": secret,
                "secret_display": "once",
                "machine_exchange_intent": "auth.machine.token",
            },
            "meta": {
                "evidence_policy": {
                    "classification": "one_time_secret",
                    "secret_fields": ["data.api_key"],
                    "browser_capture": "forbidden_while_visible",
                },
            },
        }


class AuthCredentialRevokeHandler(_CredentialManagementBase):
    INTENT_TYPE = "auth.credential.revoke"
    DESCRIPTION = "Revoke an Odoo-native API key and all bound machine sessions"

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        try:
            policy = revoke_machine_api_key(
                self.env,
                policy=self._policy(params.get("credential_id")),
                actor_user=self._current_human(),
                trace_id=_trace_id(ctx),
            )
        except (AccessDenied, AccessError, ValidationError):
            return self.err(403, "凭据撤销被拒绝")
        return {
            "ok": True,
            "data": {"credential": _policy_payload(policy), "sessions_invalidated": True},
            "meta": {},
        }


class AuthCredentialRotateHandler(_CredentialManagementBase):
    INTENT_TYPE = "auth.credential.rotate"
    DESCRIPTION = "Rotate an Odoo-native API key with one-time secret delivery"

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        confirmation = params.get("credential") if isinstance(params.get("credential"), dict) else {}
        if confirmation.get("type") != "password":
            return self.err(400, "credential.type 必须为 password")
        try:
            replacement, secret = rotate_machine_api_key(
                self.env,
                policy=self._policy(params.get("credential_id")),
                actor_user=self._current_human(),
                password=confirmation.get("secret"),
                trace_id=_trace_id(ctx),
            )
        except (AccessDenied, AccessError, ValidationError):
            return self.err(403, "凭据轮换被拒绝")
        return {
            "ok": True,
            "data": {
                "credential": _policy_payload(replacement),
                "api_key": secret,
                "secret_display": "once",
                "predecessor_revoked": True,
            },
            "meta": {
                "evidence_policy": {
                    "classification": "one_time_secret",
                    "secret_fields": ["data.api_key"],
                    "browser_capture": "forbidden_while_visible",
                },
            },
        }


class AuthMachineTokenHandler(BaseIntentHandler):
    INTENT_TYPE = "auth.machine.token"
    DESCRIPTION = "Exchange an explicit Odoo API key for a short scoped machine JWT"

    def handle(self, payload=None, ctx=None):
        params = self.params if isinstance(self.params, dict) else {}
        credential = params.get("credential") if isinstance(params.get("credential"), dict) else {}
        if credential.get("type") != "api_key":
            return self.err(400, "credential.type 必须为 api_key")
        request_database = str(getattr(self.env.cr, "dbname", "") or "").strip()
        database = str(params.get("db") or request_database).strip()
        if not request_database or database != request_database:
            return self.err(401, "机器凭据无效或不可用")
        try:
            httprequest = getattr(self.request, "httprequest", None)
            client_identity = str(
                getattr(httprequest, "remote_addr", "")
                or (getattr(httprequest, "environ", {}) or {}).get("REMOTE_ADDR")
                or "unknown"
            ).strip()
            principal = authenticate_api_key(
                database=database,
                secret=credential.get("secret"),
                requested_scopes=credential.get("requested_scope"),
                fingerprint_pepper=_get_secret_key(),
                client_identity=client_identity,
            )
        except (AccessDenied, AccessError, ValidationError):
            return self.err(401, "机器凭据无效或不可用")
        except Exception:
            _logger.exception(
                "Machine credential exchange failed closed on database %s",
                request_database,
            )
            return self.err(401, "机器凭据无效或不可用")
        token = generate_token(
            principal=principal,
            expires_in=MACHINE_TOKEN_TTL_SECONDS,
        )
        record_machine_token_issued(
            self.env,
            principal=principal,
            trace_id=_trace_id(ctx),
        )
        return {
            "ok": True,
            "data": {
                "session": {
                    "token": token,
                    "token_type": "Bearer",
                    "expires_at": int(time.time()) + MACHINE_TOKEN_TTL_SECONDS,
                    "db": principal.database,
                },
                "principal": {
                    "type": principal.principal_type,
                    "auth_method": principal.auth_method,
                    "credential_id": principal.credential_id,
                    "scope": list(principal.scopes),
                    "user_id": principal.user_id,
                    "company_id": principal.company_id,
                    "allowed_company_ids": list(principal.allowed_company_ids),
                },
            },
            "meta": {},
        }


for handler in (
    AuthCredentialListHandler,
    AuthCredentialCreateHandler,
    AuthCredentialRevokeHandler,
    AuthCredentialRotateHandler,
    AuthMachineTokenHandler,
):
    HANDLER_REGISTRY.setdefault(handler.INTENT_TYPE, handler)
