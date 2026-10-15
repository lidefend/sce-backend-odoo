"""Platform database governance: real principals, real boundary, no bypass.

These cases exercise the platform capability rather than its source text: one
governed database registration, its managed lifecycle entries, and the separate
maintenance authorization. The two boundaries the owner named are asserted
directly -- database isolation never replaces record permission, and platform
database management never grants customer business data read.
"""
import os
from unittest.mock import patch

from odoo import SUPERUSER_ID, fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install", "platform_database_governance")
class TestPlatformDatabaseGovernance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A customer-purpose registration is a signed maintenance import, not a
        # plain create. Present the same capability the governed entry expects
        # (never bypass the boundary); the demo space below is created through
        # the maintenance-only non-customer entry as usual.
        cls.maintenance_secret = "g" * 64
        maintenance = patch.dict(
            os.environ,
            {"SC_TENANT_PAYLOAD_MAINTENANCE_CAPABILITY": cls.maintenance_secret},
        )
        maintenance.start()
        cls.addClassCleanup(maintenance.stop)

        cls.Registry = cls.env["sc.platform.database.registration"]
        cls.Operation = cls.env["sc.platform.database.operation"]
        cls.Access = cls.env["sc.platform.maintenance.access"]

        cls.space = cls.env["sc.tenant.company.registration"].with_user(
            SUPERUSER_ID
        )._create_non_customer_space(
            tenant_key="dbgov-demo-space", purpose="demo", company_name="DBGov demo space"
        )
        cls.demo_company = cls.space.company_id

        cls.customer_company = cls.env["res.company"].create({"name": "DBGov customer tenant"})
        cls.customer_registration = cls.env["sc.tenant.company.registration"].with_user(
            SUPERUSER_ID
        ).with_context(
            sc_tenant_payload_import=True,
            sc_tenant_payload_maintenance_capability=cls.maintenance_secret,
        ).create({
            "tenant_key": "dbgov-customer-space",
            "company_id": cls.customer_company.id,
            "source_module": "platform_database_governance_unit",
            "source_external_key": "unit-customer",
        })

        cls.platform_admin = cls.env["res.users"].create({
            "name": "DBGov platform admin",
            "login": "dbgov_platform_admin",
            "company_id": cls.demo_company.id,
            "company_ids": [(6, 0, [cls.demo_company.id, cls.customer_company.id])],
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("smart_core.group_smart_core_admin").id,
                cls.env.ref("smart_core.group_smart_core_non_customer_data_user").id,
            ])],
        })
        cls.security_admin = cls.env["res.users"].create({
            "name": "DBGov security admin",
            "login": "dbgov_security_admin",
            "company_id": cls.demo_company.id,
            "company_ids": [(6, 0, [cls.demo_company.id, cls.customer_company.id])],
            "groups_id": [(6, 0, [
                cls.env.ref("base.group_user").id,
                cls.env.ref("smart_core.group_smart_core_security_admin").id,
            ])],
        })
        # Neither the requester nor an approver: the "no authority" counter-example
        # must not also be a self-approval, or the two refusals would collapse.
        cls.bystander = cls.env["res.users"].create({
            "name": "DBGov bystander",
            "login": "dbgov_bystander",
            "company_id": cls.demo_company.id,
            "company_ids": [(6, 0, [cls.demo_company.id])],
            "groups_id": [(6, 0, [cls.env.ref("base.group_user").id])],
        })
        cls.db_name = "sc_db_gov_unit"

    # ------------------------------------------------------------------
    # registration + lifecycle
    # ------------------------------------------------------------------
    def test_registration_requires_the_governed_maintenance_principal(self):
        with self.assertRaises(AccessError):
            self.Registry.with_user(self.platform_admin)._register_database(
                db_name="sc_db_gov_denied",
                environment_role="platform_internal_demo",
                data_purpose="demo",
            )

    def test_unknown_role_or_purpose_is_refused(self):
        with self.assertRaises(ValidationError):
            self.Registry._register_database(
                db_name="sc_db_gov_bad_role",
                environment_role="not_a_role",
                data_purpose="demo",
            )
        with self.assertRaises(ValidationError):
            self.Registry._register_database(
                db_name="sc_db_gov_bad_purpose",
                environment_role="industry_acceptance",
                data_purpose="demo",
            )
        with self.assertRaises(ValidationError):
            self.Registry._register_database(
                db_name="sc_db_gov_bad_purpose_value",
                environment_role="platform_internal_demo",
                data_purpose="customer",
            )

    def test_lifecycle_readback_matches_persisted_audit(self):
        registered = self.Registry._register_database(
            db_name=self.db_name, environment_role="platform_internal_demo",
            data_purpose="demo", tenant_key="dbgov-demo-space",
        )
        record = self.Registry._resolve_entry(self.db_name)
        self.assertEqual(registered["last_operation"], "register")
        self.assertEqual(registered["operation_count"], 1)
        for count, (operation, prior, target) in enumerate([
            ("provision", "declared", "provisioned"),
            ("activate", "provisioned", "active"),
            ("suspend", "active", "suspended"),
        ], start=2):
            result = self.Registry._apply_operation(self.db_name, operation)
            audit = record.operation_ids.sorted("id")[-1]
            self.assertEqual((audit.from_state, audit.to_state), (prior, target))
            self.assertEqual(result["last_operation"], operation)
            self.assertEqual(result["operation_count"], count)
            self.assertEqual(result, record.readback())
            self.assertEqual(audit.result, record.last_readback)
            self.assertEqual(audit.result, result)

    def test_operation_reason_and_execution_identity_survive_in_audit(self):
        reason, execution_id = "isolated lifecycle rehearsal", "a" * 32
        result = self.Registry._register_database(
            db_name=self.db_name, environment_role="platform_internal_demo",
            data_purpose="demo", tenant_key="dbgov-demo-space",
            reason=reason, execution_id=execution_id,
        )
        record = self.Registry._resolve_entry(self.db_name)
        self.assertEqual(result["operation_request"], {"reason": reason, "execution_id": execution_id})
        self.assertEqual(record.operation_ids.sorted("id")[-1].result, result)
        result = self.Registry._apply_operation(
            self.db_name, "provision", reason="verify provision", execution_id="b" * 32,
        )
        audit = record.operation_ids.sorted("id")[-1]
        self.assertEqual(audit.result["operation_request"],
                         {"reason": "verify provision", "execution_id": "b" * 32})
        self.assertEqual(audit.result, result)

    def test_lifecycle_entries_are_governed_and_audited(self):
        readback = self.Registry._register_database(
            db_name=self.db_name,
            environment_role="platform_internal_demo",
            data_purpose="demo",
            tenant_key="dbgov-demo-space",
        )
        self.assertEqual(readback["lifecycle_state"], "declared")
        self.assertEqual(readback["strategy"], "single_db_multi_company")
        self.assertFalse(readback["grants_business_data_scope"])

        # declared -> active is not declared, so it must fail closed.
        with self.assertRaises(ValidationError):
            self.Registry._apply_operation(self.db_name, "activate")
        with self.assertRaises(ValidationError):
            self.Registry._apply_operation(self.db_name, "not_an_operation")

        self.assertEqual(
            self.Registry._apply_operation(self.db_name, "provision")["lifecycle_state"],
            "provisioned",
        )
        # suspended cannot be reached directly from provisioned
        with self.assertRaises(ValidationError):
            self.Registry._apply_operation(self.db_name, "suspend")
        self.assertEqual(
            self.Registry._apply_operation(self.db_name, "activate")["lifecycle_state"], "active"
        )
        self.assertEqual(
            self.Registry._apply_operation(self.db_name, "suspend")["lifecycle_state"], "suspended"
        )
        self.assertEqual(
            self.Registry._apply_operation(self.db_name, "resume")["lifecycle_state"], "active"
        )
        self.assertEqual(
            self.Registry._apply_operation(self.db_name, "retire")["lifecycle_state"], "retired"
        )
        with self.assertRaises(ValidationError):
            self.Registry._apply_operation(self.db_name, "activate")

        record = self.Registry._resolve_entry(self.db_name)
        self.assertEqual(record.last_operation, "retire")
        self.assertEqual(record.last_readback["lifecycle_state"], "retired")
        # register + provision + activate + suspend + resume + retire
        self.assertEqual(len(record.operation_ids), 6)
        self.assertFalse(record.operation_ids.filtered(lambda row: not row.actor_id))
        with self.assertRaises(UserError):
            record.operation_ids[0].write({"operation": "tampered"})
        with self.assertRaises(UserError):
            record.operation_ids[0].unlink()

    def test_database_registration_identity_is_immutable(self):
        self.Registry._register_database(
            db_name=self.db_name,
            environment_role="platform_internal_demo",
            data_purpose="demo",
        )
        record = self.Registry._resolve_entry(self.db_name)
        with self.assertRaises(UserError):
            record.write({"db_name": "sc_db_gov_renamed"})
        with self.assertRaises(UserError):
            record.unlink()
        with self.assertRaises(ValidationError):
            self.Registry._register_database(
                db_name=self.db_name,
                environment_role="platform_internal_demo",
                data_purpose="demo",
            )

    def test_operational_assertion_fails_closed_before_activation(self):
        self.Registry._register_database(
            db_name=self.db_name,
            environment_role="platform_internal_demo",
            data_purpose="demo",
        )
        with self.assertRaises(UserError):
            self.Registry._assert_database_operational(self.db_name)
        self.Registry._apply_operation(self.db_name, "provision")
        self.Registry._apply_operation(self.db_name, "activate")
        self.assertTrue(self.Registry._assert_database_operational(self.db_name)["db_name"])

    # ------------------------------------------------------------------
    # maintenance access: explicit + independent + audited, never a data grant
    # ------------------------------------------------------------------
    def _activated_database(self, db_name):
        self.Registry._register_database(
            db_name=db_name, environment_role="platform_internal_demo", data_purpose="demo"
        )
        self.Registry._apply_operation(db_name, "provision")
        self.Registry._apply_operation(db_name, "activate")

    def test_maintenance_access_needs_an_independent_approver(self):
        self._activated_database(self.db_name)
        requested = self.Access._request_access(
            self.db_name, "backup", "pre-upgrade snapshot", requester_id=self.platform_admin.id
        )
        self.assertEqual(requested["state"], "requested")
        with self.assertRaises(AccessError):
            # the requester may not approve their own maintenance access
            self.Access.with_user(self.platform_admin)._approve_access(requested["access_id"])
        with self.assertRaises(AccessError):
            # an independent identity without the security-admin role may not approve
            self.Access.with_user(self.bystander)._approve_access(requested["access_id"])
        approved = self.Access.with_user(self.security_admin)._approve_access(
            requested["access_id"]
        )
        self.assertEqual(approved["state"], "approved")
        self.assertFalse(approved["grants_business_data_scope"])
        self.assertTrue(approved["valid_until"])

    def test_maintenance_access_is_scoped_and_time_bounded(self):
        self._activated_database(self.db_name)
        opened = self.Access._request_access(
            self.db_name, "restore", "restore rehearsal", requester_id=self.platform_admin.id
        )
        self.Access.with_user(self.security_admin)._approve_access(opened["access_id"])
        self.assertTrue(self.Access._assert_access_authorized(self.db_name, "restore"))
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # an unregistered database is refused as an unknown governed object
        with self.assertRaises(ValidationError):
            self.Access._assert_access_authorized("sc_db_gov_unregistered", "restore")
        with self.assertRaises(ValidationError):
            self.Access._request_access(
                self.db_name, "not_a_capability", "nope", requester_id=self.platform_admin.id
            )
        with self.assertRaises(ValidationError):
            self.Access._request_access(
                self.db_name, "backup", "   ", requester_id=self.platform_admin.id
            )

        self.Access.with_user(self.security_admin)._revoke_access(
            opened["access_id"], "the restore rehearsal is over"
        )
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "restore")

    def test_expired_maintenance_access_does_not_authorize(self):
        self._activated_database(self.db_name)
        opened = self.Access._request_access(
            self.db_name, "inspect", "diagnose", requester_id=self.platform_admin.id
        )
        self.Access.with_user(self.security_admin)._approve_access(opened["access_id"])
        access = self.Access.sudo().browse(opened["access_id"])
        access._super_write({"valid_until": fields.Datetime.subtract(fields.Datetime.now(), hours=1)})
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "inspect")

    def test_maintenance_access_never_widens_business_data_scope(self):
        self._activated_database(self.db_name)
        admin = self.platform_admin
        before = admin.with_user(admin)._sc_data_company_ids()
        self.assertIn(self.demo_company.id, before)
        self.assertNotIn(self.customer_company.id, before)

        opened = self.Access._request_access(
            self.db_name, "backup", "nightly backup", requester_id=self.platform_admin.id
        )
        self.Access.with_user(self.security_admin)._approve_access(opened["access_id"])
        access = self.Access.sudo().browse(opened["access_id"])

        self.assertFalse(access.grants_business_data_scope)
        self.assertFalse(access.business_data_scope_companies())
        self.assertEqual(admin.with_user(admin)._sc_data_company_ids(), before)

        # the one authoritative answer for "does this identity own customer
        # business data" ignores the administrator groups entirely.
        from odoo.addons.smart_core.security.platform_admin import (
            has_customer_business_data_scope,
        )

        self.assertFalse(has_customer_business_data_scope(admin))
        self.assertFalse(has_customer_business_data_scope(self.security_admin))

    # ------------------------------------------------------------------
    # the product entries: request / approve / reject / revoke / expire / query
    # ------------------------------------------------------------------
    def _migrate_request(self, requester=None, **overrides):
        facts = {
            "db_name": self.db_name,
            "capability": "migrate",
            "reason": "signed payload import for one customer duty",
            "operator_identity_key": "smart_core.svc_tenant_payload_operator_unit",
            "subject_checksum": "c" * 64,
            "authorized_operations": ["provision", "grant"],
        }
        facts.update(overrides)
        access = self.Access.with_user(requester or self.platform_admin)
        return access.request_access(**facts)

    def test_a_request_authorizes_nothing_until_it_is_approved(self):
        self._activated_database(self.db_name)
        before = self.Operation.sudo().search_count([])
        opened = self._migrate_request()
        self.assertEqual(opened["state"], "requested")
        self.assertEqual(opened["authorized_operations"], ["provision", "grant"])
        self.assertEqual(opened["valid_until"], "")
        # The requester is the verified principal, and no decider exists yet.
        record = self.Access.sudo().browse(opened["access_id"])
        self.assertEqual(record.requested_by, self.platform_admin)
        self.assertFalse(record.approved_by)
        # Nothing is authorized yet, and the row records no decider.
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # The only write before an approval is the request itself plus its audit.
        audit = self.Operation.sudo().search([("operation", "=", "maintenance_request")])
        self.assertEqual(len(audit), 1)
        self.assertEqual(self.Operation.sudo().search_count([]), before + 1)
        self.assertEqual(audit.actor_id, self.platform_admin)
        self.assertEqual(self.Access.sudo().browse(opened["access_id"]).approved_by.id, False)

    def test_the_requester_identity_is_the_verified_principal(self):
        self._activated_database(self.db_name)
        with self.assertRaises(AccessError):
            # A principal without the platform-admin identity may not open one.
            self.Access.with_user(self.env.ref("base.public_user")).request_access(
                db_name=self.db_name,
                capability="migrate",
                reason="not this principal",
                operator_identity_key="smart_core.svc_tenant_payload_operator_unit",
                subject_checksum="c" * 64,
                authorized_operations=["provision"],
            )
        with self.assertRaises(AccessError):
            self.Access.with_user(self.security_admin).request_access(
                db_name=self.db_name,
                capability="migrate",
                reason="security administration is not the requesting identity",
                operator_identity_key="smart_core.svc_tenant_payload_operator_unit",
                subject_checksum="c" * 64,
                authorized_operations=["provision"],
            )

    def test_a_migrate_request_must_name_its_operation_set(self):
        self._activated_database(self.db_name)
        for operations, message in (
            (None, "DATABASE_GOVERNANCE_MAINTENANCE_OPERATIONS_REQUIRED"),
            ([], "DATABASE_GOVERNANCE_MAINTENANCE_OPERATIONS_REQUIRED"),
            (["import"], "DATABASE_GOVERNANCE_UNKNOWN_MAINTENANCE_OPERATION"),
        ):
            with self.subTest(operations=operations), self.assertRaisesRegex(
                ValidationError, message
            ):
                self._migrate_request(authorized_operations=operations)
        # The capability no longer stands in for the operation set: a request
        # that names only one operation is created as such.
        opened = self._migrate_request(authorized_operations=["provision"])
        self.assertEqual(opened["authorized_operations"], ["provision"])

    def test_a_retired_identity_can_never_file_a_request(self):
        self._activated_database(self.db_name)
        retired = self.env["res.users"].create({
            "name": "DBGov retired requester",
            "login": "dbgov_retired_requester",
            "company_id": self.demo_company.id,
            "company_ids": [(6, 0, [self.demo_company.id])],
            "groups_id": [(6, 0, [
                self.env.ref("base.group_user").id,
                self.env.ref("smart_core.group_smart_core_admin").id,
            ])],
        })
        retired.write({"active": False})
        with self.assertRaises(ValidationError):
            self.Access._request_access(
                self.db_name,
                "backup",
                "filed by an account that no longer exists",
                requester_id=retired.id,
            )

    def test_the_target_database_is_bound_and_never_replaced(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        self.Access.with_user(self.security_admin).approve_access(opened["access_id"])
        self.assertTrue(self.Access._assert_access_authorized(self.db_name, "migrate"))
        self._activated_database("sc_db_gov_unit_other")
        # The approval names one database; another governed database is not it.
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized("sc_db_gov_unit_other", "migrate")
        with self.assertRaises(ValidationError):
            self._migrate_request(db_name="sc_db_gov_unregistered")

    def test_the_decider_is_verified_on_the_server_side(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        with self.assertRaises(AccessError):
            # self-approval: the requester may never decide its own request
            self.Access.with_user(self.platform_admin).approve_access(opened["access_id"])
        with self.assertRaises(AccessError):
            # no security-admin role: a platform administrator is not an approver
            self.Access.with_user(self.platform_admin).reject_access(
                opened["access_id"], "no authority"
            )
        with self.assertRaises(AccessError):
            self.Access.with_user(self.platform_admin).expire_accesses(self.db_name)
        approved = self.Access.with_user(self.security_admin).approve_access(
            opened["access_id"]
        )
        self.assertEqual(approved["state"], "approved")

    def test_a_rejected_request_never_authorizes(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        with self.assertRaises(ValidationError):
            # a decision without a recorded reason is refused
            self.Access.with_user(self.security_admin).reject_access(opened["access_id"], "  ")
        rejected = self.Access.with_user(self.security_admin).reject_access(
            opened["access_id"], "the payload digest was not reviewed"
        )
        self.assertEqual(rejected["state"], "rejected")
        self.assertEqual(rejected["decision_note"], "the payload digest was not reviewed")
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # A rejected request is terminal: it cannot be approved or revoked.
        with self.assertRaises(UserError):
            self.Access.with_user(self.security_admin).approve_access(opened["access_id"])
        with self.assertRaises(UserError):
            self.Access.with_user(self.security_admin).revoke_access(opened["access_id"])

    def test_a_revoked_approval_stops_authorizing(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        self.Access.with_user(self.security_admin).approve_access(opened["access_id"])
        revoked = self.Access.with_user(self.security_admin).revoke_access(
            opened["access_id"], "the maintenance window closed early"
        )
        self.assertEqual(revoked["state"], "revoked")
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # Repeating a decision is refused, never silently accepted.
        with self.assertRaises(UserError):
            self.Access.with_user(self.security_admin).revoke_access(opened["access_id"])

    def test_an_elapsed_approval_is_retired_by_an_audited_sweep(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        self.Access.with_user(self.security_admin).approve_access(
            opened["access_id"], validity_hours=1
        )
        record = self.Access.sudo().browse(opened["access_id"])
        record._super_write(
            {"valid_until": fields.Datetime.subtract(fields.Datetime.now(), hours=1)}
        )
        expired = self.Access.with_user(self.security_admin).expire_accesses(self.db_name)
        self.assertEqual([row["state"] for row in expired], ["expired"])
        record.invalidate_recordset()
        self.assertEqual(record.state, "expired")
        audit = self.Operation.sudo().search([("operation", "=", "maintenance_expire")])
        self.assertEqual(len(audit), 1)
        self.assertEqual(audit.actor_id, self.security_admin)
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # A second sweep is a no-op: an expired access is not expired twice.
        self.assertEqual(
            self.Access.with_user(self.security_admin).expire_accesses(self.db_name), []
        )

    def test_access_outside_the_validity_window_expires_without_a_sweep(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        self.Access.with_user(self.security_admin).approve_access(opened["access_id"])
        record = self.Access.sudo().browse(opened["access_id"])
        record._super_write(
            {"valid_from": fields.Datetime.subtract(fields.Datetime.now(), hours=4)}
        )
        record._super_write(
            {"valid_until": fields.Datetime.subtract(fields.Datetime.now(), hours=1)}
        )
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        self.assertIsNone(self.Access._approved_access_projection(db_name=self.db_name, capability="migrate"))

    def test_the_authorization_ledger_is_append_only(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        record = self.Access.sudo().browse(opened["access_id"])
        with self.assertRaises(UserError):
            record.write({"capability": "backup"})
        with self.assertRaises(UserError):
            record.unlink()
        operation = self.Operation.sudo().search([], limit=1)
        with self.assertRaises(UserError):
            operation.write({"operation": "forged"})
        with self.assertRaises(UserError):
            operation.unlink()

    def test_the_projection_carries_the_operation_set_and_the_decision(self):
        self._activated_database(self.db_name)
        opened = self._migrate_request()
        self.Access.with_user(self.security_admin).approve_access(opened["access_id"])
        covering = self.Access._approved_access_projection(
            db_name=self.db_name, capability="migrate"
        )
        self.assertEqual(covering["authorized_operations"], ["provision", "grant"])
        self.assertEqual(covering["access_id"], opened["access_id"])
        rows = self.Access.with_user(self.platform_admin).access_projection(
            db_name=self.db_name, state="approved"
        )
        self.assertEqual([row["access_id"] for row in rows], [opened["access_id"]])
        self.assertEqual(rows[0]["reason"], "signed payload import for one customer duty")
        self.assertEqual(rows[0]["operator_identity_key"], "smart_core.svc_tenant_payload_operator_unit")
        self.assertEqual(rows[0]["subject_checksum"], "c" * 64)
        self.assertEqual(rows[0]["approved_by"], self.security_admin.login)
        self.assertEqual(rows[0]["requested_by"], self.platform_admin.login)
        self.assertFalse(rows[0]["grants_business_data_scope"])
        self.assertEqual(rows[0]["tenant_key"], "")
        # A state that was never reached is simply empty, not an error.
        self.assertEqual(
            self.Access.with_user(self.platform_admin).access_projection(state="expired"), []
        )

    def test_the_ledger_is_not_readable_by_an_unrelated_principal(self):
        self._activated_database(self.db_name)
        self._migrate_request()
        outsider = self.env["res.users"].create({
            "name": "DBGov outsider",
            "login": "dbgov_outsider",
            "company_id": self.demo_company.id,
            "company_ids": [(6, 0, [self.demo_company.id])],
            "groups_id": [(6, 0, [self.env.ref("base.group_user").id])],
        })
        with self.assertRaises(AccessError):
            self.Access.with_user(outsider).access_projection()
