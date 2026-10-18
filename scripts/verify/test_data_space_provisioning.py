"""Pure decision tests for the governed business data-space onboarding module.

The module under test imports nothing from odoo, so these tests drive it with a
plain mapping. Real ORM enforcement stays with the registration model tests.
"""
import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


provisioning = load(
    "addons/smart_core/security/data_space_provisioning.py", "provisioning_under_test"
)


class _Ids:
    def __init__(self, ids):
        self.ids = list(ids)


class _Registrations:
    """A registration recordset with the fields the onboarding decision reads."""

    def __init__(self, records):
        self._records = list(records)
        self.ids = [record["id"] for record in self._records]
        self.company_id = _Ids([record["company_id"] for record in self._records])

    def __bool__(self):
        return bool(self._records)

    def _single(self, name):
        if len(self._records) != 1:
            raise AssertionError("expected one registration, got %d" % len(self._records))
        return self._records[0][name]

    @property
    def active(self):
        return self._single("active")

    @property
    def data_purpose(self):
        return self._single("data_purpose")

    @property
    def tenant_key(self):
        return self._single("tenant_key")


class _Model:
    def __init__(self, *, ids=(), records=None, count=0, created=None, field_names=(),
                 creates=False, carrier=False,
                 pending_enrollment=(), owners=None):
        if records is None:
            self._records = [
                {
                    "id": index,
                    "company_id": company_id,
                    "active": True,
                    "data_purpose": "demo",
                    "tenant_key": None,
                }
                for index, company_id in enumerate(ids, 1)
            ]
        else:
            self._records = [dict(record) for record in records]
        self._ids = [record["id"] for record in self._records]
        self._count = count
        self._carrier = bool(carrier)
        self._owners = dict(owners or {})
        self._created = created if created is not None else []
        self._fields = {name: None for name in field_names}
        self.domains = []
        self._creates = creates
        self._registered = []
        self._adopted = []
        self._pending_enrollment = list(pending_enrollment)
        self._enrollments = []
        self._enrollment_queries = []

    def _enroll_data_space_operators(self, registrations):
        self._enrollments.append(registrations)
        return {
            "group": "smart_core.group_smart_core_non_customer_data_user",
            "companies": list(registrations.company_id.ids),
            "enrolled": ["probe-operator"],
            "already_effective": [],
        }

    def _data_space_operators_pending_enrollment(self, registrations):
        self._enrollment_queries.append(registrations)
        return list(self._pending_enrollment)

    def sudo(self):
        return self

    def search(self, domain, limit=None):
        """Filter like the ORM does for the two domains onboarding reads."""
        self.domains.append(domain)
        records = list(self._records)
        for clause in domain:
            if not isinstance(clause, (list, tuple)) or len(clause) != 3:
                continue
            field, operator, value = clause
            if operator != "=":
                continue
            if field == "active":
                records = [record for record in records if record["active"] == value]
            elif field == "data_purpose":
                records = [record for record in records if record["data_purpose"] == value]
            elif field == "company_id":
                records = [record for record in records if record["company_id"] == value]
        if limit:
            records = records[:limit]
        return _Registrations(records)

    def search_count(self, domain):
        self.domains.append(domain)
        return self._count

    def _read_group(self, domain, groupby=(), aggregates=(), **kwargs):
        """Grouped company readback, standing in for the ORM aggregate.

        ``owners`` is ``{company_id: row_count}``; the platform entry only needs
        the group keys, but the count keeps the fake honest about the shape
        ``_read_group`` returns (recordset, aggregate) tuples.
        """
        self.domains.append(domain)
        return [(_Recordset(company_id), count)
                for company_id, count in sorted(self._owners.items())]

    def _create_non_customer_space(self, **kwargs):
        self._created.append(kwargs)
        return {"tenant_key": kwargs["tenant_key"], "data_purpose": kwargs["purpose"]}

    def _register_non_customer_space(self, **kwargs):
        self._registered.append(kwargs)
        return {"tenant_key": kwargs["tenant_key"], "data_purpose": kwargs["purpose"],
                "company_id": kwargs["company_id"]}

    def _adopt_environment_main_company(self, **kwargs):
        self._adopted.append(kwargs)
        return {"tenant_key": kwargs["tenant_key"], "data_purpose": kwargs["purpose"],
                "company_id": kwargs["company_id"],
                "environment_role": kwargs["environment_role"]}

    def browse(self, ids):
        return _Recordset(ids, carrier=self._carrier)

    def with_context(self, **kwargs):
        return self


class _Recordset:
    def __init__(self, ids, carrier=False):
        self.id = int(ids)
        self.is_platform_bootstrap_company = bool(carrier)

    def exists(self):
        return self


class _MainCompany:
    def __init__(self, id_):
        self.id = int(id_)


class _ConfigParameter:
    def __init__(self, value=None):
        self.value = value
        self.writes = []

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.value if self.value is not None else default

    def set_param(self, key, value):
        self.writes.append((key, value))
        self.value = value
        return True


class FakeEnv(dict):
    def __init__(self, company=None, registration=None, models=None,
                 *, role=None, main_company_id=1):
        super().__init__()
        self["res.company"] = company or _Model()
        self["sc.tenant.company.registration"] = registration or _Model()
        for name, model in (models or {}).items():
            self[name] = model
        self["ir.config_parameter"] = _ConfigParameter(role)
        self.company = _MainCompany(main_company_id)


class StrategyResolutionTest(unittest.TestCase):
    def test_known_purposes_resolve_to_declared_role_and_strategy(self):
        self.assertEqual(
            provisioning.strategy_for_purpose("demo"),
            {
                "data_purpose": "demo",
                "environment_role": "platform_internal_demo",
                "strategy": "single_db_multi_company",
            },
        )
        self.assertEqual(
            provisioning.strategy_for_purpose("customer")["strategy"],
            "database_per_customer_tenant",
        )

    def test_unknown_purpose_is_refused(self):
        for purpose in ("", None, "shared", "customer_demo"):
            with self.subTest(purpose=purpose), self.assertRaises(ValueError):
                provisioning.strategy_for_purpose(purpose)

    def test_repository_declaration_is_policy_compliant(self):
        declaration = provisioning.load_declaration()
        self.assertEqual(provisioning.validate_strategy_declaration(declaration), [])

    def test_declaration_missing_role_is_reported(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"].pop("industry_acceptance")
        failures = provisioning.validate_strategy_declaration(declaration)
        self.assertTrue(any("industry_acceptance" in failure for failure in failures), failures)

    def test_declaration_with_wrong_role_strategy_is_reported(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"]["industry_acceptance"]["strategy"] = (
            "database_per_customer_tenant"
        )
        failures = provisioning.validate_strategy_declaration(declaration)
        self.assertTrue(any("strategy must be" in failure for failure in failures), failures)

    def test_declaration_that_lets_bootstrap_company_carry_data_is_reported(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"]["platform_internal_demo"][
            "bootstrap_company_carries_business_data"
        ] = True
        failures = provisioning.validate_strategy_declaration(declaration)
        self.assertTrue(any("never carry business data" in failure for failure in failures), failures)

    def test_missing_declaration_file_fails_closed(self):
        with self.assertRaises(ValueError):
            provisioning.load_declaration(ROOT / "config/tenant/does-not-exist.json")


class OnboardingEntryTest(unittest.TestCase):
    def test_customer_cannot_onboard_through_the_maintenance_entry(self):
        registration = _Model()
        env = FakeEnv(registration=registration)
        with self.assertRaises(ValueError) as ctx:
            provisioning.onboard_business_company(
                env, tenant_key="customer-a", purpose="customer", company_name="Customer A",
            )
        self.assertIn("SIGNED_IMPORT", str(ctx.exception))
        self.assertEqual(registration._created, [])

    def test_demo_onboarding_is_validated_then_delegated(self):
        registration = _Model()
        env = FakeEnv(registration=registration)
        result = provisioning.onboard_business_company(
            env, tenant_key="demo-platform", purpose="demo", company_name="Demo Company",
        )
        self.assertEqual(result["data_purpose"], "demo")
        self.assertEqual(registration._created[0]["tenant_key"], "demo-platform")

    def test_customer_cannot_be_adopted_through_the_maintenance_entry(self):
        registration = _Model()
        env = FakeEnv(registration=registration)
        with self.assertRaises(ValueError) as ctx:
            provisioning.adopt_business_company(
                env, tenant_key="customer-a", purpose="customer", company_id=3,
            )
        self.assertIn("SIGNED_IMPORT", str(ctx.exception))
        self.assertEqual(registration._created, [])

    def test_existing_company_is_adopted_after_strategy_is_proven(self):
        registration = _Model(creates=True)
        env = FakeEnv(registration=registration)
        result = provisioning.adopt_business_company(
            env, tenant_key="local-dev-demo", purpose="demo", company_id=3,
        )
        self.assertEqual(result["company_id"], 3)
        self.assertEqual(registration._registered[0]["company_id"], 3)

    def test_onboarding_stops_when_the_role_strategy_is_undeclared(self):
        registration = _Model()
        env = FakeEnv(registration=registration)
        declaration = provisioning.load_declaration()
        declaration["environment_roles"].pop("industry_acceptance")
        with self.assertRaises(ValueError):
            provisioning.onboard_business_company(
                env, tenant_key="acceptance", purpose="test", company_name="Acceptance",
                declaration=declaration,
            )
        self.assertEqual(registration._created, [])


class EnvironmentOnboardingTest(unittest.TestCase):
    """The environment main company onboarding picks its shape from the database.

    A database that already onboarded a business company cannot retire a carrier
    marker that was never there, and a database that owns none must not adopt a
    carrier without retiring it. Both shapes read the purpose from the declared
    role, so no caller can onboard a customer database.
    """

    def test_fresh_database_retires_the_carrier_marker(self):
        registration = _Model()
        env = FakeEnv(registration=registration, role="platform_internal_demo")
        result = provisioning.onboard_environment_business_company(
            env, tenant_key="sc-demo-main",
        )
        self.assertEqual(result["data_purpose"], "demo")
        self.assertEqual(result["environment_role"], "platform_internal_demo")
        self.assertEqual(registration._adopted[0]["tenant_key"], "sc-demo-main")
        self.assertEqual(registration._registered, [])

    def test_database_that_already_owns_a_registration_adopts_its_main_company(self):
        registration = _Model(ids=[21, 22])
        env = FakeEnv(registration=registration, role="platform_internal_demo")
        result = provisioning.onboard_environment_business_company(
            env, tenant_key="sc-demo-main",
        )
        self.assertEqual(result["data_purpose"], "demo")
        self.assertEqual(result["company_id"], 1)
        self.assertEqual(registration._registered[0]["tenant_key"], "sc-demo-main")
        self.assertEqual(registration._registered[0]["company_id"], 1)
        self.assertEqual(registration._adopted, [])

    def test_replay_returns_the_existing_registration(self):
        registration = _Model(records=[{
            "id": 31,
            "company_id": 1,
            "active": True,
            "data_purpose": "demo",
            "tenant_key": "sc-demo-main",
        }])
        env = FakeEnv(registration=registration, role="platform_internal_demo")
        result = provisioning.onboard_environment_business_company(
            env, tenant_key="sc-demo-main",
        )
        self.assertEqual(result.tenant_key, "sc-demo-main")
        self.assertEqual(result.data_purpose, "demo")
        self.assertEqual(registration._registered, [])
        self.assertEqual(registration._adopted, [])

    def test_replay_refuses_a_different_tenant_key_for_the_same_company(self):
        registration = _Model(records=[{
            "id": 31,
            "company_id": 1,
            "active": True,
            "data_purpose": "demo",
            "tenant_key": "sc-demo-main",
        }])
        env = FakeEnv(registration=registration, role="platform_internal_demo")
        with self.assertRaisesRegex(ValueError, "DATA_SPACE_COMPANY_ALREADY_REGISTERED"):
            provisioning.onboard_environment_business_company(
                env, tenant_key="sc-demo-other",
            )

    def test_acceptance_role_onboards_the_test_purpose(self):
        registration = _Model(ids=[21])
        env = FakeEnv(registration=registration, role="industry_acceptance")
        result = provisioning.onboard_environment_business_company(
            env, tenant_key="sc-acceptance-main",
        )
        self.assertEqual(result["data_purpose"], "test")
        self.assertEqual(registration._registered[0]["purpose"], "test")

    def test_customer_production_role_never_onboards_its_main_company(self):
        for role in (None, "customer_production"):
            with self.subTest(role=role):
                registration = _Model()
                env = FakeEnv(registration=registration, role=role)
                with self.assertRaises(ValueError) as ctx:
                    provisioning.onboard_environment_business_company(env, tenant_key="c")
                self.assertIn("SIGNED_IMPORT", str(ctx.exception))
                self.assertEqual(registration._adopted, [])
                self.assertEqual(registration._registered, [])

    def test_carrier_main_company_is_refused_when_a_registration_exists(self):
        registration = _Model(ids=[21])
        env = FakeEnv(registration=registration, role="platform_internal_demo",
                      company=_Model(carrier=True))
        with self.assertRaises(ValueError) as ctx:
            provisioning.onboard_environment_business_company(env, tenant_key="sc-demo-main")
        self.assertIn("IS_STILL_A_CARRIER", str(ctx.exception))
        self.assertEqual(registration._registered, [])

    def test_role_without_a_declared_strategy_is_refused(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"].pop("platform_internal_demo")
        registration = _Model()
        env = FakeEnv(registration=registration, role="platform_internal_demo")
        with self.assertRaises(ValueError):
            provisioning.onboard_environment_business_company(
                env, tenant_key="sc-demo-main", declaration=declaration,
            )
        self.assertEqual(registration._adopted, [])
        self.assertEqual(registration._registered, [])

    def test_undeclared_role_resolves_to_the_strictest_purpose(self):
        env = FakeEnv(registration=_Model())
        self.assertEqual(provisioning.environment_role(env), "customer_production")
        self.assertEqual(provisioning.environment_role_data_purpose(env), "customer")


class EnvironmentRoleTest(unittest.TestCase):
    def test_declared_role_is_read_from_the_parameter(self):
        env = FakeEnv(role="platform_internal_demo")
        self.assertEqual(provisioning.environment_role(env), "platform_internal_demo")

    def test_undeclared_role_resolves_to_the_strictest_role(self):
        env = FakeEnv(role=None)
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(provisioning.ENVIRONMENT_ROLE_ENV_VAR, None)
            self.assertEqual(provisioning.environment_role(env), "customer_production")

    def test_deployment_variable_is_the_only_fallback(self):
        env = FakeEnv(role=None)
        with patch.dict(
            os.environ, {provisioning.ENVIRONMENT_ROLE_ENV_VAR: "industry_acceptance"}
        ):
            self.assertEqual(provisioning.environment_role(env), "industry_acceptance")

    def test_declare_environment_role_persists_and_refuses_unknown(self):
        env = FakeEnv(role=None)
        self.assertEqual(
            provisioning.declare_environment_role(env, "industry_acceptance"),
            "industry_acceptance",
        )
        self.assertEqual(
            env["ir.config_parameter"].writes[-1],
            (provisioning.ENVIRONMENT_ROLE_PARAM, "industry_acceptance"),
        )
        with self.assertRaisesRegex(ValueError, "UNKNOWN_ENVIRONMENT_ROLE"):
            provisioning.declare_environment_role(env, "shared_space")

    def test_main_company_onboarding_purpose_is_role_scoped(self):
        for role, expected in (
            ("platform_internal_demo", "demo"),
            ("industry_acceptance", "test"),
            ("customer_production", None),
        ):
            with self.subTest(role=role):
                self.assertEqual(
                    provisioning.main_company_onboarding_purpose(FakeEnv(role=role)),
                    expected,
                )

    def test_declaration_without_main_company_purpose_is_reported(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"]["platform_internal_demo"].pop(
            "main_company_onboarding_purpose")
        failures = provisioning.validate_strategy_declaration(declaration)
        self.assertTrue(
            any("main_company_onboarding_purpose" in failure for failure in failures), failures)

    def test_customer_role_cannot_onboard_its_main_company_in_the_declaration(self):
        declaration = provisioning.load_declaration()
        declaration["environment_roles"]["customer_production"][
            "main_company_onboarding_purpose"] = "customer"
        failures = provisioning.validate_strategy_declaration(declaration)
        self.assertTrue(any("pure carrier" in failure for failure in failures), failures)


class MainCompanyOnboardingTest(unittest.TestCase):
    def test_demo_role_onboards_the_environment_main_company(self):
        registration = _Model()
        env = FakeEnv(registration=registration, role="platform_internal_demo",
                      main_company_id=1)
        result = provisioning.onboard_environment_main_company(
            env, tenant_key="sc-demo-main")
        self.assertEqual(result["environment_role"], "platform_internal_demo")
        self.assertEqual(result["company_id"], 1)
        self.assertEqual(result["data_purpose"], "demo")
        self.assertEqual(registration._adopted[0]["purpose"], "demo")

    def test_test_role_onboards_the_environment_main_company_as_test(self):
        env = FakeEnv(registration=_Model(), role="industry_acceptance", main_company_id=5)
        result = provisioning.onboard_environment_main_company(env, tenant_key="acceptance")
        self.assertEqual(result["data_purpose"], "test")
        self.assertEqual(result["company_id"], 5)

    def test_customer_role_refuses_to_onboard_its_main_company(self):
        registration = _Model()
        env = FakeEnv(registration=registration, role="customer_production",
                      main_company_id=1)
        with self.assertRaisesRegex(ValueError, "FORBIDS_MAIN_COMPANY_ONBOARDING"):
            provisioning.onboard_environment_main_company(env, tenant_key="customer-main")
        self.assertEqual(registration._adopted, [])


class IdentityEnrollmentTest(unittest.TestCase):
    """Onboarding must enroll the space's operators, or nobody can read it."""

    def test_enrollment_requires_an_onboarded_space(self):
        env = FakeEnv(registration=_Model(ids=[]))
        with self.assertRaises(ValueError) as ctx:
            provisioning.enroll_data_space_identities(env, purpose="demo")
        self.assertIn("ONBOARDING_REQUIRED", str(ctx.exception))

    def test_enrollment_delegates_to_the_registration_authority(self):
        registration = _Model(ids=[7, 9])
        env = FakeEnv(registration=registration)
        receipt = provisioning.enroll_data_space_identities(env, purpose="demo")
        self.assertEqual(receipt["companies"], [7, 9])
        self.assertEqual(len(registration._enrollments), 1)
        self.assertEqual(receipt["group"], "smart_core.group_smart_core_non_customer_data_user")

    def test_enrollment_never_relabels_a_customer_space(self):
        registration = _Model(ids=[7])
        env = FakeEnv(registration=registration)
        with self.assertRaises(ValueError):
            provisioning.enroll_data_space_identities(env, purpose="customer")
        self.assertEqual(registration._enrollments, [])

    def test_identity_readiness_fails_closed_while_operators_are_outside_the_realm(self):
        registration = _Model(ids=[7], pending_enrollment=["pm1", "fin1"])
        env = FakeEnv(registration=registration)
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_data_space_identities_enrolled(env, purpose="demo")
        self.assertIn("DATA_SPACE_IDENTITY_ENROLLMENT_INCOMPLETE", str(ctx.exception))
        self.assertIn("pm1", str(ctx.exception))
        self.assertIn("fin1", str(ctx.exception))

    def test_identity_readiness_passes_when_every_operator_is_enrolled(self):
        registration = _Model(ids=[7])
        env = FakeEnv(registration=registration)
        self.assertTrue(provisioning.assert_data_space_identities_enrolled(env, purpose="demo"))
        self.assertEqual(len(registration._enrollment_queries), 1)

    def test_identity_readiness_requires_an_onboarded_space(self):
        env = FakeEnv(registration=_Model(ids=[]))
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_data_space_identities_enrolled(env, purpose="demo")
        self.assertIn("ONBOARDING_REQUIRED", str(ctx.exception))


class ReadinessGateTest(unittest.TestCase):
    def test_readiness_fails_closed_without_an_onboarded_company(self):
        env = FakeEnv(registration=_Model(ids=[]))
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_business_data_space_ready(env)
        self.assertIn("ONBOARDING_REQUIRED", str(ctx.exception))

    def test_readiness_passes_with_an_onboarded_company(self):
        env = FakeEnv(registration=_Model(ids=[7]))
        self.assertTrue(provisioning.assert_business_data_space_ready(env))

    def test_readiness_never_accepts_the_bootstrap_company(self):
        registration = _Model(ids=[7])
        env = FakeEnv(registration=registration)
        provisioning.assert_business_data_space_ready(env, purpose="demo")
        domain = registration.domains[-1]
        self.assertIn(("company_id.is_platform_bootstrap_company", "=", False), domain)
        self.assertIn(("data_purpose", "=", "demo"), domain)

    def test_bootstrap_company_ids_are_resolved_from_the_marker(self):
        company = _Model(ids=[1])
        env = FakeEnv(company=company)
        self.assertEqual(provisioning.bootstrap_company_ids(env), [1])
        self.assertIn(("is_platform_bootstrap_company", "=", True), company.domains[-1])

    def test_unregistered_company_ownership_is_reported(self):
        registration = _Model(ids=[7])
        env = FakeEnv(registration=registration)
        self.assertEqual(provisioning.unregistered_business_companies(env, [7, 9]), [9])
        self.assertEqual(provisioning.unregistered_business_companies(env, []), [])

    def test_business_data_owners_are_read_per_company_owned_model(self):
        env = FakeEnv(models={
            "payment.request": _Model(owners={7: 34891, 9: 2}, field_names=("company_id",)),
            "no.company.field": _Model(owners={3: 1}, field_names=("name",)),
        })
        self.assertEqual(
            provisioning.business_data_company_ids(
                env, ("payment.request", "no.company.field", "not.installed")),
            [7, 9],
        )

    def test_business_data_ownership_fails_closed_for_an_unregistered_owner(self):
        env = FakeEnv(
            registration=_Model(ids=[7]),
            models={"payment.request": _Model(owners={7: 5, 9: 2}, field_names=("company_id",))},
        )
        with self.assertRaises(ValueError) as ctx:
            provisioning.assert_business_data_ownership_registered(env, ("payment.request",))
        self.assertIn("DATA_SPACE_UNREGISTERED_BUSINESS_DATA_OWNER:9", str(ctx.exception))

    def test_business_data_ownership_passes_when_every_owner_is_onboarded(self):
        env = FakeEnv(
            registration=_Model(ids=[7]),
            models={"payment.request": _Model(owners={7: 5}, field_names=("company_id",))},
        )
        self.assertEqual(
            provisioning.assert_business_data_ownership_registered(env, ("payment.request",)),
            [7],
        )

    def test_business_data_ownership_passes_before_any_row_exists(self):
        env = FakeEnv(registration=_Model(ids=[]),
                      models={"payment.request": _Model(field_names=("company_id",))})
        self.assertEqual(
            provisioning.assert_business_data_ownership_registered(env, ("payment.request",)),
            [],
        )

    def test_bootstrap_company_business_rows_are_reported(self):
        env = FakeEnv(
            company=_Model(ids=[1]),
            models={
                "payment.request": _Model(count=3, field_names=("company_id",)),
                "sc.workbench.item": _Model(count=0, field_names=("company_id",)),
                "no.company.field": _Model(count=5, field_names=("name",)),
            },
        )
        violations = provisioning.bootstrap_company_business_data_violations(
            env, ("payment.request", "sc.workbench.item", "no.company.field")
        )
        self.assertEqual(violations, ["bootstrap_company_carries_business_data:1:payment.request:3"])


if __name__ == "__main__":
    unittest.main()
