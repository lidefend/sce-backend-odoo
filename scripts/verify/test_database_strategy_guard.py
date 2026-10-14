"""Unit tests for the declarative database-strategy guard (pure file checks)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify import database_strategy_guard as guard

ROOT = Path(__file__).resolve().parents[2]


def base_declaration():
    return json.loads((ROOT / guard.DECLARATION).read_text(encoding="utf-8"))


class DatabaseStrategyGuardTest(unittest.TestCase):
    def check(self, declaration):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / guard.DECLARATION
            target.parent.mkdir(parents=True, exist_ok=True)
            if declaration is not None:
                target.write_text(json.dumps(declaration), encoding="utf-8")
            return guard.check(root=Path(tmp), declaration_path=guard.DECLARATION)

    def test_repository_declaration_passes(self):
        self.assertEqual(guard.check(), [])

    def test_missing_declaration_fails_closed(self):
        self.assertTrue(self.check(None))

    def test_invalid_json_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / guard.DECLARATION
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("{not json", encoding="utf-8")
            failures = guard.check(root=Path(tmp), declaration_path=guard.DECLARATION)
        self.assertTrue(any("invalid JSON" in failure for failure in failures))

    def test_missing_environment_role_fails(self):
        declaration = base_declaration()
        declaration["environment_roles"].pop("customer_production")
        failures = self.check(declaration)
        self.assertTrue(any("customer_production is required" in failure for failure in failures))

    def test_unknown_strategy_fails(self):
        declaration = base_declaration()
        declaration["environment_roles"]["industry_acceptance"]["strategy"] = "shared"
        failures = self.check(declaration)
        self.assertTrue(any("unknown strategy" in failure for failure in failures))

    def test_bootstrap_company_carrying_business_data_fails(self):
        declaration = base_declaration()
        declaration["environment_roles"]["platform_internal_demo"][
            "bootstrap_company_carries_business_data"
        ] = True
        failures = self.check(declaration)
        self.assertTrue(any("never carry business data" in failure for failure in failures))

    def test_customer_production_without_dedicated_database_fails(self):
        declaration = base_declaration()
        declaration["environment_roles"]["customer_production"]["strategy"] = (
            "single_db_multi_company"
        )
        failures = self.check(declaration)
        self.assertTrue(
            any("dedicated database" in failure for failure in failures), failures
        )

    def test_initialization_order_must_be_canonical(self):
        declaration = base_declaration()
        order = list(declaration["environment_roles"]["industry_acceptance"]["initialization_order"])
        order[4], order[5] = order[5], order[4]
        declaration["environment_roles"]["industry_acceptance"]["initialization_order"] = order
        failures = self.check(declaration)
        self.assertTrue(any("canonical order" in failure for failure in failures))

    def test_sharing_one_business_database_between_customers_is_never_allowed(self):
        declaration = base_declaration()
        declaration["strategies"]["single_db_multi_company"][
            "allows_multiple_customers_in_one_business_database"
        ] = True
        failures = self.check(declaration)
        self.assertTrue(
            any("allows_multiple_customers" in failure for failure in failures), failures
        )

    def test_missing_invariant_fails(self):
        declaration = base_declaration()
        declaration["invariants"] = [
            item for item in declaration["invariants"] if item != "onboarding_precedes_industry_initialization"
        ]
        failures = self.check(declaration)
        self.assertTrue(
            any("onboarding_precedes_industry_initialization" in failure for failure in failures),
            failures,
        )

    def test_unknown_data_purpose_fails(self):
        declaration = copy.deepcopy(base_declaration())
        declaration["environment_roles"]["platform_internal_demo"]["data_purpose"] = "shared"
        failures = self.check(declaration)
        self.assertTrue(any("data_purpose" in failure for failure in failures), failures)


if __name__ == "__main__":
    unittest.main()
