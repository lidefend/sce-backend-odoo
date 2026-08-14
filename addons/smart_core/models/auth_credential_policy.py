# -*- coding: utf-8 -*-
import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


SERVICE_CONTEXT_KEY = "sc_auth_credential_service"
MACHINE_NATIVE_SCOPE = "smart_core.machine"


class ScAuthCredentialPolicy(models.Model):
    _name = "sc.auth.credential.policy"
    _description = "Machine Credential Policy Projection"
    _order = "id desc"

    name = fields.Char(required=True)
    credential_id = fields.Char(required=True, index=True, copy=False)
    native_key_id = fields.Integer(required=True, index=True, copy=False)
    user_id = fields.Many2one("res.users", required=True, index=True, ondelete="cascade")
    company_ids = fields.Many2many("res.company", string="Allowed Companies")
    scopes_json = fields.Text(required=True, default="[]")
    state = fields.Selection(
        [("active", "Active"), ("revoked", "Revoked"), ("expired", "Expired")],
        required=True,
        default="active",
        index=True,
    )
    expires_at = fields.Datetime(index=True)
    last_used_at = fields.Datetime(index=True, readonly=True)
    usage_count = fields.Integer(default=0, readonly=True)
    credential_epoch = fields.Integer(default=1, required=True, readonly=True)
    revoked_at = fields.Datetime(index=True, readonly=True)
    rotated_from_id = fields.Many2one(
        "sc.auth.credential.policy",
        index=True,
        ondelete="restrict",
        readonly=True,
    )

    _sql_constraints = [
        ("sc_auth_credential_id_uniq", "unique(credential_id)", "Credential ID must be unique."),
        ("sc_auth_native_key_id_uniq", "unique(native_key_id)", "Native API key must be unique."),
    ]

    @api.constrains("scopes_json")
    def _check_scopes_json(self):
        for record in self:
            try:
                values = json.loads(record.scopes_json or "[]")
            except (TypeError, ValueError) as exc:
                raise ValidationError(_("Credential scopes must be valid JSON.")) from exc
            if not isinstance(values, list) or not values or any(
                not isinstance(value, str) or not value.strip() for value in values
            ):
                raise ValidationError(_("Credential scopes must be a non-empty string list."))
            normalized = sorted(set(value.strip() for value in values))
            if normalized != values:
                raise ValidationError(_("Credential scopes must be sorted and unique."))

    def scope_values(self):
        self.ensure_one()
        return tuple(json.loads(self.scopes_json or "[]"))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential policies can only be created by the authentication service."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential policies can only be changed by the authentication service."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("Credential policy history cannot be deleted."))

    def native_key_exists(self):
        self.ensure_one()
        self.env.cr.execute("SELECT 1 FROM res_users_apikeys WHERE id = %s", [self.native_key_id])
        return bool(self.env.cr.fetchone())


class ScAuthCredentialThrottle(models.Model):
    _name = "sc.auth.credential.throttle"
    _description = "Machine Credential Authentication Throttle"

    subject_hash = fields.Char(required=True, index=True, copy=False)
    window_started_at = fields.Datetime(required=True, index=True)
    failure_count = fields.Integer(default=0, required=True)
    blocked_until = fields.Datetime(index=True)
    last_attempt_at = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        ("sc_auth_credential_throttle_subject_uniq", "unique(subject_hash)", "Throttle subject must be unique."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential throttle state is service-managed."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential throttle state is service-managed."))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential throttle state is service-managed."))
        return super().unlink()


class ScAuthCredentialAudit(models.Model):
    _name = "sc.auth.credential.audit"
    _description = "Credential Lifecycle Audit"
    _order = "id desc"

    credential_id = fields.Char(required=True, index=True)
    event_code = fields.Char(required=True, index=True)
    subject_user_id = fields.Many2one("res.users", required=True, index=True, ondelete="restrict")
    actor_user_id = fields.Many2one("res.users", required=True, index=True, ondelete="restrict")
    trace_id = fields.Char(index=True)
    scope_json = fields.Text(default="[]")
    company_ids_json = fields.Text(default="[]")
    occurred_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get(SERVICE_CONTEXT_KEY):
            raise AccessError(_("Credential audit is service-managed."))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Credential audit is immutable."))

    def unlink(self):
        raise AccessError(_("Credential audit is immutable."))
