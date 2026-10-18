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
    DATABASE_DATA_PURPOSE_LABELS,
    DATABASE_LIFECYCLE_INITIAL_STATE,
    DATABASE_LIFECYCLE_STATE_LABELS,
    DATABASE_LIFECYCLE_STATES,
    MAINTENANCE_ACCESS_CAPABILITIES,
    MAINTENANCE_ACCESS_CAPABILITY_LABELS,
    MAINTENANCE_ACCESS_OPERATIONS,
    MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS,
    MAINTENANCE_ACCESS_STATE_LABELS,
    maintenance_access_grants_business_data_scope,
    resolve_operation_target_state,
    validate_database_governance_principal,
    validate_maintenance_capability,
    validate_maintenance_evidence,
    validate_maintenance_operations,
)
from odoo.addons.smart_core.security.platform_admin import (
    SECURITY_ADMIN_GROUP,
    user_is_platform_control_admin,
    user_is_security_admin,
)


class ScPlatformDatabaseRegistration(models.Model):
    """One governed database: role, tenant key, strategy, purpose, lifecycle."""

    _name = "sc.platform.database.registration"
    _description = "Platform Database Registration"
    _rec_name = "label"
    _order = "db_name"

    db_name = fields.Char(string="物理库（内部）", required=True, index=True, readonly=True)
    dbfilter = fields.Char(
        string="数据库过滤规则",
        readonly=True,
        help="Declared dbfilter; empty means the database name.",
    )
    environment_role = fields.Char(string="环境职责", required=True, index=True, readonly=True)
    strategy = fields.Char(string="数据库策略", required=True, readonly=True)
    data_purpose = fields.Selection(
        [(key, label) for key, label in DATABASE_DATA_PURPOSE_LABELS.items()],
        string="数据用途",
        required=True,
        readonly=True,
        index=True,
    )
    tenant_key = fields.Char(string="租户标识", readonly=True)
    lifecycle_state = fields.Selection(
        [(state, DATABASE_LIFECYCLE_STATE_LABELS[state]) for state in DATABASE_LIFECYCLE_STATES],
        string="生命周期",
        default=DATABASE_LIFECYCLE_INITIAL_STATE,
        required=True,
        readonly=True,
        index=True,
    )
    label = fields.Char(string="登记名称", compute="_compute_label")
    registered_by = fields.Many2one("res.users", string="登记人", readonly=True)
    registered_at = fields.Datetime(string="登记时间", readonly=True)
    last_operation = fields.Char(string="最近操作", readonly=True)
    last_operation_at = fields.Datetime(string="最近操作时间", readonly=True)
    last_readback = fields.Json(string="最近回读", readonly=True)
    operation_ids = fields.One2many(
        "sc.platform.database.operation",
        "registration_id",
        string="操作记录",
        readonly=True,
    )
    maintenance_access_ids = fields.One2many(
        "sc.platform.maintenance.access",
        "registration_id",
        string="维护访问",
        readonly=True,
    )

    @api.depends("tenant_key", "environment_role", "db_name", "data_purpose", "lifecycle_state")
    def _compute_label(self):
        for record in self:
            identity = record.tenant_key or record.environment_role or record.db_name
            purpose = DATABASE_DATA_PURPOSE_LABELS.get(record.data_purpose, record.data_purpose or "")
            state = DATABASE_LIFECYCLE_STATE_LABELS.get(record.lifecycle_state, record.lifecycle_state or "")
            parts = [part for part in (identity, purpose, state) if part]
            record.label = " · ".join(parts) or record.db_name

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
    _rec_name = "access_label"
    _order = "id desc"

    name = fields.Char(string="内部编号", required=True, readonly=True, default="New")
    registration_id = fields.Many2one(
        "sc.platform.database.registration",
        string="数据库登记",
        required=True,
        ondelete="restrict",
        index=True,
    )
    capability = fields.Selection(
        [
            (capability, MAINTENANCE_ACCESS_CAPABILITY_LABELS[capability])
            for capability in MAINTENANCE_ACCESS_CAPABILITIES
        ],
        string="维护能力",
        required=True,
        readonly=True,
    )
    reason = fields.Char(string="事由", required=True, readonly=True)
    # The authority the request rests on.  It is declared by the requester and
    # is immutable afterwards, because it is one of the facts the approver
    # signs off on: an authorization whose evidence could be rewritten after
    # approval would let the approval mean something else than what was read.
    evidence_reference = fields.Char(
        string="授权依据",
        required=True,
        readonly=True,
        help="Reference to the authorization this maintenance access rests on.",
    )
    requested_by = fields.Many2one("res.users", string="申请人", required=True, readonly=True)
    approved_by = fields.Many2one("res.users", string="审批人", readonly=True)
    state = fields.Selection(
        [
            (state, MAINTENANCE_ACCESS_STATE_LABELS[state])
            for state in ("requested", "approved", "rejected", "expired", "revoked")
        ],
        string="状态",
        default="requested",
        required=True,
        readonly=True,
        index=True,
    )
    valid_from = fields.Datetime(string="生效时间", readonly=True)
    valid_until = fields.Datetime(string="失效时间", readonly=True)
    # A maintenance capability that moves business data must name *which*
    # mechanism identity performs it and *which* subject it is allowed to
    # carry.  Both are facts the approver signs off on, so they are set at
    # request time and are never writable afterwards.
    operator_identity_key = fields.Char(
        string="执行身份",
        readonly=True, help="Declared external id of the mechanism identity that executes the capability."
    )
    subject_checksum = fields.Char(
        string="主体摘要",
        readonly=True, help="Digest of the subject the approved capability may carry."
    )
    # A maintenance access authorizes an explicit *operation set*, never an
    # implied one.  The names are the operations the governed duty entries
    # execute, so an approval that names only the payload import can never cover
    # creating a service identity as well.
    authorized_operations = fields.Json(
        string="授权操作",
        readonly=True,
        help="Declared maintenance operations this access authorizes, e.g. provision, grant.",
    )
    decision_note = fields.Char(
        string="审批说明",
        readonly=True, help="Why this access was rejected or revoked, as recorded by its decider."
    )
    grants_business_data_scope = fields.Boolean(
        string="授予业务数据范围",
        compute="_compute_grants_business_data_scope",
        readonly=True,
    )
    access_label = fields.Char(string="维护事项", compute="_compute_access_label")

    @api.depends("capability", "state", "name", "registration_id.label", "registration_id.db_name")
    def _compute_access_label(self):
        for record in self:
            capability = MAINTENANCE_ACCESS_CAPABILITY_LABELS.get(
                record.capability, record.capability or ""
            )
            registration = record.registration_id.label or record.registration_id.db_name
            state = MAINTENANCE_ACCESS_STATE_LABELS.get(record.state, record.state or "")
            parts = [part for part in (capability, registration, state) if part]
            record.access_label = " · ".join(parts) or record.name

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
            "tenant_key": record.registration_id.tenant_key or "",
            "capability": record.capability,
            "reason": record.reason,
            "evidence_reference": record.evidence_reference or "",
            # Who asked and who decided are part of the decision's own
            # readback, not a separate lookup: an auditor reads one row and sees
            # the independence the state machine asserted.
            "requested_by": record.requested_by.login or "",
            "approved_by": record.approved_by.login or "",
            "operator_identity_key": record.operator_identity_key or "",
            "subject_checksum": record.subject_checksum or "",
            "authorized_operations": list(record.authorized_operations or []),
            "decision_note": record.decision_note or "",
            "state": record.state,
            "valid_from": fields.Datetime.to_string(record.valid_from)
            if record.valid_from
            else "",
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
    def _create_access_request(
        self,
        *,
        db_name,
        capability,
        reason,
        requester_id,
        evidence_reference="",
        operator_identity_key="",
        subject_checksum="",
        operations=None,
    ):
        """Create one ``requested`` access row; it authorizes nothing yet.

        The requester is an input fact, not a guess: the governed shell entry
        passes its own principal, and the product entry passes the identity it
        verified from the authenticated session.  Either way the row is born
        ``requested``, and only an independent security administrator can move
        it out of that state.
        """
        try:
            validate_maintenance_capability(capability)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        text = str(reason or "").strip()
        if not text:
            raise ValidationError("DBGOV1_MAINTENANCE_REASON_REQUIRED")
        try:
            evidence = validate_maintenance_evidence(evidence_reference)
        except ValueError as error:
            raise ValidationError(str(error)) from error
        operator_identity = str(operator_identity_key or "").strip()
        checksum = str(subject_checksum or "").strip()
        requester = self.env["res.users"].sudo().browse(int(requester_id or 0)).exists()
        if not requester or not requester.active:
            raise ValidationError("DBGOV1_MAINTENANCE_REQUESTER_REQUIRED")
        declared_operations = list(operations or [])
        if capability == "migrate":
            # A data-moving capability without a named operator, a bound subject
            # digest and an explicit operation set would authorize "someone,
            # with something, to do whatever the capability implies".
            if not operator_identity:
                raise ValidationError("DBGOV1_MAINTENANCE_OPERATOR_REQUIRED")
            if not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", operator_identity):
                raise ValidationError("DBGOV1_MAINTENANCE_OPERATOR_INVALID")
            if not re.fullmatch(r"[0-9a-f]{64}", checksum):
                raise ValidationError("DBGOV1_MAINTENANCE_SUBJECT_CHECKSUM_INVALID")
            try:
                declared_operations = list(validate_maintenance_operations(operations))
            except ValueError as error:
                raise ValidationError(str(error)) from error
        elif declared_operations:
            try:
                declared_operations = list(validate_maintenance_operations(operations))
            except ValueError as error:
                raise ValidationError(str(error)) from error
        registration = self.env["sc.platform.database.registration"]._resolve_entry(db_name)
        record = self.sudo().with_context(sc_platform_database_managed=True).create([{
            "name": "MA-%s-%s" % (registration.db_name, capability),
            "registration_id": registration.id,
            "capability": capability,
            "reason": text,
            "evidence_reference": evidence,
            "operator_identity_key": operator_identity,
            "subject_checksum": checksum,
            "authorized_operations": declared_operations,
            "requested_by": requester.id,
            "state": "requested",
        }])
        return self._write_state(record, {}, "maintenance_request")

    @api.model
    def _request_access(
        self,
        db_name,
        capability,
        reason,
        evidence_reference="",
        operator_identity_key="",
        subject_checksum="",
        operations=None,
        requester_id=None,
    ):
        """Open a maintenance authorization request; never self-approving.

        The governed principal that executes this entry is not necessarily the
        identity that asks for the maintenance: the shell runs as the platform
        superuser while the requester is a named platform administrator.  The
        requester is therefore an explicit input rather than an assumption, and
        an entry that names no one inherits the executing principal -- which the
        requester check refuses when that carrier is inactive.
        """
        self._assert_governance_principal()
        return self._create_access_request(
            db_name=db_name,
            capability=capability,
            reason=reason,
            requester_id=requester_id or self.env.uid,
            evidence_reference=evidence_reference,
            operator_identity_key=operator_identity_key,
            subject_checksum=subject_checksum,
            operations=operations,
        )

    @api.model
    def _assert_decision_authority(self, record=None):
        """Verify the decision identity on the server, never from a payload.

        An approval, a rejection and an expiry are decided by an independent
        security administrator.  The identity is read from the executing
        principal -- never from a caller-supplied field -- and independence from
        the requester is asserted here, so no entry may hand itself the
        permission it asked for.
        """
        decider = self.env.user
        if record is not None and decider.id == record.requested_by.id:
            raise AccessError("DBGOV1_MAINTENANCE_APPROVER_MUST_BE_INDEPENDENT")
        if not decider.has_group(SECURITY_ADMIN_GROUP):
            raise AccessError("DBGOV1_MAINTENANCE_APPROVER_IDENTITY_REQUIRED")
        return decider

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
        approver = self._assert_decision_authority(record)
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
    def _reject_access(self, access_id, note=""):
        """Refuse a request, with the decision recorded on the request itself."""
        record = self.sudo().browse(int(access_id or 0)).exists()
        if not record:
            raise ValidationError("DBGOV1_MAINTENANCE_ACCESS_NOT_FOUND")
        if record.state != "requested":
            raise UserError("DBGOV1_MAINTENANCE_ACCESS_NOT_REQUESTED:%s" % (record.state,))
        self._assert_decision_authority(record)
        text = str(note or "").strip()
        if not text:
            raise ValidationError("DBGOV1_MAINTENANCE_REJECTION_REASON_REQUIRED")
        return self._write_state(
            record, {"state": "rejected", "decision_note": text}, "maintenance_reject"
        )

    @api.model
    def _revoke_access(self, access_id, note=""):
        record = self.sudo().browse(int(access_id or 0)).exists()
        if not record:
            raise ValidationError("DBGOV1_MAINTENANCE_ACCESS_NOT_FOUND")
        if record.state not in ("requested", "approved"):
            raise UserError("DBGOV1_MAINTENANCE_ACCESS_NOT_ACTIVE:%s" % (record.state,))
        self._assert_decision_authority(record)
        return self._write_state(
            record,
            {"state": "revoked", "decision_note": str(note or "").strip()},
            "maintenance_revoke",
        )

    @api.model
    def _expire_accesses(self, db_name=None):
        """Move every elapsed approval to ``expired``; one audit row each.

        An elapsed access already authorizes nothing (``_active_access`` is
        bounded by the validity window), so this entry never widens authority:
        it stops a stale row from *reading* as an approval.
        """
        self._assert_decision_authority()
        domain = [("state", "=", "approved"), ("valid_until", "<", fields.Datetime.now())]
        if db_name:
            domain.append(
                ("registration_id", "=", self.env["sc.platform.database.registration"]._resolve_entry(db_name).id)
            )
        records = self.sudo().search(domain, order="id")
        return [
            self._write_state(record, {"state": "expired"}, "maintenance_expire")
            for record in records
        ]

    def business_data_scope_companies(self):
        """A maintenance access never contributes business company scope."""
        self.ensure_one()
        return self.env["res.company"].browse([])

    # ------------------------------------------------------------------
    # product entries: request / approve / reject / revoke / expire / query
    # ------------------------------------------------------------------
    @api.model
    def request_access(
        self,
        db_name,
        capability,
        reason,
        evidence_reference="",
        operator_identity_key="",
        subject_checksum="",
        authorized_operations=None,
    ):
        """Open a maintenance request as a verified platform administrator.

        Requesting grants nothing: the row is born ``requested`` and the query
        projection reports it as such.  The requester recorded on the row is the
        authenticated principal, so the independence rule can never be satisfied
        by a caller that names someone else as the requester.
        """
        if not user_is_platform_control_admin(self.env.user):
            raise AccessError("DBGOV1_MAINTENANCE_REQUESTER_IDENTITY_REQUIRED")
        return self._create_access_request(
            db_name=db_name,
            capability=capability,
            reason=reason,
            requester_id=self.env.user.id,
            evidence_reference=evidence_reference,
            operator_identity_key=operator_identity_key,
            subject_checksum=subject_checksum,
            operations=authorized_operations,
        )

    @api.model
    def approve_access(self, access_id, validity_hours=None):
        """Approve a request; the approver is the verified principal."""
        return self._approve_access(access_id, validity_hours=validity_hours)

    @api.model
    def reject_access(self, access_id, note=""):
        """Reject a request, recording why on the request itself."""
        return self._reject_access(access_id, note)

    @api.model
    def revoke_access(self, access_id, note=""):
        """Revoke a requested or approved access."""
        return self._revoke_access(access_id, note)

    @api.model
    def expire_accesses(self, db_name=None):
        """Retire every elapsed approval so it cannot read as an approval."""
        return self._expire_accesses(db_name)

    @api.model
    def access_projection(self, db_name=None, state=None, limit=0):
        """Read-only query entry over the maintenance authorization ledger."""
        if not (user_is_platform_control_admin(self.env.user) or user_is_security_admin(self.env.user)):
            raise AccessError("DBGOV1_MAINTENANCE_READER_IDENTITY_REQUIRED")
        domain = []
        if db_name:
            domain.append(
                ("registration_id", "=", self.env["sc.platform.database.registration"]._resolve_entry(db_name).id)
            )
        if state:
            domain.append(("state", "=", state))
        records = self.sudo().search(domain, order="id desc", limit=int(limit or 0) or None)
        return [self._projection(record) for record in records]

    @api.model
    def _projection(self, record):
        return {
            "access_id": record.id,
            "db_name": record.registration_id.db_name,
            "tenant_key": record.registration_id.tenant_key or "",
            "capability": record.capability,
            "state": record.state,
            "reason": record.reason,
            "evidence_reference": record.evidence_reference or "",
            "operator_identity_key": record.operator_identity_key or "",
            "subject_checksum": record.subject_checksum or "",
            "authorized_operations": list(record.authorized_operations or []),
            "approved_by": record.approved_by.login or "",
            "requested_by": record.requested_by.login or "",
            "decision_note": record.decision_note or "",
            "valid_from": fields.Datetime.to_string(record.valid_from)
            if record.valid_from
            else "",
            "valid_until": fields.Datetime.to_string(record.valid_until)
            if record.valid_until
            else "",
            "grants_business_data_scope": maintenance_access_grants_business_data_scope(),
        }

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

        ``authorized_operations`` is part of the projection on purpose: an
        executor must prove that *this* operation was approved, not that some
        operation under the same capability was.
        """
        record = self._active_access(db_name, capability)
        if not record:
            return None
        return self._projection(record)

    @api.model
    def _assert_access_authorized(self, db_name, capability):
        """Fail closed unless an approved, in-window maintenance access covers it."""
        if not self._active_access(db_name, capability):
            raise AccessError(
                "DBGOV1_MAINTENANCE_ACCESS_NOT_AUTHORIZED:%s:%s" % (db_name, capability)
            )
        return True
