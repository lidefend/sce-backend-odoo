"""Platform database registration, lifecycle and maintenance access.

Owner ruling (2026-10-14): the database architecture policy and the data-space
onboarding mechanism are the single declaration source; this module is their
platform product capability, deliberately small:

* a database *registration* row carries the database role, tenant key, strategy,
  data purpose and lifecycle state, so a database is a governed object and not
  an ambient convention;
* the *managed operation entries* are the only writers of that lifecycle, they
  refuse an entry the declaration does not authorize and each one returns a
  result readback plus one audit row;
* a *maintenance access* is a separate authorization for special maintenance
  work. It authorizes operations only: it never widens business record scope,
  which is why ``grants_business_data_scope`` is a computed, always-false fact
  rather than a configurable field.

Nothing here decides a tenant, a purpose or an initialization rule: those stay
declared in ``data/tenant/database_strategy.v1.json`` and resolved by
``security/data_space_provisioning.py``.
"""

from __future__ import annotations

import re
from datetime import timedelta

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.smart_core.security import data_space_provisioning as provisioning
from odoo.addons.smart_core.security.database_governance import (
    DATABASE_LIFECYCLE_INITIAL_STATE,
    DATABASE_LIFECYCLE_STATES,
    MAINTENANCE_ACCESS_CAPABILITIES,
    MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS,
    maintenance_access_grants_business_data_scope,
    resolve_operation_target_state,
    validate_database_governance_principal,
    validate_maintenance_capability,
)

SECURITY_ADMIN_GROUP = "smart_core.group_smart_core_security_admin"


class ScPlatformDatabaseRegistration(models.Model):
    """One governed database: role, tenant key, strategy, purpose, lifecycle."""

    _name = "sc.platform.database.registration"
    _description = "Platform Database Registration"
    _order = "db_name"

    db_name = fields.Char(required=True, index=True, readonly=True)
    dbfilter = fields.Char(readonly=True, help="Declared dbfilter; empty means the database name.")
    environment_role = fields.Char(required=True, index=True, readonly=True)
    strategy = fields.Char(required=True, readonly=True)
    data_purpose = fields.Selection(
        [("customer", "Customer business"), ("demo", "Demonstration"), ("test", "Test")],
        required=True,
        readonly=True,
        index=True,
    )
    tenant_key = fields.Char(readonly=True)
    lifecycle_state = fields.Selection(
        [(state, state) for state in DATABASE_LIFECYCLE_STATES],
        default=DATABASE_LIFECYCLE_INITIAL_STATE,
        required=True,
        readonly=True,
        index=True,
    )
    registered_by = fields.Many2one("res.users", readonly=True)
    registered_at = fields.Datetime(readonly=True)
    last_operation = fields.Char(readonly=True)
    last_operation_at = fields.Datetime(readonly=True)
    last_readback = fields.Json(readonly=True)
    operation_ids = fields.One2many(
        "sc.platform.database.operation", "registration_id", readonly=True
    )
    maintenance_access_ids = fields.One2many(
        "sc.platform.maintenance.access", "registration_id", readonly=True
    )

    _sql_constraints = [
        (
            "platform_database_registration_db_name_uniq",
            "unique(db_name)",
            "A governed database is registered exactly once.",
        ),
    ]

    # ------------------------------------------------------------------
    # readback
    # ------------------------------------------------------------------
    def readback(self):
        self.ensure_one()
        return {
            "db_name": self.db_name,
            "dbfilter": self.dbfilter or "",
            "environment_role": self.environment_role,
            "strategy": self.strategy,
            "data_purpose": self.data_purpose,
            "tenant_key": self.tenant_key or "",
            "lifecycle_state": self.lifecycle_state,
            "last_operation": self.last_operation or "",
            "operation_count": len(self.operation_ids),
            "maintenance_access_count": len(self.maintenance_access_ids),
            "grants_business_data_scope": maintenance_access_grants_business_data_scope(),
        }

    def _write_readback(self, operation, *, reason="", execution_id=""):
        self.ensure_one()
        self.with_context(sc_platform_database_readback=True).write(
            {
                "last_operation": operation,
                "last_operation_at": fields.Datetime.now(),
            }
        )
        readback = self.readback()
        # The registration row is locked by the lifecycle entry; include the
        # audit being appended in this same transaction in its result snapshot.
        readback["operation_count"] += 1
        if reason or execution_id:
            readback["operation_request"] = {"reason": str(reason), "execution_id": str(execution_id)}
        self.env["sc.platform.database.operation"].sudo().create(
            [{
                "registration_id": self.id,
                "operation": operation,
                "from_state": self.env.context.get("sc_platform_database_from_state") or "",
                "to_state": self.lifecycle_state,
                "actor_id": self.env.uid,
                "result": readback,
            }]
        )
        self.with_context(sc_platform_database_readback=True).write({"last_readback": readback})
        return readback

    # ------------------------------------------------------------------
    # immutable identity / managed lifecycle
    # ------------------------------------------------------------------
    def write(self, vals):
        allowed = {
            "last_operation",
            "last_operation_at",
            "last_readback",
        }
        if set(vals) - allowed and not self.env.context.get("sc_platform_database_managed"):
            raise UserError("DBGOV1_DATABASE_REGISTRATION_IDENTITY_IMMUTABLE")
        return super().write(vals)

    def unlink(self):
        raise UserError("DBGOV1_DATABASE_REGISTRATION_IMMUTABLE")

    @api.model
    def _assert_governance_principal(self):
        try:
            validate_database_governance_principal(
                uid=self.env.uid, superuser_id=SUPERUSER_ID, su=self.env.su
            )
        except PermissionError as exc:
            raise AccessError(str(exc)) from exc

    @api.model
    def _resolve_declared_role(self, environment_role, data_purpose):
        declaration = provisioning.assert_strategy_declared_for_purpose(data_purpose)
        declaration = provisioning.load_declaration()
        roles = declaration.get("environment_roles") or {}
        entry = roles.get(environment_role)
        if not isinstance(entry, dict):
            raise ValidationError("DBGOV1_UNKNOWN_ENVIRONMENT_ROLE:%s" % (environment_role,))
        if entry.get("data_purpose") != data_purpose:
            raise ValidationError(
                "DBGOV1_ROLE_PURPOSE_MISMATCH:%s:%s" % (environment_role, data_purpose)
            )
        return declaration, entry

    @api.model
    def _register_database(
        self, *, db_name, environment_role, data_purpose, tenant_key="", dbfilter="", reason="", execution_id=""
    ):
        """Register one governed database in its declared initial lifecycle state."""
        self._assert_governance_principal()
        name = str(db_name or "").strip()
        if not name:
            raise ValidationError("DBGOV1_DATABASE_NAME_REQUIRED")
        declaration, entry = self._resolve_declared_role(environment_role, data_purpose)
        if self.sudo().with_context(active_test=False).search_count([("db_name", "=", name)]):
            raise ValidationError("DBGOV1_DATABASE_ALREADY_REGISTERED")
        strategy = entry.get("strategy")
        if strategy not in (declaration.get("strategies") or {}):
            raise ValidationError("DBGOV1_UNDECLARED_STRATEGY:%s" % (strategy,))
        record = self.sudo().with_context(sc_platform_database_managed=True).create([{
            "db_name": name,
            "dbfilter": str(dbfilter or ""),
            "environment_role": environment_role,
            "strategy": strategy,
            "data_purpose": data_purpose,
            "tenant_key": str(tenant_key or ""),
            "lifecycle_state": DATABASE_LIFECYCLE_INITIAL_STATE,
            "registered_by": self.env.uid,
            "registered_at": fields.Datetime.now(),
        }])
        return record._write_readback("register", reason=reason, execution_id=execution_id)

    @api.model
    def _apply_operation(self, db_name, operation, *, reason="", execution_id=""):
        """The only writer of the database lifecycle; fail closed on any other."""
        self._assert_governance_principal()
        record = self.sudo().search([("db_name", "=", str(db_name or "").strip())], limit=1)
        if not record:
            raise ValidationError("DBGOV1_DATABASE_NOT_REGISTERED:%s" % (db_name,))
        self.env.cr.execute(
            "SELECT id FROM sc_platform_database_registration WHERE id = %s FOR UPDATE NOWAIT",
            (record.id,),
        )
        record.invalidate_recordset()
        current = record.lifecycle_state
        try:
            target = resolve_operation_target_state(current, operation)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        record = record.sudo().with_context(
            sc_platform_database_managed=True, sc_platform_database_from_state=current
        )
        record.write({"lifecycle_state": target})
        record.invalidate_recordset(["lifecycle_state"])
        return record._write_readback(operation, reason=reason, execution_id=execution_id)

    @api.model
    def _resolve_entry(self, db_name):
        record = self.sudo().search([("db_name", "=", str(db_name or "").strip())], limit=1)
        if not record:
            raise ValidationError("DBGOV1_DATABASE_NOT_REGISTERED:%s" % (db_name,))
        return record

    @api.model
    def _assert_database_operational(self, db_name):
        """Fail closed unless the named database is registered and active."""
        record = self._resolve_entry(db_name)
        if record.lifecycle_state != "active":
            raise UserError(
                "DBGOV1_DATABASE_NOT_ACTIVE:%s:%s" % (record.db_name, record.lifecycle_state)
            )
        return record.readback()


class ScPlatformDatabaseOperation(models.Model):
    """Append-only audit row for one managed database operation."""

    _name = "sc.platform.database.operation"
    _description = "Platform Database Operation Audit"
    _order = "id desc"

    registration_id = fields.Many2one(
        "sc.platform.database.registration", required=True, ondelete="restrict", index=True
    )
    operation = fields.Char(required=True)
    from_state = fields.Char()
    to_state = fields.Char()
    actor_id = fields.Many2one("res.users", readonly=True)
    occurred_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    result = fields.Json(readonly=True)

    def write(self, vals):
        raise UserError("DBGOV1_DATABASE_OPERATION_APPEND_ONLY")

    def unlink(self):
        raise UserError("DBGOV1_DATABASE_OPERATION_APPEND_ONLY")


class ScPlatformMaintenanceAccess(models.Model):
    """Explicit, independently approved, audited maintenance authorization.

    A maintenance access authorizes a listed maintenance capability against one
    registered database for a bounded period. It is never a business data grant:
    ``grants_business_data_scope`` is a computed always-false fact, so operator
    maintenance work cannot become customer business record read.
    """

    _name = "sc.platform.maintenance.access"
    _description = "Platform Maintenance Access Authorization"
    _order = "id desc"

    name = fields.Char(required=True, readonly=True, default="New")
    registration_id = fields.Many2one(
        "sc.platform.database.registration", required=True, ondelete="restrict", index=True
    )
    capability = fields.Selection(
        [(capability, capability) for capability in MAINTENANCE_ACCESS_CAPABILITIES],
        required=True,
        readonly=True,
    )
    reason = fields.Char(required=True, readonly=True)
    requested_by = fields.Many2one("res.users", required=True, readonly=True)
    approved_by = fields.Many2one("res.users", readonly=True)
    state = fields.Selection(
        [
            ("requested", "Requested"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        default="requested",
        required=True,
        readonly=True,
        index=True,
    )
    valid_from = fields.Datetime(readonly=True)
    valid_until = fields.Datetime(readonly=True)
    # A maintenance capability that moves business data must name *which*
    # mechanism identity performs it and *which* subject it is allowed to
    # carry.  Both are facts the approver signs off on, so they are set at
    # request time and are never writable afterwards.
    operator_identity_key = fields.Char(
        readonly=True, help="Declared external id of the mechanism identity that executes the capability."
    )
    subject_checksum = fields.Char(
        readonly=True, help="Digest of the subject the approved capability may carry."
    )
    grants_business_data_scope = fields.Boolean(
        compute="_compute_grants_business_data_scope", readonly=True
    )

    def _compute_grants_business_data_scope(self):
        grants = maintenance_access_grants_business_data_scope()
        for record in self:
            record.grants_business_data_scope = grants

    def write(self, vals):
        raise UserError("DBGOV1_MAINTENANCE_ACCESS_STATE_MACHINE_ONLY")

    def unlink(self):
        raise UserError("DBGOV1_MAINTENANCE_ACCESS_APPEND_ONLY")

    @api.model
    def _write_state(self, record, values, operation):
        record.sudo().with_context(sc_platform_database_managed=True)._super_write(values)
        readback = {
            "access_id": record.id,
            "db_name": record.registration_id.db_name,
            "capability": record.capability,
            "operator_identity_key": record.operator_identity_key or "",
            "subject_checksum": record.subject_checksum or "",
            "state": record.state,
            "valid_until": fields.Datetime.to_string(record.valid_until)
            if record.valid_until
            else "",
            "grants_business_data_scope": maintenance_access_grants_business_data_scope(),
        }
        record.env["sc.platform.database.operation"].sudo().create([{
            "registration_id": record.registration_id.id,
            "operation": operation,
            "from_state": record.registration_id.lifecycle_state,
            "to_state": record.registration_id.lifecycle_state,
            "actor_id": record.env.uid,
            "result": readback,
        }])
        return readback

    def _super_write(self, values):
        return super().write(values)

    @api.model
    def _assert_governance_principal(self):
        """Same governed maintenance principal as the registration lifecycle."""
        self.env["sc.platform.database.registration"]._assert_governance_principal()

    @api.model
    def _request_access(self, db_name, capability, reason, operator_identity_key="", subject_checksum=""):
        """Open a maintenance authorization request; never self-approving."""
        self._assert_governance_principal()
        try:
            validate_maintenance_capability(capability)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        text = str(reason or "").strip()
        if not text:
            raise ValidationError("DBGOV1_MAINTENANCE_REASON_REQUIRED")
        operator_identity = str(operator_identity_key or "").strip()
        checksum = str(subject_checksum or "").strip()
        if capability == "migrate":
            # A data-moving capability without a named operator and a bound
            # subject digest would authorize "someone, with something".
            if not operator_identity:
                raise ValidationError("DBGOV1_MAINTENANCE_OPERATOR_REQUIRED")
            if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", operator_identity):
                raise ValidationError("DBGOV1_MAINTENANCE_OPERATOR_INVALID")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValidationError("DBGOV1_MAINTENANCE_SUBJECT_CHECKSUM_INVALID")
        registration = self.env["sc.platform.database.registration"]._resolve_entry(db_name)
        record = self.sudo().with_context(sc_platform_database_managed=True).create([{
            "name": "MA-%s-%s" % (registration.db_name, capability),
            "registration_id": registration.id,
            "capability": capability,
            "reason": text,
            "operator_identity_key": operator_identity,
            "subject_checksum": checksum,
            "requested_by": self.env.uid,
            "state": "requested",
        }])
        return self._write_state(record, {}, "maintenance_request")

    @api.model
    def _approve_access(self, access_id, *, validity_hours=None):
        """Approve a request under an independent security-admin identity.

        The approver is deliberately NOT required to be the platform maintenance
        principal: independence is the whole point. It must be a different user
        from the requester and must hold the independent security-admin group
        (a governed superuser is accepted, an arbitrary caller is not).
        """
        record = self.sudo().browse(int(access_id or 0)).exists()
        if not record:
            raise ValidationError("DBGOV1_MAINTENANCE_ACCESS_NOT_FOUND")
        if record.state != "requested":
            raise UserError("DBGOV1_MAINTENANCE_ACCESS_NOT_REQUESTED:%s" % (record.state,))
        approver = self.env.user
        if approver.id == record.requested_by.id:
            raise AccessError("DBGOV1_MAINTENANCE_APPROVER_MUST_BE_INDEPENDENT")
        if not approver.has_group(SECURITY_ADMIN_GROUP):
            raise AccessError("DBGOV1_MAINTENANCE_APPROVER_IDENTITY_REQUIRED")
        hours = int(validity_hours or MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS)
        if hours <= 0 or hours > MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS:
            raise ValidationError(
                "DBGOV1_MAINTENANCE_VALIDITY_OUT_OF_RANGE:%s" % (MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS,)
            )
        now = fields.Datetime.now()
        return self._write_state(
            record,
            {
                "state": "approved",
                "approved_by": approver.id,
                "valid_from": now,
                "valid_until": now + timedelta(hours=hours),
            },
            "maintenance_approve",
        )

    @api.model
    def _revoke_access(self, access_id):
        record = self.sudo().browse(int(access_id or 0)).exists()
        if not record:
            raise ValidationError("DBGOV1_MAINTENANCE_ACCESS_NOT_FOUND")
        if record.state not in ("requested", "approved"):
            raise UserError("DBGOV1_MAINTENANCE_ACCESS_NOT_ACTIVE:%s" % (record.state,))
        return self._write_state(record, {"state": "revoked"}, "maintenance_revoke")

    def business_data_scope_companies(self):
        """A maintenance access never contributes business company scope."""
        self.ensure_one()
        return self.env["res.company"].browse([])

    @api.model
    def _active_access(self, db_name, capability):
        """Return the covering approved access, or an empty recordset."""
        registration = self.env["sc.platform.database.registration"]._resolve_entry(db_name)
        now = fields.Datetime.now()
        return self.sudo().search([
            ("registration_id", "=", registration.id),
            ("capability", "=", capability),
            ("state", "=", "approved"),
            ("valid_from", "<=", now),
            ("valid_until", ">=", now),
        ], limit=1)

    @api.model
    def _approved_access_projection(self, *, db_name, capability):
        """Read-only projection of the covering approved maintenance access.

        The projection is what an executor may rely on: it names the approver,
        the requester, the bound operator identity, the bound subject digest and
        the validity window, so a caller can bind an approval to its own run
        instead of inventing one. It reads and never writes.
        """
        record = self._active_access(db_name, capability)
        if not record:
            return None
        return {
            "access_id": record.id,
            "db_name": record.registration_id.db_name,
            "tenant_key": record.registration_id.tenant_key or "",
            "capability": record.capability,
            "state": record.state,
            "operator_identity_key": record.operator_identity_key or "",
            "subject_checksum": record.subject_checksum or "",
            "approved_by": record.approved_by.login or "",
            "requested_by": record.requested_by.login or "",
            "valid_from": fields.Datetime.to_string(record.valid_from)
            if record.valid_from
            else "",
            "valid_until": fields.Datetime.to_string(record.valid_until)
            if record.valid_until
            else "",
        }

    @api.model
    def _assert_access_authorized(self, db_name, capability):
        """Fail closed unless an approved, in-window maintenance access covers it."""
        if not self._active_access(db_name, capability):
            raise AccessError(
                "DBGOV1_MAINTENANCE_ACCESS_NOT_AUTHORIZED:%s:%s" % (db_name, capability)
            )
        return True
