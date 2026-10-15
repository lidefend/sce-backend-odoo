# -*- coding: utf-8 -*-
"""The platform owns the import operator's account lifecycle.

The pure decisions are proven in
``scripts/verify/test_tenant_payload_operator_policy.py``; this test owns the
persisted effects: what the mechanism creates, what it refuses to take over,
that the grant is the only membership it adds, and that revoking removes the
permission while keeping the account and its audit association.
"""

from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

from odoo.addons.smart_core.security import tenant_payload_operator as lifecycle
from odoo.addons.smart_core.security import tenant_payload_operator_policy as policy

IDENTITY_KEY = "smart_core.svc_tenant_payload_operator_test"
LOGIN = "svc-tenant-payload-operator-test"
SUBJECT_CHECKSUM = "b" * 64


@tagged("post_install", "-at_install", "smart_core", "tenant_payload_operator")
class TestTenantPayloadOperatorLifecycle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.internal = cls.env.ref("base.group_user")
        cls.importer = cls.env.ref(policy.IMPORTER_GROUP_XMLID)
        cls.data_operator = cls.env.ref(policy.DATA_OPERATOR_GROUP_XMLID)
        cls.env["ir.config_parameter"].sudo().set_param(
            "sc.tenant.bound_tenant_key", "operator-lifecycle-test"
        )

    # -- helpers -----------------------------------------------------------
    def declaration(self, **overrides):
        block = {
            "carrier": "unified_onboarding_service_identity",
            "identity_key": IDENTITY_KEY,
            "login": LOGIN,
            "name": "Tenant payload operator (test)",
            "company_xmlid": "base.main_company",
            "authorization_basis": "test/tenant_payload_operator_lifecycle",
            "expected_account_groups": list(policy.REQUIRED_ACCOUNT_GROUPS),
            "forbidden_account_groups": list(policy.FORBIDDEN_ACCOUNT_GROUPS),
            "import_capability": policy.IMPORT_CAPABILITY,
        }
        block.update(overrides)
        return block

    def authorization(self, **overrides):
        now = fields.Datetime.now()
        record = {
            "access_id": 7,
            "db_name": self.env.cr.dbname,
            "tenant_key": "operator-lifecycle-test",
            "operator_identity_key": IDENTITY_KEY,
            "capability": policy.IMPORT_CAPABILITY,
            "state": "approved",
            "subject_checksum": SUBJECT_CHECKSUM,
            "approved_by": "owner-approver",
            "requested_by": "platform-maintenance",
            "valid_from": fields.Datetime.to_string(now - timedelta(hours=1)),
            "valid_until": fields.Datetime.to_string(now + timedelta(hours=1)),
            "authorized_operations": ["provision", "grant"],
        }
        record.update(overrides)
        return record

    def operator_record(self):
        return self.env.ref(IDENTITY_KEY, raise_if_not_found=False)

    # -- provisioning ------------------------------------------------------
    def test_provision_creates_a_narrow_non_interactive_identity(self):
        readback = lifecycle.provision(
            self.env, declaration=self.declaration(), authorization=self.authorization()
        )
        operator = readback["operator"]
        self.assertTrue(readback["created"])
        self.assertEqual(readback["mode"], "provision")
        self.assertEqual(readback["writes"], 1)
        self.assertEqual(operator["login"], LOGIN)
        self.assertTrue(operator["active"])
        self.assertFalse(operator["share"])
        self.assertEqual(operator["company_ids"], [self.company.id])
        # Odoo materialises the implied closure of the required groups, so the
        # account carries exactly that closure -- and the readback reports what
        # the platform itself says it is, instead of a hard-coded list.
        self.assertEqual(
            operator["group_xmlids"], readback["required_group_closure_xmlids"]
        )
        self.assertIn(policy.INTERNAL_USER_GROUP_XMLID, operator["group_xmlids"])
        self.assertFalse(operator["has_stored_password"])
        self.assertFalse(operator["has_native_api_keys"])
        self.assertFalse(operator["is_importer"])
        self.assertFalse(operator["is_data_operator"])
        self.assertFalse(readback["interactive_login_capable"])
        self.assertEqual(readback["plan"]["grantable_group_xmlids"], [policy.IMPORTER_GROUP_XMLID])
        self.assertTrue(self.operator_record())

    def test_provision_is_idempotent_on_its_own_account(self):
        first = lifecycle.provision(
            self.env, declaration=self.declaration(), authorization=self.authorization()
        )
        second = lifecycle.provision(
            self.env, declaration=self.declaration(), authorization=self.authorization()
        )
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        self.assertEqual(second["writes"], 0)
        self.assertEqual(first["operator"]["id"], second["operator"]["id"])
        self.assertEqual(
            second["operator"]["group_xmlids"],
            second["required_group_closure_xmlids"],
        )

    def test_provision_never_takes_over_an_account_holding_an_undeclared_group(self):
        # A membership this mechanism never grants widens the identity, even
        # when the extra group is not itself in the forbidden list.
        self.provisioned()
        user = self.operator_record()
        user.write({"groups_id": [Command.link(self.env.ref("base.group_partner_manager").id)]})
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_EXISTING_IDENTITY_MISMATCH"
        ):
            lifecycle.provision(
                self.env, declaration=self.declaration(), authorization=self.authorization()
            )

    def test_provision_never_takes_over_an_account_with_another_identity(self):
        other = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Someone else",
                "login": "someone-else",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [Command.set([self.internal.id])],
            }
        )
        self.env["ir.model.data"].sudo().create(
            {
                "module": "smart_core",
                "name": IDENTITY_KEY.split(".", 1)[1],
                "model": "res.users",
                "res_id": other.id,
                "noupdate": True,
            }
        )
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_EXISTING_IDENTITY_MISMATCH"
        ):
            lifecycle.provision(
                self.env, declaration=self.declaration(), authorization=self.authorization()
            )
        self.assertEqual(self.operator_record(), other)
        self.assertEqual(other.login, "someone-else")

    def test_provision_refuses_a_login_owned_by_another_account(self):
        self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Login owner",
                "login": LOGIN,
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [Command.set([self.internal.id])],
            }
        )
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_LOGIN_ALREADY_OWNED"
        ):
            lifecycle.provision(
                self.env, declaration=self.declaration(), authorization=self.authorization()
            )
        self.assertFalse(self.operator_record())

    def test_provision_refuses_an_identity_owned_by_base(self):
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "DECLARATION_IDENTITY_MODULE_FORBIDDEN"
        ):
            lifecycle.provision(
                self.env,
                declaration=self.declaration(identity_key="base.user_admin"),
                authorization=self.authorization(),
            )

    def test_provision_refuses_widened_or_missing_authorization(self):
        for authorization, rule in (
            (None, "AUTHORIZATION_MISSING"),
            ({}, "AUTHORIZATION_FACT_MISMATCH:db_name"),
            (self.authorization(state="requested"), "AUTHORIZATION_FACT_MISMATCH:state"),
            (self.authorization(capability="read"), "AUTHORIZATION_FACT_MISMATCH:capability"),
            (self.authorization(tenant_key="another-tenant"), "AUTHORIZATION_FACT_MISMATCH:tenant_key"),
            (self.authorization(db_name="another_db"), "AUTHORIZATION_FACT_MISMATCH:db_name"),
            (
                self.authorization(operator_identity_key="smart_core.other"),
                "AUTHORIZATION_FACT_MISMATCH:operator_identity_key",
            ),
            (self.authorization(approved_by=""), "AUTHORIZATION_APPROVER_MISSING"),
            (
                self.authorization(approved_by="platform-maintenance"),
                "AUTHORIZATION_APPROVER_NOT_INDEPENDENT",
            ),
            (self.authorization(subject_checksum="nope"), "AUTHORIZATION_SUBJECT_CHECKSUM_INVALID"),
            (self.authorization(access_id=0), "AUTHORIZATION_ACCESS_ID_INVALID"),
        ):
            with self.subTest(rule=rule):
                # The declaration and the authorization are the *policy*
                # layer's facts, so their refusals surface as the policy's own
                # error type rather than the mechanism's.
                with self.assertRaisesRegex(policy.OperatorPolicyError, rule):
                    lifecycle.provision(
                        self.env, declaration=self.declaration(), authorization=authorization
                    )
        self.assertFalse(self.operator_record())

    def test_provision_refuses_a_database_without_a_bound_tenant_key(self):
        # The tenant binding is one of the facts the approver signed off on, so
        # a database that carries none is a stop rather than a default.
        self.env["ir.config_parameter"].sudo().set_param("sc.tenant.bound_tenant_key", "")
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "AUTHORIZATION_FACT_MISSING:tenant_key"
        ):
            lifecycle.provision(
                self.env, declaration=self.declaration(), authorization=self.authorization()
            )
        self.assertFalse(self.operator_record())

    def test_provision_refuses_a_company_that_is_not_the_tenant_company(self):
        other_company = self.env["res.company"].create({"name": "Other tenant company"})
        self.env["ir.model.data"].sudo().create(
            {
                "module": "smart_core",
                "name": "tenant_payload_operator_other_company",
                "model": "res.company",
                "res_id": other_company.id,
                "noupdate": True,
            }
        )
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_DECLARED_COMPANY_NOT_TENANT_COMPANY"
        ):
            lifecycle.provision(
                self.env,
                declaration=self.declaration(
                    company_xmlid="smart_core.tenant_payload_operator_other_company"
                ),
                authorization=self.authorization(),
            )
        self.assertFalse(self.operator_record())

    def test_the_lifecycle_is_refused_outside_the_governed_principal(self):
        outsider = self.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Outsider",
                "login": "operator-lifecycle-outsider",
                "company_id": self.company.id,
                "company_ids": [Command.set([self.company.id])],
                "groups_id": [Command.set([self.internal.id])],
            }
        )
        with self.assertRaises(AccessError):
            lifecycle.provision(
                self.env(user=outsider.id),
                declaration=self.declaration(),
                authorization=self.authorization(),
            )
        self.assertFalse(self.operator_record())

    # -- the narrow grant --------------------------------------------------
    def provisioned(self):
        lifecycle.provision(
            self.env, declaration=self.declaration(), authorization=self.authorization()
        )
        return self.operator_record()

    def test_grant_adds_only_the_narrow_importer_group(self):
        user = self.provisioned()
        before = set(user.groups_id.ids)
        result = lifecycle.grant_import_scope(
            self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
        )
        after = set(user.groups_id.ids)
        self.assertEqual(after - before, {self.importer.id})
        self.assertEqual(result["after"]["granted_group_xmlid"], policy.IMPORTER_GROUP_XMLID)
        self.assertTrue(result["after"]["changed"])
        self.assertEqual(result["after"]["writes"], 1)
        self.assertTrue(result["after"]["operator"]["is_importer"])
        self.assertFalse(result["after"]["operator"]["is_data_operator"])

    def test_grant_is_idempotent_and_never_widens_the_account(self):
        user = self.provisioned()
        lifecycle.grant_import_scope(
            self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
        )
        groups_after_first = set(user.groups_id.ids)
        after = lifecycle.grant_import_scope(
            self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
        )
        self.assertFalse(after["after"]["changed"])
        self.assertEqual(after["after"]["writes"], 0)
        self.assertEqual(set(user.groups_id.ids), groups_after_first)
        self.assertNotIn(self.data_operator.id, user.groups_id.ids)
        self.assertEqual(after["after"]["operator"]["group_xmlids"].count(policy.IMPORTER_GROUP_XMLID), 1)

    def test_grant_refuses_a_service_identity_holding_a_forbidden_group(self):
        user = self.provisioned()
        user.write({"groups_id": [Command.link(self.env.ref("base.group_system").id)]})
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_OPERATOR_HOLDS_FORBIDDEN_GROUP"
        ):
            lifecycle.grant_import_scope(
            self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
        )
        self.assertNotIn(self.importer.id, user.groups_id.ids)

    def test_grant_refuses_an_unprovisioned_or_missing_identity(self):
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_OPERATOR_NOT_PROVISIONED"
        ):
            lifecycle.grant_import_scope(
                self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
            )

    def test_grant_refuses_an_approval_that_does_not_cover_the_grant(self):
        """The capability is not the grant: naming only ``provision`` is a stop."""
        user = self.provisioned()
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "AUTHORIZATION_OPERATION_NOT_COVERED:grant"
        ):
            lifecycle.grant_import_scope(
                self.env,
                identity_xmlid=IDENTITY_KEY,
                authorization=self.authorization(authorized_operations=["provision"]),
            )
        self.assertNotIn(self.importer.id, user.groups_id.ids)

    def test_grant_refuses_an_approval_without_an_operation_set(self):
        user = self.provisioned()
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "AUTHORIZATION_OPERATIONS_MISSING"
        ):
            lifecycle.grant_import_scope(
                self.env,
                identity_xmlid=IDENTITY_KEY,
                authorization=self.authorization(authorized_operations=None),
            )
        self.assertNotIn(self.importer.id, user.groups_id.ids)

    def test_provision_refuses_an_account_carrying_a_native_api_key(self):
        user = self.provisioned()
        self.env.cr.execute(
            "INSERT INTO res_users_apikeys (user_id, name, key, scope) VALUES (%s, %s, %s, %s)",
            (user.id, "unmanaged", "unmanaged-key", "rpc"),
        )
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_OPERATOR_HAS_UNMANAGED_API_KEY"
        ):
            lifecycle.provision(
                self.env, declaration=self.declaration(), authorization=self.authorization()
            )

    # -- revocation --------------------------------------------------------
    def test_revoke_removes_only_the_grant_and_keeps_the_account(self):
        user = self.provisioned()
        lifecycle.grant_import_scope(
            self.env, identity_xmlid=IDENTITY_KEY, authorization=self.authorization()
        )
        groups_before = set(user.groups_id.ids)
        result = lifecycle.revoke_import_scope(self.env, identity_xmlid=IDENTITY_KEY)
        groups_after = set(user.groups_id.ids)
        self.assertTrue(result["changed"])
        self.assertEqual(groups_after, groups_before - {self.importer.id})
        self.assertFalse(result["operator"]["is_importer"])
        # The account and its audit association survive the revocation.
        self.assertTrue(self.operator_record())
        self.assertTrue(self.operator_record().active)
        self.assertNotIn(self.data_operator.id, groups_after)
        readback = lifecycle.assert_import_operator(self.env, identity_xmlid=IDENTITY_KEY)
        self.assertEqual(
            readback["operator"]["group_xmlids"], readback["required_group_closure_xmlids"]
        )

    def test_revoke_is_a_no_op_when_the_grant_was_never_issued(self):
        self.provisioned()
        result = lifecycle.revoke_import_scope(self.env, identity_xmlid=IDENTITY_KEY)
        self.assertFalse(result["changed"])
        self.assertTrue(self.operator_record())

    def test_revoke_refuses_an_unprovisioned_identity(self):
        with self.assertRaisesRegex(
            lifecycle.TenantPayloadOperatorError, "TPO_OPERATOR_NOT_PROVISIONED"
        ):
            lifecycle.revoke_import_scope(self.env, identity_xmlid=IDENTITY_KEY)
