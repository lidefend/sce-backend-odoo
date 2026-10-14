"""Pure decision tests for the governed business data-space onboarding module.

The module under test imports nothing from odoo, so these tests drive it with a
plain mapping. Real ORM enforcement stays with the registration model tests.
"""
import importlib.util
import unittest
from pathlib import Path

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
    def __init__(self, *, ids=(), count=0, created=None, field_names=()):
        self._ids = list(ids)
        self._count = count
        self._created = created if created is not None else []
        self._fields = {name: None for name in field_names}
        self.domains = []

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


class FakeEnv(dict):
    def __init__(self, company=None, registration=None, models=None):
        super().__init__()
        self["res.company"] = company or _Model()
        self["sc.tenant.company.registration"] = registration or _Model()
        for name, model in (models or {}).items():
            self[name] = model


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
