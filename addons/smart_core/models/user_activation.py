# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
import time
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


PURPOSE_ENTERPRISE_ACTIVATION = "enterprise_activation"
PURPOSE_PASSWORD_RECOVERY = "password_recovery"
SUPPORTED_PURPOSES = (
    (PURPOSE_ENTERPRISE_ACTIVATION, "Enterprise activation"),
    (PURPOSE_PASSWORD_RECOVERY, "Password recovery"),
    ("email_verification", "Email verification"),
    ("saas_registration_verification", "SaaS registration verification"),
    ("tenant_invitation", "Tenant invitation"),
)
ENABLED_PURPOSES = frozenset({PURPOSE_ENTERPRISE_ACTIVATION})
TOKEN_TTL_HOURS = 24
CHALLENGE_TTL_MINUTES = 10
MAX_FAILED_ATTEMPTS = 8


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_digest(value) -> str:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return _sha256_text(payload)


class ScUserActivationBatch(models.Model):
    _name = "sc.user.activation.batch"
    _description = "User activation batch"
    _order = "create_date desc, id desc"

    batch_key = fields.Char(required=True, index=True, copy=False)
    purpose = fields.Selection(SUPPORTED_PURPOSES, required=True, index=True)
    tenant_key = fields.Char(required=True, index=True)
    environment_type = fields.Selection(
        [("production", "Production"), ("acceptance", "Acceptance"), ("practice", "Practice")],
        required=True,
        default="production",
        index=True,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("paused", "Paused"), ("closed", "Closed")],
        required=True,
        default="draft",
        index=True,
    )
    emergency_stop_reason = fields.Char(copy=False)

    _sql_constraints = [
        ("sc_user_activation_batch_key_uniq", "unique(batch_key)", "Activation batch key must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("ACTIVATION_BATCH_DELETE_FORBIDDEN"))


class ScUserActivationCredential(models.Model):
    _name = "sc.user.activation.credential"
    _description = "Digest-only user activation credential"
    _order = "issued_at desc, id desc"

    credential_id = fields.Char(required=True, index=True, copy=False)
    immutable_user_id = fields.Char(required=True, index=True, copy=False)
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="restrict")
    purpose = fields.Selection(SUPPORTED_PURPOSES, required=True, index=True)
    tenant_key = fields.Char(required=True, index=True)
    environment_type = fields.Selection(
        [("production", "Production"), ("acceptance", "Acceptance"), ("practice", "Practice")],
        required=True,
        index=True,
    )
    target_login = fields.Char(required=True, copy=False)
    token_digest = fields.Char(required=True, index=True, copy=False)
    token_fingerprint = fields.Char(required=True, index=True, copy=False)
    challenge_digest = fields.Char(index=True, copy=False)
    challenge_expires_at = fields.Datetime(copy=False)
    group_snapshot_digest = fields.Char(required=True, copy=False)
    primary_company_snapshot = fields.Char(required=True, copy=False)
    allowed_company_snapshot_digest = fields.Char(required=True, copy=False)
    active_snapshot = fields.Boolean(required=True)
    share_snapshot = fields.Boolean(required=True)
    batch_id = fields.Many2one("sc.user.activation.batch", required=True, index=True, ondelete="restrict")
    issued_at = fields.Datetime(required=True, copy=False)
    expires_at = fields.Datetime(required=True, index=True, copy=False)
    used_at = fields.Datetime(copy=False)
    revoked_at = fields.Datetime(copy=False)
    failed_attempts = fields.Integer(required=True, default=0, copy=False)
    state = fields.Selection(
        [("pending", "Pending"), ("used", "Used"), ("revoked", "Revoked"), ("expired", "Expired")],
        required=True,
        default="pending",
        index=True,
    )

    _sql_constraints = [
        ("sc_user_activation_credential_id_uniq", "unique(credential_id)", "Credential ID must be unique."),
        ("sc_user_activation_token_digest_uniq", "unique(token_digest)", "Credential digest must be unique."),
        ("sc_user_activation_challenge_digest_uniq", "unique(challenge_digest)", "Challenge digest must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("ACTIVATION_CREDENTIAL_DELETE_FORBIDDEN"))

    @api.model
    def _require_activation_admin(self):
        if not self.env.user.has_group("smart_core.group_smart_core_user_activation_admin"):
            raise AccessError(_("USER_ACTIVATION_ADMIN_REQUIRED"))

    @api.model
    def _record_xmlids(self, records) -> list[str]:
        if not records:
            return []
        mapping = records.get_external_id()
        return sorted(mapping.get(record.id) or f"{record._name}:dbid:{record.id}" for record in records)

    @api.model
    def _snapshot(self, user) -> dict[str, object]:
        user.ensure_one()
        return {
            "groups": self._record_xmlids(user.groups_id),
            "primary_company": self._record_xmlids(user.company_id),
            "allowed_companies": self._record_xmlids(user.company_ids),
            "active": bool(user.active),
            "share": bool(user.share),
        }

    @api.model
    def _validate_eligible_user(self, user):
        user.ensure_one()
        public_user = self.env.ref("base.public_user", raise_if_not_found=False)
        portal = self.env.ref("base.group_portal", raise_if_not_found=False)
        if not user.active or user.share or (public_user and user == public_user):
            raise UserError(_("ACTIVATION_USER_NOT_ELIGIBLE"))
        if portal and portal in user.groups_id:
            raise UserError(_("ACTIVATION_USER_NOT_ELIGIBLE"))

    @api.model
    def _create_batch(self, *, batch_key: str, tenant_key: str, environment_type: str, purpose: str):
        self._require_activation_admin()
        if purpose not in ENABLED_PURPOSES:
            raise UserError(_("ACTIVATION_PURPOSE_NOT_ENABLED"))
        values = {
            "batch_key": str(batch_key or "").strip(),
            "tenant_key": str(tenant_key or "").strip(),
            "environment_type": str(environment_type or "").strip(),
            "purpose": purpose,
            "state": "active",
        }
        if not values["batch_key"] or not values["tenant_key"]:
            raise ValidationError(_("ACTIVATION_BATCH_IDENTITY_REQUIRED"))
        return self.env["sc.user.activation.batch"].sudo().with_context(sc_activation_service=True).create(values)

    @api.model
    def _issue_once(
        self,
        *,
        user,
        immutable_user_id: str,
        target_login: str,
        tenant_key: str,
        environment_type: str,
        batch,
        purpose: str = PURPOSE_ENTERPRISE_ACTIVATION,
        ttl_hours: int = TOKEN_TTL_HOURS,
    ) -> dict[str, str]:
        self._require_activation_admin()
        if purpose not in ENABLED_PURPOSES:
            raise UserError(_("ACTIVATION_PURPOSE_NOT_ENABLED"))
        user = user.sudo().exists()
        if len(user) != 1:
            raise UserError(_("ACTIVATION_USER_IDENTITY_AMBIGUOUS"))
        self._validate_eligible_user(user)
        if batch.state != "active" or batch.purpose != purpose:
            raise UserError(_("ACTIVATION_BATCH_NOT_ACTIVE"))
        if batch.tenant_key != tenant_key or batch.environment_type != environment_type:
            raise UserError(_("ACTIVATION_BATCH_BINDING_MISMATCH"))
        immutable_user_id = str(immutable_user_id or "").strip()
        target_login = str(target_login or "").strip()
        if not immutable_user_id or not target_login:
            raise ValidationError(_("ACTIVATION_USER_BINDING_REQUIRED"))
        if user.login != target_login:
            raise UserError(_("ACTIVATION_TARGET_LOGIN_NOT_MIGRATED"))

        now = fields.Datetime.now()
        pending = self.sudo().search(
            [
                ("user_id", "=", user.id),
                ("purpose", "=", purpose),
                ("state", "=", "pending"),
                ("expires_at", ">", now),
            ]
        )
        if pending:
            raise UserError(_("ACTIVATION_PENDING_CREDENTIAL_EXISTS"))

        raw_token = secrets.token_urlsafe(32)
        token_digest = _sha256_text(raw_token)
        snapshot = self._snapshot(user)
        expires_at = now + timedelta(hours=max(1, min(int(ttl_hours), TOKEN_TTL_HOURS)))
        credential = self.sudo().with_context(sc_activation_service=True).create(
            {
                "credential_id": str(uuid.uuid4()),
                "immutable_user_id": immutable_user_id,
                "user_id": user.id,
                "purpose": purpose,
                "tenant_key": tenant_key,
                "environment_type": environment_type,
                "target_login": target_login,
                "token_digest": token_digest,
                "token_fingerprint": token_digest[:16],
                "group_snapshot_digest": _canonical_digest(snapshot["groups"]),
                "primary_company_snapshot": _canonical_digest(snapshot["primary_company"]),
                "allowed_company_snapshot_digest": _canonical_digest(snapshot["allowed_companies"]),
                "active_snapshot": snapshot["active"],
                "share_snapshot": snapshot["share"],
                "batch_id": batch.id,
                "issued_at": now,
                "expires_at": expires_at,
                "state": "pending",
            }
        )
        credential._event("issued")
        # The raw token is returned once and is never persisted by this model.
        return {
            "credential_id": credential.credential_id,
            "activation_token": raw_token,
            "token_fingerprint": credential.token_fingerprint,
            "expires_at": fields.Datetime.to_string(expires_at),
        }

    @api.model
    def _constant_time_lookup(self, *, field_name: str, raw_secret: str):
        digest = _sha256_text(str(raw_secret or ""))
        if field_name not in {"token_digest", "challenge_digest"}:
            raise ValueError("unsupported credential digest field")
        self.env.cr.execute(
            f"SELECT id, {field_name} FROM sc_user_activation_credential WHERE {field_name} = %s FOR UPDATE",
            [digest],
        )
        row = self.env.cr.fetchone()
        if not row or not hmac.compare_digest(str(row[1] or ""), digest):
            return self.browse()
        credential = self.sudo().browse(row[0]).exists()
        # The digest is read under an explicit row lock.  In the same
        # transaction the ORM cache may still contain the pre-challenge
        # values, so make the locked database row authoritative before the
        # state/binding checks below.
        credential.invalidate_recordset()
        return credential

    def _binding_is_current(self) -> bool:
        self.ensure_one()
        user = self.user_id.sudo().exists()
        if len(user) != 1:
            return False
        snapshot = self._snapshot(user)
        checks = (
            user.login == self.target_login,
            bool(user.active) == bool(self.active_snapshot),
            bool(user.share) == bool(self.share_snapshot),
            hmac.compare_digest(_canonical_digest(snapshot["groups"]), self.group_snapshot_digest),
            hmac.compare_digest(_canonical_digest(snapshot["primary_company"]), self.primary_company_snapshot),
            hmac.compare_digest(_canonical_digest(snapshot["allowed_companies"]), self.allowed_company_snapshot_digest),
        )
        return all(checks)

    def _runtime_binding_is_current(self) -> bool:
        self.ensure_one()
        parameters = self.env["ir.config_parameter"].sudo()
        runtime_tenant = str(parameters.get_param("sc.runtime.tenant_key", "") or "").strip()
        runtime_environment = str(parameters.get_param("sc.runtime.environment_type", "") or "").strip()
        return bool(
            runtime_tenant
            and runtime_environment
            and hmac.compare_digest(runtime_tenant, self.tenant_key)
            and hmac.compare_digest(runtime_environment, self.environment_type)
        )

    def _reject_attempt(self, event_type: str):
        self.ensure_one()
        self.sudo().with_context(sc_activation_service=True).write(
            {"failed_attempts": min(int(self.failed_attempts or 0) + 1, MAX_FAILED_ATTEMPTS)}
        )
        self._event(event_type)

    @api.model
    def _begin_activation(self, raw_token: str, *, expected_purpose: str) -> dict[str, str]:
        if expected_purpose != PURPOSE_ENTERPRISE_ACTIVATION:
            raise UserError(_("ACTIVATION_REQUEST_REJECTED"))
        credential = self._constant_time_lookup(field_name="token_digest", raw_secret=raw_token)
        now = fields.Datetime.now()
        if (
            not credential
            or credential.purpose != expected_purpose
            or credential.state != "pending"
            or credential.expires_at <= now
            or credential.failed_attempts >= MAX_FAILED_ATTEMPTS
            or credential.batch_id.state != "active"
            or credential.challenge_digest
            or not credential._binding_is_current()
            or not credential._runtime_binding_is_current()
        ):
            if credential:
                credential._reject_attempt("start_rejected")
            raise UserError(_("ACTIVATION_REQUEST_REJECTED"))
        challenge = secrets.token_urlsafe(32)
        credential.with_context(sc_activation_service=True).write(
            {
                "challenge_digest": _sha256_text(challenge),
                "challenge_expires_at": now + timedelta(minutes=CHALLENGE_TTL_MINUTES),
            }
        )
        credential._event("challenge_issued")
        return {"activation_context": challenge, "expires_in_seconds": str(CHALLENGE_TTL_MINUTES * 60)}

    @api.model
    def _validate_password(self, password: str):
        password = str(password or "")
        if len(password) < 12 or not any(ch.isalpha() for ch in password) or not any(ch.isdigit() for ch in password):
            raise UserError(_("ACTIVATION_PASSWORD_POLICY_REJECTED"))

    @api.model
    def _complete_activation(self, activation_context: str, password: str, *, expected_purpose: str):
        if expected_purpose != PURPOSE_ENTERPRISE_ACTIVATION:
            raise UserError(_("ACTIVATION_REQUEST_REJECTED"))
        credential = self._constant_time_lookup(field_name="challenge_digest", raw_secret=activation_context)
        now = fields.Datetime.now()
        if (
            not credential
            or credential.purpose != expected_purpose
            or credential.state != "pending"
            or not credential.challenge_expires_at
            or credential.challenge_expires_at <= now
            or credential.expires_at <= now
            or credential.batch_id.state != "active"
            or not credential._binding_is_current()
            or not credential._runtime_binding_is_current()
        ):
            if credential:
                credential._reject_attempt("completion_rejected")
            raise UserError(_("ACTIVATION_REQUEST_REJECTED"))
        try:
            self._validate_password(password)
        except UserError:
            credential.with_context(sc_activation_service=True).write(
                {"failed_attempts": credential.failed_attempts + 1}
            )
            credential._event("password_rejected")
            raise

        user = credential.user_id.sudo()
        before = credential._snapshot(user)
        # Odoo remains the password hashing and authentication authority.
        user.with_context(sc_skip_token_epoch_bump=False).write({"password": password})
        after = credential._snapshot(user)
        if before != after or user.login != credential.target_login:
            raise UserError(_("ACTIVATION_BINDING_MUTATION_DETECTED"))
        credential.with_context(sc_activation_service=True).write(
            {
                "state": "used",
                "used_at": now,
                "challenge_digest": False,
                "challenge_expires_at": False,
            }
        )
        credential._event("used")
        return True

    def _event(self, event_type: str):
        self.ensure_one()
        return self.env["sc.user.activation.event"].sudo().with_context(sc_activation_service=True).create(
            {
                "credential_id": self.id,
                "batch_id": self.batch_id.id,
                "event_type": event_type,
                "token_fingerprint": self.token_fingerprint,
                "occurred_at": fields.Datetime.now(),
            }
        )

    def _revoke(self, reason: str = ""):
        self._require_activation_admin()
        for credential in self.filtered(lambda item: item.state == "pending"):
            credential.sudo().with_context(sc_activation_service=True).write(
                {
                    "state": "revoked",
                    "revoked_at": fields.Datetime.now(),
                    "challenge_digest": False,
                    "challenge_expires_at": False,
                }
            )
            credential._event("revoked")
        return True

    @api.model
    def _reissue_once(self, **issue_values):
        """Replace one pending credential without ever redisplaying a secret."""
        self._require_activation_admin()
        user = issue_values.get("user").sudo().exists()
        purpose = issue_values.get("purpose", PURPOSE_ENTERPRISE_ACTIVATION)
        pending = self.sudo().search(
            [("user_id", "=", user.id), ("purpose", "=", purpose), ("state", "=", "pending")]
        )
        if pending:
            pending.with_user(self.env.user)._revoke(reason="reissued")
        return self._issue_once(**issue_values)

    def _record_delivery(self, *, operator_identity: str, channel_type: str, verification_method: str):
        self._require_activation_admin()
        self.ensure_one()
        if self.state != "pending":
            raise UserError(_("ACTIVATION_DELIVERY_STATE_INVALID"))
        return self.env["sc.user.activation.delivery.audit"].sudo().with_context(sc_activation_service=True).create(
            {
                "credential_id": self.id,
                "batch_id": self.batch_id.id,
                "immutable_user_id": self.immutable_user_id,
                "authorized_delivery_operator": str(operator_identity or "").strip(),
                "delivery_channel_type": str(channel_type or "").strip(),
                "identity_verification_method": str(verification_method or "").strip(),
                "delivered_at": fields.Datetime.now(),
                "token_fingerprint": self.token_fingerprint,
                "expires_at": self.expires_at,
            }
        )


class ScUserActivationDeliveryAudit(models.Model):
    _name = "sc.user.activation.delivery.audit"
    _description = "Non-secret activation delivery audit"
    _order = "delivered_at desc, id desc"

    credential_id = fields.Many2one("sc.user.activation.credential", required=True, index=True, ondelete="restrict")
    batch_id = fields.Many2one("sc.user.activation.batch", required=True, index=True, ondelete="restrict")
    immutable_user_id = fields.Char(required=True, index=True)
    authorized_delivery_operator = fields.Char(required=True)
    delivery_channel_type = fields.Char(required=True)
    identity_verification_method = fields.Char(required=True)
    delivered_at = fields.Datetime(required=True)
    token_fingerprint = fields.Char(required=True, index=True)
    expires_at = fields.Datetime(required=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        if any(not vals.get("authorized_delivery_operator") or not vals.get("delivery_channel_type") or not vals.get("identity_verification_method") for vals in vals_list):
            raise ValidationError(_("ACTIVATION_DELIVERY_AUDIT_REQUIRED"))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("ACTIVATION_DELIVERY_AUDIT_IMMUTABLE"))

    def unlink(self):
        raise AccessError(_("ACTIVATION_DELIVERY_AUDIT_IMMUTABLE"))


class ScUserActivationEvent(models.Model):
    _name = "sc.user.activation.event"
    _description = "User activation security event"
    _order = "occurred_at desc, id desc"

    credential_id = fields.Many2one("sc.user.activation.credential", required=True, index=True, ondelete="restrict")
    batch_id = fields.Many2one("sc.user.activation.batch", required=True, index=True, ondelete="restrict")
    event_type = fields.Char(required=True, index=True)
    token_fingerprint = fields.Char(required=True, index=True)
    occurred_at = fields.Datetime(required=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("ACTIVATION_EVENT_IMMUTABLE"))

    def unlink(self):
        raise AccessError(_("ACTIVATION_EVENT_IMMUTABLE"))


class ScUserActivationThrottle(models.Model):
    _name = "sc.user.activation.throttle"
    _description = "Hashed activation request throttle"

    scope_digest = fields.Char(required=True, index=True)
    window_start = fields.Integer(required=True, default=0)
    request_count = fields.Integer(required=True, default=0)
    last_seen = fields.Integer(required=True, default=0)

    _sql_constraints = [
        ("sc_user_activation_throttle_scope_uniq", "unique(scope_digest)", "Throttle scope must be unique."),
    ]

    @api.model
    def _scope_digest(self, scope: str) -> str:
        database_uuid = self.env["ir.config_parameter"].sudo().get_param("database.uuid", self.env.cr.dbname)
        return hmac.new(str(database_uuid).encode("utf-8"), str(scope).encode("utf-8"), hashlib.sha256).hexdigest()

    @api.model
    def _check_and_bump(self, *, scope: str, window_seconds: int = 600, max_requests: int = 10) -> bool:
        digest = self._scope_digest(scope)
        now = int(time.time())
        self.env.cr.execute(
            "SELECT id FROM sc_user_activation_throttle WHERE scope_digest = %s FOR UPDATE",
            [digest],
        )
        row = self.env.cr.fetchone()
        if not row:
            self.sudo().with_context(sc_activation_service=True).create(
                {"scope_digest": digest, "window_start": now, "request_count": 1, "last_seen": now}
            )
            return True
        record = self.sudo().browse(row[0])
        if now - record.window_start >= int(window_seconds):
            record.with_context(sc_activation_service=True).write(
                {"window_start": now, "request_count": 1, "last_seen": now}
            )
            return True
        if record.request_count >= int(max_requests):
            return False
        record.with_context(sc_activation_service=True).write(
            {"request_count": record.request_count + 1, "last_seen": now}
        )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get("sc_activation_service"):
            raise AccessError(_("ACTIVATION_SERVICE_CONTEXT_REQUIRED"))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("ACTIVATION_THROTTLE_DELETE_FORBIDDEN"))
