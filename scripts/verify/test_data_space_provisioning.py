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
    def __init__(self, company_ids):
        self.ids = list(range(1, len(company_ids) + 1))
        self.company_id = _Ids(company_ids)

    def __bool__(self):
        return bool(self.ids)


class _Model:
    def __init__(self, *, ids=(), count=0, created=None, field_names=(), creates=False):
        self._ids = list(ids)
        self._count = count
        self._created = created if created is not None else []
        self._fields = {name: None for name in field_names}
        self.domains = []
        self._creates = creates
        self._registered = []
        self._adopted = []

    def sudo(self):
        return self

    def search(self, domain):
        self.domains.append(domain)
        return _Registrations(self._ids)

    def search_count(self, domain):
        self.domains.append(domain)
        return self._count

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
        return _Recordset(ids)

    def with_context(self, **kwargs):
        return self


class _Recordset:
    def __init__(self, ids):
        self.id = int(ids)

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
