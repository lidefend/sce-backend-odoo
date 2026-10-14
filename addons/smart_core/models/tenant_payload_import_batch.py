from __future__ import annotations

import os

from odoo import SUPERUSER_ID, api, fields, models
from odoo.exceptions import UserError, ValidationError, AccessError

from odoo.addons.smart_core.utils.tenant_payload_v1 import (
    TenantPayloadError,
    validate_manifest,
)
from odoo.addons.smart_core.utils.tenant_payload_capability import (
    maintenance_capability_matches,
)
from odoo.addons.smart_core.security.data_space import (
    CUSTOMER_PURPOSE,
    validate_customer_registration,
    validate_non_customer_creation,
)


IMPORTER_GROUP = "smart_core.group_smart_core_tenant_payload_importer"


def _assert_signed_import_boundary(env):
    if not env.user.has_group(IMPORTER_GROUP):
        raise AccessError("TPV1_IMPORT_OPERATOR_REQUIRED")
    if not env.context.get("sc_tenant_payload_import"):
        raise UserError("TPV1_SIGNED_IMPORT_CONTEXT_REQUIRED")
    if env.registry.in_test_mode():
        return
    expected = str(
        os.environ.get("SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY", "") or ""
    )
    actual = str(
        env.context.get("sc_tenant_payload_maintenance_capability", "") or ""
    )
    if not maintenance_capability_matches(actual, expected):
        # R10-v2: an import context presented WITHOUT the signed maintenance
        # capability is an unauthorized access attempt, not a usage mistake —
        # spec tests assert AccessError here (context-missing stays UserError).
        raise AccessError("TPV1_SIGNED_MAINTENANCE_CAPABILITY_REQUIRED")


class ResCompany(models.Model):
    _inherit = "res.company"

    is_platform_bootstrap_company = fields.Boolean(
        string="Platform bootstrap company",
        default=False,
        readonly=True,
        help="Technical carrier for Odoo startup; it never represents a business tenant.",
    )


class ScDataSpaceSerialization(models.Model):
    """Transaction coordination only; never an ownership or permission fact.

    No user ACL or public mutation API. Rows outlive registration deletion so
    concurrent registration/re-registration always touches the same key.
    """

    _name = "sc.data.space.serialization"
    _description = "Data Space Registration Transaction Coordination"
    _log_access = False

    tenant_key = fields.Char(required=True)
    revision = fields.Integer(required=True, default=0)
    _sql_constraints = [
        ("tenant_key_unique", "unique(tenant_key)", "One transaction key per tenant."),
    ]


class ScTenantCompanyRegistration(models.Model):
    """Explicit binding between a tenant payload and a business company.

    Odoo's ``base.main_company`` remains a neutral bootstrap carrier. A
    user-data module must create and register a distinct business company
    through this boundary. Product and industry modules never manufacture a
    concrete tenant identity.
    """

    _name = "sc.tenant.company.registration"
    _description = "Tenant Company Registration"
    _order = "tenant_key, company_id"

    tenant_key = fields.Char(required=True, index=True, readonly=True)
    data_purpose = fields.Selection(
        [("customer", "Customer business"), ("demo", "Demonstration"), ("test", "Test")],
        default=CUSTOMER_PURPOSE,
        required=True,
        index=True,
        readonly=True,
        copy=False,
        help="Immutable purpose of this registered data space; unknown history stays customer data.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        readonly=True,
        ondelete="cascade",
    )
    source_module = fields.Char(required=True, readonly=True)
    source_external_key = fields.Char(required=True, readonly=True)
    active = fields.Boolean(default=True, required=True, readonly=True)

    _sql_constraints = [
        (
            "tenant_company_registration_company_uniq",
            "unique(company_id)",
            "A business company may only have one tenant registration.",
        ),
        (
            "tenant_company_registration_identity_uniq",
            "unique(tenant_key, source_external_key)",
            "A tenant company identity must be unique.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        _assert_signed_import_boundary(self.env)
        for values in vals_list:
            try:
                validate_customer_registration(values)
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
        # Explicitly defeat default_data_purpose from an RPC context.
        vals_list = [dict(values, data_purpose=CUSTOMER_PURPOSE) for values in vals_list]
        if any(
            str(values.get("source_module") or "").strip().startswith(("smart_", "sc_"))
            for values in vals_list
        ):
            raise UserError("TPV1_PRODUCT_MODULE_CANNOT_REGISTER_BUSINESS_COMPANY")
        # A newly provisioned business company is intentionally not yet in the
        # import operator's company scope.  The importer group plus the
        # explicit payload-import context authorize this one registration
        # boundary; use sudo only to verify the immutable bootstrap marker.
        companies = self.env["res.company"].sudo().browse(
            [int(values.get("company_id") or 0) for values in vals_list]
        ).exists()
        if len(companies) != len(vals_list) or any(
            company.is_platform_bootstrap_company for company in companies
        ):
            raise UserError("TPV1_PLATFORM_BOOTSTRAP_COMPANY_CANNOT_REGISTER")
        registrations = super().create(vals_list)
        registrations._after_tenant_company_registration()
        self.env.registry.clear_cache()
        return registrations

    @api.constrains("tenant_key", "data_purpose")
    def _check_tenant_purpose(self):
        self._serialize_tenant_keys(self.mapped("tenant_key"))
        for registration in self:
            if self.sudo().with_context(active_test=False).search_count([
                ("tenant_key", "=", registration.tenant_key),
                ("data_purpose", "!=", registration.data_purpose),
            ]):
                raise ValidationError("DATA_SPACE_TENANT_PURPOSE_CONFLICT")

    @api.model
    def _serialize_tenant_keys(self, tenant_keys):
        # A real row write is necessary under REPEATABLE READ. An advisory
        # lock followed by a query would still see an old transaction snapshot.
        # Serialization failures deliberately propagate to the transaction
        # owner; never retry inside this already-failed transaction.
        for tenant_key in sorted(set(tenant_keys)):
            self.env.cr.execute("""
                INSERT INTO sc_data_space_serialization (tenant_key, revision)
                VALUES (%s, 1)
                ON CONFLICT (tenant_key) DO UPDATE
                SET revision = sc_data_space_serialization.revision + 1
            """, [tenant_key])

    def _assert_non_customer_maintenance(self, *, purpose, tenant_key):
        """One maintenance-principal rule for every non-customer onboarding entry."""
        try:
            validate_non_customer_creation(
                uid=self.env.uid, superuser_id=SUPERUSER_ID, su=self.env.su,
                purpose=purpose, tenant_key=tenant_key,
            )
        except PermissionError as exc:
            raise AccessError(str(exc)) from exc
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def _open_non_customer_registration(self, *, tenant_key, purpose, company_id):
        """Bind an immutable ownership anchor to an already verified company."""
        registration = super().create([{
            "tenant_key": tenant_key.strip(),
            "data_purpose": purpose,
            "company_id": int(company_id),
            "source_module": "smart_core",
            "source_external_key": str(company_id),
            "active": True,
        }])
        registration._after_tenant_company_registration()
        self.env.registry.clear_cache()
        return registration

    @api.model
    def _create_non_customer_space(self, *, tenant_key, purpose, company_name):
        """Maintenance-only creation; never relabel an existing company.

        Private ORM entry, unavailable over RPC. A sudo product-admin
        environment is explicitly insufficient. Fixtures use this entry and
        keep the resulting registration as their immutable ownership anchor.
        """
        self._assert_non_customer_maintenance(purpose=purpose, tenant_key=tenant_key)
        if not isinstance(company_name, str) or not company_name.strip():
            raise ValidationError("DATA_SPACE_COMPANY_NAME_REQUIRED")
        # Roll back the company too if registration or product defaults fail.
        with self.env.cr.savepoint():
            company = self.env["res.company"].create({
                "name": company_name.strip(),
                "is_platform_bootstrap_company": False,
            })
            return self._open_non_customer_registration(
                tenant_key=tenant_key, purpose=purpose, company_id=company.id)

    @api.model
    def _register_non_customer_space(self, *, tenant_key, purpose, company_id):
        """Maintenance-only onboarding of an EXISTING non-bootstrap company.

        Same maintenance principal and immutable anchor as creation, with the
        guardrails that keep "reuse" from becoming "relabel": the platform
        bootstrap company can never be registered, and a company that already
        owns a registration is refused instead of being re-purposed.
        """
        self._assert_non_customer_maintenance(purpose=purpose, tenant_key=tenant_key)
        company = self.env["res.company"].sudo().browse(int(company_id or 0)).exists()
        if not company or company.is_platform_bootstrap_company:
            raise ValidationError("DATA_SPACE_BUSINESS_COMPANY_REQUIRED")
        if self.sudo().with_context(active_test=False).search_count(
                [("company_id", "=", company.id)]):
            raise ValidationError("DATA_SPACE_COMPANY_ALREADY_REGISTERED")
        with self.env.cr.savepoint():
            return self._open_non_customer_registration(
                tenant_key=tenant_key, purpose=purpose, company_id=company.id)

    def _after_tenant_company_registration(self):
        """Extension point for product modules' neutral company defaults."""
        return True

    @api.model
    def resolve_registered_company(self, company_id, *, require_active=True):
        company = self.env["res.company"].browse(int(company_id or 0)).exists()
        if (
            not company
            or company not in self.env.user.company_ids
            or company.is_platform_bootstrap_company
        ):
            raise UserError("TPV1_REGISTERED_BUSINESS_COMPANY_REQUIRED")
        domain = [("company_id", "=", company.id)]
        if require_active:
            domain.append(("active", "=", True))
        registration = self.sudo().search(domain, limit=1)
        if not registration:
            raise UserError("TPV1_REGISTERED_BUSINESS_COMPANY_REQUIRED")
        return registration

    def write(self, vals):
        if set(vals) - {"active"}:
            raise UserError("TPV1_COMPANY_REGISTRATION_IDENTITY_IMMUTABLE")
        _assert_signed_import_boundary(self.env)
        result = super().write(vals)
        self.env.registry.clear_cache()
        return result

    def unlink(self):
        if not self.env.context.get("allow_audited_tenant_destroy"):
            raise UserError("TPV1_COMPANY_REGISTRATION_IMMUTABLE")
        _assert_signed_import_boundary(self.env)
        result = super().unlink()
        self.env.registry.clear_cache()
        return result


class ScTenantPayloadAdapter(models.AbstractModel):
    _name = "sc.tenant.payload.adapter"
    _description = "Product-neutral tenant payload adapter protocol"

    @api.model
    def assert_import_operator(self):
        _assert_signed_import_boundary(self.env)

    @api.model
    def get_adapter(self, tenant_key):
        """Customer modules extend this method and delegate unknown tenants to super()."""
        self.assert_import_operator()
        raise UserError("TPV1_CUSTOMER_ADAPTER_NOT_FOUND")

    @api.model
    def validate_payload_semantics(self, tenant_key, payload_root, manifest):
        """Customer modules may fail closed on cross-record business semantics."""
        self.assert_import_operator()
        return {
            "schema_version": "tenant_payload_semantic_validation.v1",
            "status": "PASS",
            "tenant_key": tenant_key,
        }


class ScTenantPayloadExternalIdentity(models.Model):
    _name = "sc.tenant.payload.external.identity"
    _description = "Stable external identity for tenant payload imports"
    _order = "tenant_key, resource, external_key"

    tenant_key = fields.Char(required=True, index=True, readonly=True)
    resource = fields.Char(required=True, index=True, readonly=True)
    external_key = fields.Char(required=True, index=True, readonly=True)
    model_name = fields.Char(required=True, index=True, readonly=True)
    res_id = fields.Integer(required=True, index=True, readonly=True)
    content_checksum = fields.Char(required=True, index=True, readonly=True)
    company_id = fields.Many2one("res.company", index=True, readonly=True)
    batch_id = fields.Many2one("sc.tenant.payload.import.batch", required=True, index=True, readonly=True)

    _sql_constraints = [
        (
            "tenant_payload_external_key_unique",
            "unique(tenant_key, resource, external_key)",
            "A tenant payload external key must identify exactly one record.",
        ),
        (
            "tenant_payload_external_res_id_positive",
            "check(res_id > 0)",
            "A tenant payload external identity must reference a positive record id.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        _assert_signed_import_boundary(self.env)
        return super().create(vals_list)

    def write(self, vals):
        allowed = {"content_checksum", "batch_id"}
        if set(vals) - allowed:
            raise UserError("TPV1_EXTERNAL_IDENTITY_IMMUTABLE")
        _assert_signed_import_boundary(self.env)
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get("allow_audited_tenant_destroy"):
            raise UserError("TPV1_EXTERNAL_IDENTITY_IMMUTABLE")
        return super().unlink()


class ScTenantPayloadImportBatch(models.Model):
    _name = "sc.tenant.payload.import.batch"
    _description = "Tenant payload import batch"
    _order = "create_date desc, id desc"

    payload_id = fields.Char(required=True, index=True, readonly=True)
    tenant_key = fields.Char(required=True, index=True, readonly=True)
    payload_version = fields.Char(readonly=True)  # legacy compatibility; no payload bytes are stored
    schema_version = fields.Char(required=True, readonly=True)
    payload_hash = fields.Char(required=True, index=True, readonly=True)
    source_key = fields.Char(index=True, readonly=True)
    source_snapshot_id = fields.Char(required=True, index=True, readonly=True, default="legacy-unresolved")
    product_interface_version = fields.Char(required=True, readonly=True, default="1")
    customer_module = fields.Char(required=True, readonly=True, default="legacy-unresolved")
    customer_module_version = fields.Char(required=True, readonly=True, default="legacy-unresolved")
    product_image_digest = fields.Char(readonly=True)
    customer_module_digest = fields.Char(readonly=True)
    signature_key_id = fields.Char(readonly=True)
    # Only redacted control metadata is retained; records, amounts, and relationships are excluded.
    manifest_json = fields.Json(required=True, readonly=True)
    state = fields.Selection(
        [
            ("validated", "Validated"),
            ("planned", "Planned"),
            ("importing", "Importing"),
            ("interrupted", "Interrupted"),
            ("verifying", "Verifying"),
            ("completed", "Completed"),
            ("failed", "Failed"),
            ("rolled_back", "Rolled back"),
        ],
        required=True,
        default="validated",
        index=True,
        readonly=True,
    )
    checkpoint = fields.Json(default=dict, readonly=True)
    created_count = fields.Integer(default=0, readonly=True)
    updated_count = fields.Integer(default=0, readonly=True)
    skipped_count = fields.Integer(default=0, readonly=True)
    conflict_count = fields.Integer(default=0, readonly=True)
    warning_count = fields.Integer(default=0, readonly=True)
    filestore_count = fields.Integer(default=0, readonly=True)
    # Legacy counters retained for upgrade compatibility.
    imported_count = fields.Integer(default=0, readonly=True)
    failed_count = fields.Integer(default=0, readonly=True)
    error_summary = fields.Text(readonly=True)
    acceptance_report = fields.Json(default=dict, readonly=True)
    operator_id = fields.Many2one("res.users", required=True, readonly=True, default=lambda self: self.env.user)
    started_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        ("tenant_payload_id_unique", "unique(tenant_key, payload_id)", "A tenant payload may only create one import batch."),
        ("tenant_payload_hash_unique", "unique(tenant_key, payload_hash)", "A tenant payload checksum may only be imported once."),
        (
            "tenant_payload_counts_non_negative",
            "check(created_count >= 0 and updated_count >= 0 and skipped_count >= 0 and conflict_count >= 0 and warning_count >= 0 and filestore_count >= 0)",
            "Import counters cannot be negative.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        _assert_signed_import_boundary(self.env)
        normalized = []
        for vals in vals_list:
            item = dict(vals)
            manifest = item.get("manifest_json")
            try:
                validate_manifest(manifest, expected_tenant_key=item.get("tenant_key"))
            except TenantPayloadError as exc:
                raise ValidationError(str(exc)) from exc
            redacted_manifest = {
                key: manifest[key]
                for key in (
                    "schema_version",
                    "payload_id",
                    "tenant_key",
                    "customer_module",
                    "customer_module_version",
                    "product_interface_version",
                    "source_snapshot_id",
                    "source_database_fingerprint",
                    "created_at_utc",
                    "filestore_file_count",
                    "filestore_bytes",
                    "payload_checksum",
                    "signature_algorithm",
                    "signature_key_id",
                )
            }
            item.update(
                {
                    "payload_id": manifest["payload_id"],
                    "tenant_key": manifest["tenant_key"],
                    "schema_version": manifest["schema_version"],
                    "payload_hash": manifest["payload_checksum"],
                    "source_snapshot_id": manifest["source_snapshot_id"],
                    "product_interface_version": manifest["product_interface_version"],
                    "customer_module": manifest["customer_module"],
                    "customer_module_version": manifest["customer_module_version"],
                    "signature_key_id": manifest["signature_key_id"],
                    "manifest_json": redacted_manifest,
                    "state": "validated",
                    "operator_id": self.env.user.id,
                }
            )
            normalized.append(item)
        return super().create(normalized)

    def _assert_operator(self):
        _assert_signed_import_boundary(self.env)

    def action_plan(self, report):
        self._assert_operator()
        for batch in self:
            if batch.state != "validated":
                raise UserError("TPV1_STATE_INVALID_FOR_PLAN")
            batch.write({"state": "planned", "acceptance_report": report or {}, "error_summary": False})
        return True

    def action_start(self, *, allow_failed=False):
        self._assert_operator()
        for batch in self:
            allowed = {"planned", "interrupted"} | ({"failed"} if allow_failed else set())
            if batch.state not in allowed:
                raise UserError("TPV1_STATE_INVALID_FOR_IMPORT")
            values = {"state": "importing", "error_summary": False}
            if not batch.started_at:
                values["started_at"] = fields.Datetime.now()
            batch.write(values)
        return True

    def update_checkpoint(self, *, checkpoint, counters):
        self._assert_operator()
        allowed = {
            "created_count",
            "updated_count",
            "skipped_count",
            "conflict_count",
            "warning_count",
            "filestore_count",
        }
        if set(counters) - allowed:
            raise UserError("TPV1_COUNTER_INVALID")
        for batch in self:
            if batch.state != "importing":
                raise UserError("TPV1_CHECKPOINT_STATE_INVALID")
            batch.write({"checkpoint": checkpoint or {}, **counters})
        return True

    def action_interrupt(self, rule="TPV1_IMPORT_INTERRUPTED"):
        self._assert_operator()
        for batch in self:
            if batch.state not in {"importing", "verifying"}:
                raise UserError("TPV1_STATE_INVALID_FOR_INTERRUPT")
            batch.write({"state": "interrupted", "error_summary": str(rule)})
        return True

    def action_verify(self):
        self._assert_operator()
        for batch in self:
            if batch.state != "importing":
                raise UserError("TPV1_STATE_INVALID_FOR_VERIFY")
            batch.write({"state": "verifying"})
        return True

    def action_complete(self, acceptance_report):
        self._assert_operator()
        for batch in self:
            if batch.state != "verifying" or batch.conflict_count:
                raise UserError("TPV1_STATE_INVALID_FOR_COMPLETE")
            batch.write(
                {
                    "state": "completed",
                    "completed_at": fields.Datetime.now(),
                    "acceptance_report": acceptance_report or {},
                    "warning_count": max(
                        batch.warning_count,
                        int((acceptance_report or {}).get("verification_warning_count", 0)),
                    ),
                    "error_summary": False,
                }
            )
        return True

    def action_complete_after_reverify(self, acceptance_report):
        """Close a fully written batch whose first final verification failed.

        The prior safe rule is retained inside the acceptance report so the
        recovery remains auditable, while error_summary continues to describe
        only the active state.
        """
        self._assert_operator()
        for batch in self:
            if batch.state != "failed" or batch.conflict_count:
                raise UserError("TPV1_STATE_INVALID_FOR_REVERIFY_COMPLETE")
            report = dict(acceptance_report or {})
            report["recovered_from_error_rule"] = batch.error_summary or "TPV1_PRIOR_VERIFY_FAILED"
            batch.write(
                {
                    "state": "completed",
                    "completed_at": fields.Datetime.now(),
                    "acceptance_report": report,
                    "warning_count": max(batch.warning_count, int(report.get("verification_warning_count", 0))),
                    "error_summary": False,
                }
            )
        return True

    def record_filestore_reconciliation(self, report):
        self._assert_operator()
        for batch in self:
            if batch.state != "completed":
                raise UserError("TPV1_STATE_INVALID_FOR_FILESTORE_RECONCILE")
            acceptance = dict(batch.acceptance_report or {})
            acceptance["filestore_reconciliation"] = report or {}
            batch.write({"acceptance_report": acceptance})
        return True

    def action_fail(self, error_rule):
        self._assert_operator()
        for batch in self:
            if batch.state in {"completed", "rolled_back"}:
                raise UserError("TPV1_STATE_INVALID_FOR_FAIL")
            batch.write({"state": "failed", "error_summary": str(error_rule or "TPV1_IMPORT_FAILED")})
        return True

    def action_mark_rolled_back(self, acceptance_report=None):
        self._assert_operator()
        for batch in self:
            if batch.state != "failed":
                raise UserError("TPV1_STATE_INVALID_FOR_ROLLBACK")
            batch.write(
                {
                    "state": "rolled_back",
                    "acceptance_report": acceptance_report or {},
                    "completed_at": fields.Datetime.now(),
                }
            )
        return True

    def unlink(self):
        if not self.env.context.get("allow_audited_tenant_destroy"):
            raise UserError("TPV1_BATCH_IMMUTABLE")
        return super().unlink()
