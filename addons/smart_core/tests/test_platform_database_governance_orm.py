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
        requested = self.Access._request_access(self.db_name, "backup", "pre-upgrade snapshot")
        self.assertEqual(requested["state"], "requested")
        with self.assertRaises(AccessError):
            # the requester may not approve their own maintenance access
            self.Access._approve_access(requested["access_id"])
        with self.assertRaises(AccessError):
            # an identity without the independent security-admin role may not approve
            self.Access.with_user(self.platform_admin)._approve_access(requested["access_id"])
        approved = self.Access.with_user(self.security_admin)._approve_access(
            requested["access_id"]
        )
        self.assertEqual(approved["state"], "approved")
        self.assertFalse(approved["grants_business_data_scope"])
        self.assertTrue(approved["valid_until"])

    def test_maintenance_access_is_scoped_and_time_bounded(self):
        self._activated_database(self.db_name)
        opened = self.Access._request_access(self.db_name, "restore", "restore rehearsal")
        self.Access.with_user(self.security_admin)._approve_access(opened["access_id"])
        self.assertTrue(self.Access._assert_access_authorized(self.db_name, "restore"))
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "migrate")
        # an unregistered database is refused as an unknown governed object
        with self.assertRaises(ValidationError):
            self.Access._assert_access_authorized("sc_db_gov_unregistered", "restore")
        with self.assertRaises(ValidationError):
            self.Access._request_access(self.db_name, "not_a_capability", "nope")
        with self.assertRaises(ValidationError):
            self.Access._request_access(self.db_name, "backup", "   ")

        self.Access._revoke_access(opened["access_id"])
        with self.assertRaises(AccessError):
            self.Access._assert_access_authorized(self.db_name, "restore")

    def test_expired_maintenance_access_does_not_authorize(self):
        self._activated_database(self.db_name)
        opened = self.Access._request_access(self.db_name, "inspect", "diagnose")
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

        opened = self.Access._request_access(self.db_name, "backup", "nightly backup")
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
