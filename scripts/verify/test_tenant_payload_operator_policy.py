"""Pure decision tests for the narrow payload import operator lifecycle.

The ORM test owns the persisted effects; this file owns the refusals.  Every
case below is one of the three boundaries the owner fixed: a service identity
never carries an administrator group, an existing account is never taken over,
and an approval is never inferred from the declaration.
"""

from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load(
    "addons/smart_core/security/tenant_payload_operator_policy.py",
    "tenant_payload_operator_policy_under_test",
)

VALID_CHECKSUM = "a" * 64


def declaration(**overrides) -> dict:
    block = {
        "carrier": "unified_onboarding_service_identity",
        "identity_key": "smart_core.svc_tenant_payload_operator_sample",
        "login": "svc-tenant-payload-operator-sample",
        "name": "Tenant payload operator (sample, dev)",
        "company_xmlid": "base.main_company",
        "authorization_basis": "docs/ops/iterations/daily_runtime_version_release_user_acceptance_20261015.md",
        "expected_account_groups": list(policy.REQUIRED_ACCOUNT_GROUPS),
        "forbidden_account_groups": list(policy.FORBIDDEN_ACCOUNT_GROUPS),
        "import_capability": policy.IMPORT_CAPABILITY,
    }
    block.update(overrides)
    return block


def authorization(**overrides) -> dict:
    record = {
        "access_id": 7,
        "db_name": "sc_tenant_sample_dev",
        "tenant_key": "sample",
        "operator_identity_key": "smart_core.svc_tenant_payload_operator_sample",
        "capability": policy.IMPORT_CAPABILITY,
        "state": "approved",
        "approved_by": "owner",
        "requested_by": "platform_maintenance",
        "valid_from": "2026-10-15 00:00:00",
        "valid_until": "2026-10-16 00:00:00",
        "authorized_operations": ["provision", "grant"],
    }
    record.update(overrides)
    return record


def check_authorization(record, **overrides):
    facts = {
        "db_name": "sc_tenant_sample_dev",
        "tenant_key": "sample",
        "identity_key": "smart_core.svc_tenant_payload_operator_sample",
        "subject_checksum": VALID_CHECKSUM,
        "now": "2026-10-15 12:00:00",
        "action": "provision",
    }
    facts.update(overrides)
    return policy.validate_authorization(record, **facts)


class PurityTest(unittest.TestCase):
    def test_the_policy_layer_imports_no_odoo(self):
        """A decision layer that needs the ORM cannot be tested as one."""
        tree = ast.parse(
            (ROOT / "addons/smart_core/security/tenant_payload_operator_policy.py").read_text(
                encoding="utf-8"
            )
        )
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("odoo", imported)


class DeclarationTest(unittest.TestCase):
    def test_a_declared_service_identity_resolves(self):
        resolved = policy.validate_declaration(declaration())
        self.assertEqual(resolved["identity_key"], "smart_core.svc_tenant_payload_operator_sample")
        self.assertEqual(resolved["expected_account_groups"], ["base.group_user"])
        self.assertEqual(resolved["grantable_group_xmlids"], [policy.IMPORTER_GROUP_XMLID])

    def test_a_missing_declaration_is_a_stop(self):
        for block in (None, "text", [], 0):
            with self.subTest(block=block), self.assertRaises(policy.OperatorPolicyError):
                policy.validate_declaration(block)

    def test_only_the_unified_onboarding_carrier_is_accepted(self):
        for carrier in ("", "narrow_import_grant", "customer_module", None):
            with self.subTest(carrier=carrier), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_CARRIER_UNSUPPORTED"
            ):
                policy.validate_declaration(declaration(carrier=carrier))

    def test_an_identity_owned_by_base_is_refused(self):
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "DECLARATION_IDENTITY_MODULE_FORBIDDEN"
        ):
            policy.validate_declaration(declaration(identity_key="base.user_admin"))

    def test_an_unusable_identity_key_is_refused(self):
        for key in ("", "notanxmlid", "smart_core.", ".name", "smart_core.Name", "smart_core.a b"):
            with self.subTest(key=key), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_IDENTITY_KEY_INVALID"
            ):
                policy.validate_declaration(declaration(identity_key=key))

    def test_the_company_is_declared_never_defaulted(self):
        for company in ("", None, " main ", "maincompany", "base."):
            with self.subTest(company=company), self.assertRaises(policy.OperatorPolicyError):
                policy.validate_declaration(declaration(company_xmlid=company))

    def test_an_unusable_login_or_name_is_refused(self):
        for login in ("", "AB", "1svc", "svc account", "svc@example.com"):
            with self.subTest(login=login), self.assertRaises(policy.OperatorPolicyError):
                policy.validate_declaration(declaration(login=login))
        for name in ("", "   ", None):
            with self.subTest(name=name), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_NAME_MISSING"
            ):
                policy.validate_declaration(declaration(name=name))

    def test_the_authorization_basis_is_required(self):
        for basis in ("", "   ", None):
            with self.subTest(basis=basis), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_AUTHORIZATION_BASIS_MISSING"
            ):
                policy.validate_declaration(declaration(authorization_basis=basis))

    def test_the_account_group_ceiling_is_exact(self):
        for groups in (
            [],
            None,
            ["base.group_user", "base.group_system"],
            ["base.group_user", "smart_core.group_smart_core_data_operator"],
            ["base.group_user", "smart_core.group_smart_core_tenant_payload_importer"],
            ["base.group_user", "base.group_user"],
        ):
            with self.subTest(groups=groups), self.assertRaises(policy.OperatorPolicyError):
                policy.validate_declaration(declaration(expected_account_groups=groups))

    def test_the_forbidden_ceiling_must_be_complete(self):
        for forbidden in ([], None, ["base.group_system"], list(policy.FORBIDDEN_ACCOUNT_GROUPS) + ["x.y"]):
            with self.subTest(forbidden=forbidden), self.assertRaises(policy.OperatorPolicyError):
                policy.validate_declaration(declaration(forbidden_account_groups=forbidden))

    def test_the_required_and_forbidden_ceilings_are_disjoint(self):
        """The conflict guard is only sound while these two sets never overlap."""
        required = set(policy.REQUIRED_ACCOUNT_GROUPS)
        forbidden = set(policy.FORBIDDEN_ACCOUNT_GROUPS)
        self.assertEqual(required & forbidden, set())
        self.assertNotIn(policy.IMPORTER_GROUP_XMLID, forbidden)
        self.assertNotIn(policy.INTERNAL_USER_GROUP_XMLID, forbidden)
        self.assertIn(policy.DATA_OPERATOR_GROUP_XMLID, forbidden)

    def test_another_capability_is_refused(self):
        for capability in ("read", "suspended", "import", "Migrate"):
            with self.subTest(capability=capability), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_IMPORT_CAPABILITY_INVALID"
            ):
                policy.validate_declaration(declaration(import_capability=capability))

    def test_an_undeclared_capability_is_a_stop_not_a_default(self):
        for capability in (None, "", "   "):
            with self.subTest(capability=capability), self.assertRaisesRegex(
                policy.OperatorPolicyError, "DECLARATION_IMPORT_CAPABILITY_MISSING"
            ):
                policy.validate_declaration(declaration(import_capability=capability))

    def test_a_group_that_is_not_the_narrow_importer_is_never_grantable(self):
        resolved = policy.validate_declaration(declaration())
        self.assertEqual(resolved["grantable_group_xmlids"], [policy.IMPORTER_GROUP_XMLID])
        self.assertNotIn(policy.DATA_OPERATOR_GROUP_XMLID, resolved["grantable_group_xmlids"])
        self.assertNotIn(policy.DATA_OPERATOR_GROUP_XMLID, policy.REQUIRED_ACCOUNT_GROUPS)


class IdentityTest(unittest.TestCase):
    def setUp(self):
        self.declared = {
            "identity_key": "smart_core.svc_tenant_payload_operator_sample",
            "login": "svc-tenant-payload-operator-sample",
            "company_ids": [1],
            "expected_account_groups": ["base.group_user"],
            "forbidden_account_groups": list(policy.FORBIDDEN_ACCOUNT_GROUPS),
        }
        self.existing = {
            "xmlid": "smart_core.svc_tenant_payload_operator_sample",
            "login": "svc-tenant-payload-operator-sample",
            "active": True,
            "share": False,
            "has_stored_password": False,
            "company_ids": [1],
            "group_xmlids": ["base.group_user"],
        }

    def test_the_declared_identity_is_reused(self):
        self.assertTrue(
            policy.account_identity_matches(existing=self.existing, declared=self.declared)
        )

    def test_an_account_with_another_login_is_never_taken_over(self):
        for login in ("admin", "", "svc-other"):
            with self.subTest(login=login):
                existing = dict(self.existing, login=login)
                self.assertFalse(
                    policy.account_identity_matches(existing=existing, declared=self.declared)
                )

    def test_an_archived_or_shared_or_interactive_account_is_never_taken_over(self):
        for override in (
            {"active": False},
            {"active": None},
            {"share": True},
            {"has_stored_password": True},
        ):
            with self.subTest(override=override):
                existing = dict(self.existing, **override)
                self.assertFalse(
                    policy.account_identity_matches(existing=existing, declared=self.declared)
                )

    def test_another_company_scope_is_never_taken_over(self):
        for company_ids in ([2], [], [1, 2], None):
            with self.subTest(company_ids=company_ids):
                existing = dict(self.existing, company_ids=company_ids)
                self.assertFalse(
                    policy.account_identity_matches(existing=existing, declared=self.declared)
                )

    def test_an_account_that_lost_a_required_group_is_never_taken_over(self):
        existing = dict(self.existing, group_xmlids=[])
        self.assertFalse(
            policy.account_identity_matches(existing=existing, declared=self.declared)
        )

    def test_an_account_holding_a_forbidden_group_is_never_taken_over(self):
        for group in ("base.group_system", "smart_core.group_smart_core_data_operator"):
            with self.subTest(group=group):
                existing = dict(self.existing, group_xmlids=["base.group_user", group])
                self.assertFalse(
                    policy.account_identity_matches(existing=existing, declared=self.declared)
                )

    def test_a_comparison_without_facts_is_a_stop(self):
        for existing, declared in ((None, {}), ({}, None), ("x", {}), ({}, "x")):
            with self.subTest(existing=existing), self.assertRaisesRegex(
                policy.OperatorPolicyError, "IDENTITY_COMPARISON_INVALID"
            ):
                policy.account_identity_matches(existing=existing, declared=declared)

    def test_the_platform_closure_of_the_required_group_is_part_of_the_identity(self):
        # Odoo materialises the implied closure of the required groups, so the
        # closure the platform reports is reusable.  Without it the strict
        # reading applies and the same account is refused.
        declared = dict(
            self.declared, expected_implied_account_groups=["base.group_multi_currency"]
        )
        existing = dict(
            self.existing, group_xmlids=["base.group_user", "base.group_multi_currency"]
        )
        self.assertTrue(
            policy.account_identity_matches(existing=existing, declared=declared)
        )
        self.assertFalse(
            policy.account_identity_matches(existing=existing, declared=self.declared)
        )

    def test_a_group_beyond_the_declared_closure_is_never_taken_over(self):
        declared = dict(
            self.declared, expected_implied_account_groups=["base.group_multi_currency"]
        )
        existing = dict(
            self.existing,
            group_xmlids=[
                "base.group_user",
                "base.group_multi_currency",
                "base.group_partner_manager",
            ],
        )
        self.assertFalse(
            policy.account_identity_matches(existing=existing, declared=declared)
        )


class AuthorizationTest(unittest.TestCase):
    def test_an_approved_in_window_record_is_accepted(self):
        resolved = check_authorization(authorization())
        self.assertEqual(resolved["access_id"], 7)
        self.assertEqual(resolved["approved_by"], "owner")
        self.assertEqual(resolved["subject_checksum"], VALID_CHECKSUM)

    def test_a_missing_authorization_is_a_stop(self):
        for record in (None, [], "approved", 0):
            with self.subTest(record=record), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_MISSING"
            ):
                check_authorization(record)

    def test_every_bound_fact_must_match_the_target(self):
        for key, value in (
            ("db_name", "another_db"),
            ("tenant_key", "another_tenant"),
            ("operator_identity_key", "smart_core.other_operator"),
            ("capability", "read"),
            ("state", "requested"),
        ):
            with self.subTest(key=key), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_FACT_MISMATCH:%s" % key
            ):
                check_authorization(authorization(**{key: value}))

    def test_an_empty_bound_fact_is_a_stop(self):
        with self.assertRaises(policy.OperatorPolicyError):
            policy.validate_authorization(
                authorization(),
                db_name="",
                tenant_key="sample",
                identity_key="smart_core.svc_tenant_payload_operator_sample",
                subject_checksum=VALID_CHECKSUM,
                now="2026-10-15 12:00:00",
                action="provision",
            )

    def test_a_fabricated_approver_is_a_stop(self):
        for approver in ("", "   ", None):
            with self.subTest(approver=approver), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_APPROVER_MISSING"
            ):
                check_authorization(authorization(approved_by=approver))

    def test_the_requester_may_not_approve_itself(self):
        with self.assertRaisesRegex(
            policy.OperatorPolicyError, "AUTHORIZATION_APPROVER_NOT_INDEPENDENT"
        ):
            check_authorization(authorization(requested_by="owner"))

    def test_the_validity_window_is_enforced(self):
        for now in ("2026-10-14 23:59:59", "2026-10-16 00:00:00", "2026-10-20 00:00:00"):
            with self.subTest(now=now), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_OUT_OF_WINDOW"
            ):
                check_authorization(authorization(), now=now)
        for record in ({"valid_from": ""}, {"valid_until": ""}, {"valid_from": None, "valid_until": None}):
            with self.subTest(record=record), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_VALIDITY_MISSING"
            ):
                check_authorization(authorization(**record))

    def test_an_unusable_subject_digest_is_a_stop(self):
        for checksum in ("", None, "f1adc6fb", "F" * 64, "z" * 64, "a" * 63, "a" * 65):
            with self.subTest(checksum=checksum), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_SUBJECT_CHECKSUM_INVALID"
            ):
                check_authorization(authorization(), subject_checksum=checksum)

    def test_an_unusable_access_id_is_a_stop(self):
        for access_id in (0, -1, "7", None, True, 7.0):
            with self.subTest(access_id=access_id), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_ACCESS_ID_INVALID"
            ):
                check_authorization(authorization(access_id=access_id))

    def test_an_approval_must_name_the_operation_it_authorizes(self):
        # The capability is not the grant: an access that names only the other
        # operation must never be read as covering this one.
        for granted, requested in ((["grant"], "provision"), (["provision"], "grant")):
            with self.subTest(granted=granted, requested=requested), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_OPERATION_NOT_COVERED"
            ):
                check_authorization(
                    authorization(authorized_operations=granted), action=requested
                )
        check_authorization(authorization(authorized_operations=["grant", "provision"]))

    def test_an_approval_without_an_operation_set_is_a_stop(self):
        for operations in (None, [], "", "provision", [1], ["", None]):
            with self.subTest(operations=operations), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_OPERATIONS_MISSING"
            ):
                check_authorization(authorization(authorized_operations=operations))

    def test_an_unnamed_operation_is_a_stop(self):
        for action in ("", "   ", None):
            with self.subTest(action=action), self.assertRaisesRegex(
                policy.OperatorPolicyError, "AUTHORIZATION_ACTION_MISSING"
            ):
                check_authorization(authorization(), action=action)


class AccountPlanTest(unittest.TestCase):
    def test_the_plan_never_creates_an_interactive_principal(self):
        plan = policy.plan_account_creation(
            declared=policy.validate_declaration(declaration()), company_ids=[1]
        )
        self.assertFalse(plan["usable_password"])
        self.assertFalse(plan["interactive_login"])
        self.assertFalse(plan["share"])
        self.assertTrue(plan["active"])
        self.assertEqual(plan["company_ids"], [1])
        self.assertEqual(plan["group_xmlids"], ["base.group_user"])

    def test_a_wider_or_empty_company_scope_is_a_stop(self):
        declared = policy.validate_declaration(declaration())
        for company_ids in ([], None, [1, 2], [1, 1, 2]):
            with self.subTest(company_ids=company_ids), self.assertRaisesRegex(
                policy.OperatorPolicyError, "ACCOUNT_COMPANY_SCOPE_NOT_SINGLE"
            ):
                policy.plan_account_creation(declared=declared, company_ids=company_ids)

    def test_a_plan_without_a_declaration_is_a_stop(self):
        for declared in ({}, {"login": "svc-tenant-payload-operator-sample"}, {"identity_key": "smart_core.a"}):
            with self.subTest(declared=declared), self.assertRaises(policy.OperatorPolicyError):
                policy.plan_account_creation(declared=declared, company_ids=[1])


if __name__ == "__main__":
    unittest.main()
