"""Pure decision tests for the platform database governance vocabulary.

The module under test imports nothing from odoo, so these tests drive it with
plain values. Real ORM enforcement (lifecycle entries, maintenance access,
business-scope boundary) stays with the model tests.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


governance = load(
    "addons/smart_core/security/database_governance.py", "governance_under_test"
)
DECLARATION = ROOT / "addons/smart_core/data/tenant/database_strategy.v1.json"


class TestPlatformDatabaseGovernanceDeclaration(unittest.TestCase):
    def test_repository_declaration_is_governance_compliant(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        self.assertEqual(governance.validate_governance_declaration(declaration), [])

    def test_all_four_responsibility_layers_are_declared(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        layers = declaration["responsibility_layers"]
        for layer in governance.RESPONSIBILITY_LAYERS:
            self.assertIn(layer, layers)
            self.assertEqual(sorted(layers[layer]["owns"]), sorted(governance.LAYER_RESPONSIBILITIES[layer]))

    def test_every_layer_keeps_its_forbidden_responsibilities(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        for layer, forbidden in governance.LAYER_FORBIDDEN_RESPONSIBILITIES.items():
            declared = set(declaration["responsibility_layers"][layer]["must_not_own"])
            self.assertTrue(set(forbidden).issubset(declared), layer)

    def test_platform_management_layer_may_not_own_business_record_read(self):
        with self.assertRaises(ValueError):
            governance.validate_layer_responsibilities(
                "platform_database_management", ["business_record_read"]
            )
        with self.assertRaises(ValueError):
            governance.validate_layer_responsibilities("demo", ["guard_bypass"])
        self.assertTrue(
            governance.validate_layer_responsibilities(
                "platform_database_management", ["provisioning", "database_audit"]
            )
        )

    def test_missing_declaration_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                governance.load_declaration(Path(folder) / "absent.json")

    def test_extra_lifecycle_state_is_reported(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["database_lifecycle"]["transitions"]["active"].append("purged")
        failures = governance.validate_governance_declaration(declaration)
        self.assertTrue(any("active" in failure for failure in failures))

    def test_maintenance_access_may_not_grant_business_scope(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["maintenance_access"]["grants_business_data_scope"] = True
        failures = governance.validate_governance_declaration(declaration)
        self.assertIn("maintenance_access: grants_business_data_scope must be false", failures)

    def test_missing_responsibility_layer_is_reported(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["responsibility_layers"].pop("demo")
        failures = governance.validate_governance_declaration(declaration)
        self.assertTrue(any("demo is not declared" in failure for failure in failures))

    def test_missing_data_read_invariant_is_reported(self):
        declaration = json.loads(DECLARATION.read_text(encoding="utf-8"))
        declaration["invariants"] = [
            name
            for name in declaration["invariants"]
            if name != "platform_database_management_never_grants_business_data_read"
        ]
        failures = governance.validate_governance_declaration(declaration)
        self.assertTrue(any("platform_database_management_never" in f for f in failures))


class TestPlatformDatabaseGovernanceLifecycle(unittest.TestCase):
    def test_initial_and_terminal_states(self):
        self.assertEqual(governance.DATABASE_LIFECYCLE_INITIAL_STATE, "declared")
        self.assertEqual(governance.DATABASE_LIFECYCLE_TERMINAL_STATES, ("retired",))
        self.assertEqual(governance.DATABASE_LIFECYCLE_TRANSITIONS["retired"], ())

    def test_legal_and_illegal_transitions(self):
        self.assertEqual(
            governance.validate_lifecycle_transition("declared", "provisioned"), "provisioned"
        )
        for pair in (
            ("declared", "active"),
            ("provisioned", "suspended"),
            ("retired", "active"),
            ("active", "provisioned"),
        ):
            with self.assertRaises(ValueError):
                governance.validate_lifecycle_transition(*pair)

    def test_unknown_state_is_refused(self):
        with self.assertRaises(ValueError):
            governance.validate_lifecycle_state("migrating")

    def test_every_operation_resolves_to_a_legal_target(self):
        legal_source = {
            "provision": "declared",
            "activate": "provisioned",
            "suspend": "active",
            "resume": "suspended",
            "retire": "active",
            "abandon": "declared",
        }
        self.assertEqual(set(legal_source), set(governance.DATABASE_OPERATION_TARGET_STATE))
        self.assertEqual(set(legal_source), set(governance.DATABASE_OPERATION_SOURCE_STATES))
        for operation, sources in governance.DATABASE_OPERATION_SOURCE_STATES.items():
            self.assertIn(legal_source[operation], sources)
        for operation, target in governance.DATABASE_OPERATION_TARGET_STATE.items():
            self.assertEqual(
                governance.resolve_operation_target_state(legal_source[operation], operation), target
            )
        with self.assertRaises(ValueError):
            governance.resolve_operation_target_state("active", "explode")
        # activate is only legal from provisioned, resume only from suspended,
        # so picking the wrong entry is refused even though both land on active
        with self.assertRaises(ValueError):
            governance.resolve_operation_target_state("suspended", "activate")
        with self.assertRaises(ValueError):
            governance.resolve_operation_target_state("provisioned", "resume")
        with self.assertRaises(ValueError):
            governance.resolve_operation_target_state("active", "activate")
        with self.assertRaises(ValueError):
            governance.resolve_operation_target_state("declared", "suspend")
        self.assertEqual(
            governance.resolve_operation_target_state("declared", "abandon"), "retired"
        )
        self.assertEqual(
            governance.resolve_operation_target_state("suspended", "retire"), "retired"
        )

    def test_principal_rule_is_fail_closed(self):
        governance.validate_database_governance_principal(uid=1, superuser_id=1, su=True)
        with self.assertRaises(PermissionError):
            governance.validate_database_governance_principal(uid=1, superuser_id=1, su=False)
        with self.assertRaises(PermissionError):
            # a sudo() product administrator is not the governed principal
            governance.validate_database_governance_principal(uid=42, superuser_id=1, su=True)


class TestPlatformDatabaseGovernanceMaintenanceAccess(unittest.TestCase):
    def test_capability_vocabulary(self):
        for capability in governance.MAINTENANCE_ACCESS_CAPABILITIES:
            self.assertEqual(governance.validate_maintenance_capability(capability), capability)
        with self.assertRaises(ValueError):
            governance.validate_maintenance_capability("drop_table")

    def test_max_validity_is_bounded(self):
        self.assertGreater(governance.MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS, 0)
        self.assertLessEqual(governance.MAINTENANCE_ACCESS_MAX_VALIDITY_HOURS, 168)

    def test_maintenance_access_is_never_a_business_data_grant(self):
        self.assertFalse(governance.MAINTENANCE_ACCESS_GRANTS_BUSINESS_DATA_SCOPE)
        self.assertFalse(governance.maintenance_access_grants_business_data_scope())


if __name__ == "__main__":
    unittest.main()
