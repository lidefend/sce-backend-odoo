# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
from dataclasses import dataclass, replace
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import AccessDenied, AccessError, ValidationError
from odoo.modules.registry import Registry

from ..models.auth_credential_policy import MACHINE_NATIVE_SCOPE, SERVICE_CONTEXT_KEY


AUTH_METHOD_PASSWORD = "password"
AUTH_METHOD_API_KEY = "api_key"
AUTH_METHOD_BOOTSTRAP_SECRET = "bootstrap_secret"
PRINCIPAL_HUMAN = "human"
PRINCIPAL_MACHINE = "machine"
DEFAULT_MACHINE_SCOPES = ("intent.read",)
MACHINE_TOKEN_TTL_SECONDS = 15 * 60
THROTTLE_WINDOW_SECONDS = 5 * 60
THROTTLE_MAX_FAILURES = 5
THROTTLE_BLOCK_SECONDS = 15 * 60


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: int
    database: str
    company_id: int
    allowed_company_ids: tuple[int, ...]
    role_xmlids: tuple[str, ...]
    principal_type: str
    auth_method: str
    credential_id: str
    scopes: tuple[str, ...]
    token_version: int
    credential_epoch: int = 0

    def claims(self):
        return {
            "user_id": self.user_id,
            "db": self.database,
            "company_id": self.company_id,
            "allowed_company_ids": list(self.allowed_company_ids),
            "role_xmlids": list(self.role_xmlids),
            "principal_type": self.principal_type,
            "auth_method": self.auth_method,
            "credential_id": self.credential_id,
            "scope": list(self.scopes),
            "token_version": self.token_version,
            "credential_epoch": self.credential_epoch,
        }


def _normalized_scopes(values):
    if values is None:
        return DEFAULT_MACHINE_SCOPES
    if not isinstance(values, (list, tuple)):
        raise ValidationError("credential scope must be a list")
    scopes = tuple(sorted(set(str(value or "").strip() for value in values if str(value or "").strip())))
    if not scopes:
        raise ValidationError("credential scope must not be empty")
    for scope in scopes:
        if scope not in {"intent.read", "intent.write"} and not scope.startswith("intent:"):
            raise ValidationError("credential scope is not supported")
    return scopes


def _role_xmlids(user):
    mapping = user.groups_id.get_external_id() or {}
    return tuple(sorted(mapping[group.id] for group in user.groups_id if mapping.get(group.id)))


def _principal_for_user(user, *, database, principal_type, auth_method, credential_id="", scopes=(), credential_epoch=0):
    user = user.sudo()
    if not user.exists() or not user.active:
        raise AccessDenied("credential principal is inactive")
    allowed = tuple(sorted(set(int(value) for value in user.company_ids.ids)))
    company_id = int(user.company_id.id or 0)
    if not company_id or company_id not in allowed:
        raise AccessDenied("credential principal company is invalid")
    return AuthenticatedPrincipal(
        user_id=int(user.id),
        database=str(database or "").strip(),
        company_id=company_id,
        allowed_company_ids=allowed,
        role_xmlids=_role_xmlids(user),
        principal_type=principal_type,
        auth_method=auth_method,
        credential_id=str(credential_id or ""),
        scopes=tuple(scopes),
        token_version=int(getattr(user, "token_version", 0) or 0),
        credential_epoch=int(credential_epoch or 0),
    )


def authenticate_password(*, database, login, secret):
    database = str(database or "").strip()
    login = str(login or "").strip()
    if not database or not login or not isinstance(secret, str) or not secret:
        raise AccessDenied("password credential is incomplete")
    registry = Registry(database)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        user_id = env["res.users"].authenticate(
            database,
            login,
            secret,
            {"interactive": True},
        )
        user = env["res.users"].sudo().browse(int(user_id or 0))
        return _principal_for_user(
            user,
            database=database,
            principal_type=PRINCIPAL_HUMAN,
            auth_method=AUTH_METHOD_PASSWORD,
            scopes=("interactive",),
        )


def principal_for_bootstrap_user(user, *, database):
    """Compatibility principal for the existing dev/test bootstrap secret."""
    return _principal_for_user(
        user,
        database=database,
        principal_type=PRINCIPAL_MACHINE,
        auth_method=AUTH_METHOD_BOOTSTRAP_SECRET,
        credential_id="platform_bootstrap_secret",
        scopes=("bootstrap",),
    )


def _audit(env, *, policy, event_code, actor_user_id, trace_id=""):
    env["sc.auth.credential.audit"].sudo().with_context(**{SERVICE_CONTEXT_KEY: True}).create({
        "credential_id": policy.credential_id,
        "event_code": event_code,
        "subject_user_id": policy.user_id.id,
        "actor_user_id": int(actor_user_id),
        "trace_id": str(trace_id or ""),
        "scope_json": policy.scopes_json,
        "company_ids_json": json.dumps(sorted(policy.company_ids.ids)),
    })


def expire_policy_if_due(env, *, policy, trace_id="", now=None):
    """Persist an effective expiry and its immutable audit exactly once."""
    policy = policy.sudo()
    now = now or fields.Datetime.now()
    if not policy.exists() or policy.state != "active" or not policy.expires_at or policy.expires_at > now:
        return False
    env.cr.execute(
        "SELECT id FROM sc_auth_credential_policy WHERE id = %s FOR UPDATE",
        [policy.id],
    )
    policy.invalidate_recordset(["state", "expires_at"])
    if policy.state != "active" or not policy.expires_at or policy.expires_at > now:
        return False
    policy.with_context(**{SERVICE_CONTEXT_KEY: True}).write({"state": "expired"})
    _audit(
        env,
        policy=policy,
        event_code="AUTH_API_KEY_EXPIRED",
        actor_user_id=policy.user_id.id,
        trace_id=trace_id,
    )
    return True


def synchronize_expired_policies(env, *, user_id, trace_id=""):
    """Synchronize lifecycle projection in an independently committed service unit.

    Credential listing is intentionally a read intent. Expiry synchronization is a
    security lifecycle side effect, so it cannot depend on the caller's read-only
    dispatcher transaction being committed.
    """
    registry = Registry(env.cr.dbname)
    with registry.cursor() as cr:
        service_env = api.Environment(cr, SUPERUSER_ID, {})
        now = fields.Datetime.now()
        due = service_env["sc.auth.credential.policy"].sudo().search([
            ("user_id", "=", int(user_id)),
            ("state", "=", "active"),
            ("expires_at", "!=", False),
            ("expires_at", "<=", now),
        ])
        expired_count = sum(
            1
            for policy in due
            if expire_policy_if_due(service_env, policy=policy, trace_id=trace_id, now=now)
        )
        cr.commit()
    return expired_count


def issue_machine_api_key(
    env,
    *,
    actor_user,
    password,
    name,
    scopes=None,
    company_ids=None,
    expires_at=None,
    trace_id="",
    rotated_from=None,
):
    actor_user = actor_user.sudo()
    if not actor_user.exists() or actor_user.share or not actor_user.active:
        raise AccessError("only active internal users can create machine credentials")
    confirmation = authenticate_password(
        database=env.cr.dbname,
        login=actor_user.login,
        secret=password,
    )
    if confirmation.user_id != actor_user.id:
        raise AccessDenied("credential confirmation does not match the current user")
    normalized_name = str(name or "").strip()
    if not normalized_name or len(normalized_name) > 120:
        raise ValidationError("credential name is required and must not exceed 120 characters")
    normalized_scopes = _normalized_scopes(scopes)
    current_companies = set(actor_user.company_ids.ids)
    requested_companies = set(int(value) for value in (company_ids or current_companies))
    if not requested_companies or not requested_companies.issubset(current_companies):
        raise AccessError("credential company scope exceeds the current user")
    normalized_expiry = fields.Datetime.to_datetime(expires_at) if expires_at else False
    if normalized_expiry and normalized_expiry <= fields.Datetime.now():
        raise ValidationError("credential expiry must be in the future")

    # Odoo's generator returns only the cleartext key. Serialize product-managed
    # creation for this user/scope, snapshot native IDs, then require exactly
    # one new row and one matching native prefix. Never select "latest".
    lock_identity = f"smart_core.api-key-create:{actor_user.id}:{MACHINE_NATIVE_SCOPE}"
    env.cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [lock_identity])
    env.cr.execute(
        "SELECT id FROM res_users_apikeys WHERE user_id = %s AND scope = %s",
        [actor_user.id, MACHINE_NATIVE_SCOPE],
    )
    native_ids_before = {int(row[0]) for row in env.cr.fetchall()}
    user_env = api.Environment(env.cr, actor_user.id, dict(env.context, interactive=True))
    secret = user_env["res.users.apikeys"]._generate(MACHINE_NATIVE_SCOPE, normalized_name)
    env.cr.execute(
        """
        SELECT id, index FROM res_users_apikeys
         WHERE user_id = %s AND scope = %s
        """,
        [actor_user.id, MACHINE_NATIVE_SCOPE],
    )
    native_rows_after = [(int(row[0]), str(row[1] or "")) for row in env.cr.fetchall()]
    new_native_ids = {row_id for row_id, _index in native_rows_after} - native_ids_before
    matching_prefix_ids = [row_id for row_id, index in native_rows_after if index == secret[:8]]
    if len(new_native_ids) != 1 or len(matching_prefix_ids) != 1:
        raise AccessError("native API key creation identity is ambiguous")
    native_key_id = next(iter(new_native_ids))
    if matching_prefix_ids[0] != native_key_id:
        raise AccessError("native API key creation identity does not match generated key")
    credential_id = f"odoo_api_key:{native_key_id}"
    policy = env["sc.auth.credential.policy"].sudo().with_context(**{SERVICE_CONTEXT_KEY: True}).create({
        "name": normalized_name,
        "credential_id": credential_id,
        "native_key_id": native_key_id,
        "user_id": actor_user.id,
        "company_ids": [(6, 0, sorted(requested_companies))],
        "scopes_json": json.dumps(list(normalized_scopes), separators=(",", ":")),
        "expires_at": normalized_expiry,
        "rotated_from_id": rotated_from.id if rotated_from else False,
    })
    _audit(
        env,
        policy=policy,
        event_code="AUTH_API_KEY_CREATED" if not rotated_from else "AUTH_API_KEY_ROTATED_TO",
        actor_user_id=actor_user.id,
        trace_id=trace_id,
    )
    return policy, secret


def revoke_machine_api_key(env, *, policy, actor_user, trace_id="", event_code="AUTH_API_KEY_REVOKED"):
    policy = policy.sudo()
    actor_user = actor_user.sudo()
    if not policy.exists() or policy.user_id != actor_user:
        raise AccessError("credential does not belong to the current user")
    if policy.state == "revoked":
        return policy
    native_key = env["res.users.apikeys"].sudo().browse(policy.native_key_id)
    if native_key.exists():
        native_key.with_user(actor_user)._remove()
    policy.with_context(**{SERVICE_CONTEXT_KEY: True}).write({
        "state": "revoked",
        "revoked_at": fields.Datetime.now(),
        "credential_epoch": int(policy.credential_epoch or 0) + 1,
    })
    _audit(
        env,
        policy=policy,
        event_code=event_code,
        actor_user_id=actor_user.id,
        trace_id=trace_id,
    )
    return policy


def record_machine_token_issued(env, *, principal, trace_id=""):
    policy = env["sc.auth.credential.policy"].sudo().search([
        ("credential_id", "=", principal.credential_id),
        ("user_id", "=", principal.user_id),
    ], limit=1)
    if not policy:
        raise AccessDenied("machine credential policy is unavailable")
    _audit(
        env,
        policy=policy,
        event_code="AUTH_MACHINE_TOKEN_ISSUED",
        actor_user_id=principal.user_id,
        trace_id=trace_id,
    )


def rotate_machine_api_key(env, *, policy, actor_user, password, trace_id=""):
    replacement, secret = issue_machine_api_key(
        env,
        actor_user=actor_user,
        password=password,
        name=f"{policy.name} (rotated)",
        scopes=list(policy.scope_values()),
        company_ids=policy.company_ids.ids,
        expires_at=policy.expires_at,
        trace_id=trace_id,
        rotated_from=policy,
    )
    revoke_machine_api_key(
        env,
        policy=policy,
        actor_user=actor_user,
        trace_id=trace_id,
        event_code="AUTH_API_KEY_ROTATED_FROM",
    )
    return replacement, secret


def _fingerprint(secret, pepper):
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()


def _next_throttle_failure_values(*, now, window_started_at=None, failure_count=0):
    window_start = now - timedelta(seconds=THROTTLE_WINDOW_SECONDS)
    if not window_started_at or window_started_at < window_start:
        return {
            "window_started_at": now,
            "last_attempt_at": now,
            "failure_count": 1,
            "blocked_until": False,
        }
    failures = int(failure_count or 0) + 1
    values = {"failure_count": failures, "last_attempt_at": now}
    if failures >= THROTTLE_MAX_FAILURES:
        values["blocked_until"] = now + timedelta(seconds=THROTTLE_BLOCK_SECONDS)
    return values


def _native_key_id_for_verified_user(env, *, user_id, secret):
    """Resolve identity only after Odoo's native verifier accepted the key.

    The policy layer must never read or re-check Odoo's key hash. A duplicated
    native prefix is treated as ambiguous and rejected instead of guessing.
    """
    index = secret[:8]
    env.cr.execute(
        """
        SELECT id
          FROM res_users_apikeys
         WHERE user_id = %s AND index = %s AND scope = %s
         ORDER BY id DESC
        """,
        [int(user_id), index, MACHINE_NATIVE_SCOPE],
    )
    matches = [int(row[0]) for row in env.cr.fetchall()]
    if len(matches) != 1:
        raise AccessDenied("API key identity is ambiguous")
    return matches[0]


def _throttle(database, *, subject_hash, success=None):
    now = fields.Datetime.now()
    registry = Registry(database)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        cr.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", [subject_hash])
        model = env["sc.auth.credential.throttle"].sudo().with_context(**{SERVICE_CONTEXT_KEY: True})
        row = model.search([("subject_hash", "=", subject_hash)], limit=1)
        if row:
            effective_blocked_until = row.blocked_until
            if not effective_blocked_until and int(row.failure_count or 0) >= THROTTLE_MAX_FAILURES:
                effective_blocked_until = row.last_attempt_at + timedelta(seconds=THROTTLE_BLOCK_SECONDS)
            if effective_blocked_until and effective_blocked_until > now:
                raise AccessDenied("credential authentication is rate limited")
        if success is None:
            return
        if success:
            if row:
                row.unlink()
        else:
            values = _next_throttle_failure_values(
                now=now,
                window_started_at=row.window_started_at if row else None,
                failure_count=row.failure_count if row else 0,
            )
            if row:
                row.write(values)
            else:
                model.create({"subject_hash": subject_hash, **values})
        cr.commit()


def authenticate_api_key(*, database, secret, requested_scopes=None, fingerprint_pepper, client_identity):
    database = str(database or "").strip()
    if (
        not database
        or not isinstance(secret, str)
        or not secret
        or not fingerprint_pepper
        or not str(client_identity or "").strip()
    ):
        raise AccessDenied("API-key credential is incomplete")
    subject_hash = _fingerprint(str(client_identity).strip(), fingerprint_pepper)
    _throttle(database, subject_hash=subject_hash)
    registry = Registry(database)
    try:
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            user_id = env["res.users.apikeys"]._check_credentials(scope=MACHINE_NATIVE_SCOPE, key=secret)
            if not user_id:
                raise AccessDenied("API key is invalid")
            native_key_id = _native_key_id_for_verified_user(env, user_id=user_id, secret=secret)
            policy = env["sc.auth.credential.policy"].sudo().search(
                [("native_key_id", "=", native_key_id), ("user_id", "=", int(user_id))],
                limit=1,
            )
            now = fields.Datetime.now()
            if not policy or policy.state != "active" or not policy.native_key_exists():
                raise AccessDenied("API key policy is inactive")
            if policy.expires_at and policy.expires_at <= now:
                # Authentication rejects by raising, so its cursor is rolled back by
                # the registry context. Persist the lifecycle transition in the same
                # independently committed service path used by credential listing.
                expired_count = synchronize_expired_policies(
                    env,
                    user_id=int(user_id),
                    trace_id="machine-exchange",
                )
                if expired_count < 1:
                    raise AccessDenied("API key expiry lifecycle synchronization failed")
                raise AccessDenied("API key is expired")
            granted = set(policy.scope_values())
            requested = set(_normalized_scopes(requested_scopes)) if requested_scopes is not None else granted
            if not requested or not requested.issubset(granted):
                raise AccessDenied("requested scope exceeds credential policy")
            user = env["res.users"].sudo().browse(int(user_id))
            allowed_policy_companies = set(policy.company_ids.ids)
            principal = _principal_for_user(
                user,
                database=database,
                principal_type=PRINCIPAL_MACHINE,
                auth_method=AUTH_METHOD_API_KEY,
                credential_id=policy.credential_id,
                scopes=tuple(sorted(requested)),
                credential_epoch=policy.credential_epoch,
            )
            if allowed_policy_companies:
                narrowed = tuple(sorted(set(principal.allowed_company_ids) & allowed_policy_companies))
                if not narrowed:
                    raise AccessDenied("API key company policy is invalid")
                principal = replace(
                    principal,
                    company_id=principal.company_id if principal.company_id in narrowed else narrowed[0],
                    allowed_company_ids=narrowed,
                )
            policy.with_context(**{SERVICE_CONTEXT_KEY: True}).write({
                "last_used_at": now,
                "usage_count": int(policy.usage_count or 0) + 1,
            })
            cr.commit()
        _throttle(database, subject_hash=subject_hash, success=True)
        return principal
    except (AccessDenied, AccessError, ValidationError):
        _throttle(database, subject_hash=subject_hash, success=False)
        raise


def assert_principal_scope(principal, *, intent_name, params=None):
    auth_method = principal.get("auth_method") if isinstance(principal, dict) else getattr(principal, "auth_method", "")
    scopes_value = principal.get("scopes") if isinstance(principal, dict) else getattr(principal, "scopes", ())
    if not principal or auth_method != AUTH_METHOD_API_KEY:
        return True
    intent = str(intent_name or "").strip()
    from ..core.handler_registry import HANDLER_REGISTRY

    handler = HANDLER_REGISTRY.get(intent)
    resolver = getattr(handler, "machine_access_for", None)
    machine_access = str(resolver(params) if callable(resolver) else "deny").strip().lower()
    if machine_access not in {"read", "write"}:
        raise AccessError("machine credential is not allowed for this intent")
    scopes = set(scopes_value or ())
    if f"intent:{intent}" in scopes:
        return True
    if machine_access == "write":
        if "intent.write" in scopes:
            return True
    elif machine_access == "read" and "intent.read" in scopes:
        return True
    raise AccessError("machine credential scope denies this intent")
