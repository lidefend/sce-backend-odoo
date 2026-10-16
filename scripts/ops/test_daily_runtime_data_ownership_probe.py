#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import unittest
from unittest import mock
from pathlib import Path


SCRIPT = Path(__file__).with_name("daily_runtime_data_ownership_probe.py")
SPEC = importlib.util.spec_from_file_location("daily_runtime_data_ownership_probe", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

SHA = "10bf72ef4bb060556bd2844598b58f9806392d34"


def payload(**overrides):
    base = {
        "declared_models": 2,
        "scanned_models": 2,
        "unmapped_anchor_models": [],
        "errors": {},
        "registered_company_ids": [1],
        "registered_purposes": ["customer"],
        "unset_owner_rows": {},
        "unregistered_owner_rows": {},
        "installed_rules": {},
        "modules": {
            "smart_construction_core": {
                "state": "installed",
                "installed_version": "17.0.0.171",
                "latest_version": "17.0.0.171",
            }
        },
    }
    base.update(overrides)
    return base


STRICT_DOMAIN = "[('company_id', 'in', company_ids), ('company_id', 'in', user._sc_data_company_ids())]"
SHARED_DOMAIN = "['|', ('company_id', '=', False), '&', ('company_id', 'in', company_ids), ('company_id', 'in', user._sc_data_company_ids())]"


def measured(hidden, unset, principal="57", errors=None):
    return {
        "unset_rows": unset,
        "visible_by_principal": {} if errors else {principal: 0 if hidden else unset},
        "errors_by_principal": errors or {},
    }


class PreflightTests(unittest.TestCase):
    def test_accepts_declared_inputs(self):
        # preflight behaviour is exercised through probe(); the shape checks are pure.
        self.assertTrue(module.FULL_SHA.fullmatch(SHA))
        self.assertTrue(module.DATABASE_NAME.fullmatch("sc_demo"))
        self.assertTrue(module.SSH_HOST.fullmatch("sc-root"))

    def test_rejects_unsafe_database_and_host_shapes(self):
        self.assertIsNone(module.DATABASE_NAME.fullmatch("sc_demo; rm -rf /"))
        self.assertIsNone(module.SSH_HOST.fullmatch("sc-root; rm -rf /"))
        self.assertIsNone(module.FULL_SHA.fullmatch("10bf72ef"))


class SemanticsTests(unittest.TestCase):
    def test_declaration_is_the_authority_for_unset_owner(self):
        expected = module.expected_semantics(module.declarations())
        self.assertTrue(expected["sc.dashboard.cockpit.fact"]["strict"])
        self.assertFalse(expected["payment.request"]["strict"])
        self.assertIn("source", expected["payment.request"])


class VerdictTests(unittest.TestCase):
    def test_covers_every_declared_model_is_required(self):
        verdict = module.evaluate({}, payload(scanned_models=1))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("scan_covers_every_declared_model", failed)

    def test_unregistered_owner_fails_closed(self):
        verdict = module.evaluate({}, payload(unregistered_owner_rows={"2": {"project.project": 3}}))
        self.assertFalse(verdict["passed"])
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("no_unregistered_company_owns_rows", failed)

    def test_module_version_drift_fails(self):
        drifted = payload(modules={"smart_construction_core": {
            "state": "installed", "installed_version": "17.0.0.170", "latest_version": "17.0.0.171"}})
        verdict = module.evaluate({}, drifted)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("shipping_module_version_aligned", failed)

    def test_declared_strict_model_must_be_effectively_hidden(self):
        expected = {"payment.ledger": {"strict": True, "source": "x", "basis": "named rule"}}
        still_visible = payload(
            unset_owner_rows={"payment.ledger": 7},
            installed_rules={"payment.ledger": [{"name": "r", "is_global": False, "domain": SHARED_DOMAIN, "active": True}]},
            unset_owner_visible={"payment.ledger": measured(hidden=False, unset=7)},
        )
        verdict = module.evaluate(expected, still_visible)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("effective_visibility_matches_declared_semantics", failed)

        hidden = payload(
            unset_owner_rows={"payment.ledger": 7},
            installed_rules={"payment.ledger": [{"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
            unset_owner_visible={"payment.ledger": measured(hidden=True, unset=7)},
        )
        verdict = module.evaluate(expected, hidden)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["visibility_loss_rows"]["total"], 7)
        self.assertEqual(verdict["shared_visible_rows"]["total"], 0)
        self.assertEqual(verdict["rows_not_measured_against_a_principal"]["total"], 0)

    def test_shared_semantics_keep_unset_rows_visible(self):
        expected = {"payment.request": {"strict": False, "source": "x", "basis": "unsetOwner=shared"}}
        observed = payload(
            unset_owner_rows={"payment.request": 5},
            installed_rules={"payment.request": [{"name": "r", "is_global": False, "domain": SHARED_DOMAIN, "active": True}]},
            unset_owner_visible={"payment.request": measured(hidden=False, unset=5)},
        )
        verdict = module.evaluate(expected, observed)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["shared_visible_rows"]["total"], 5)
        self.assertEqual(verdict["visibility_loss_rows"]["total"], 0)

    def test_unmeasured_declared_model_fails_closed(self):
        expected = {"sc.hr.payroll.document": {"strict": True, "source": "x", "basis": "named rule"}}
        observed = payload(
            unset_owner_rows={"sc.hr.payroll.document": 9},
            installed_rules={"sc.hr.payroll.document": [
                {"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
        )
        verdict = module.evaluate(expected, observed)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("effective_visibility_matches_declared_semantics", failed)
        self.assertEqual(verdict["rows_not_measured_against_a_principal"]["total"], 9)

    def test_erroring_principal_is_not_treated_as_measured(self):
        expected = {"payment.ledger": {"strict": True, "source": "x", "basis": "named rule"}}
        observed = payload(
            unset_owner_rows={"payment.ledger": 3},
            installed_rules={"payment.ledger": [
                {"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
            unset_owner_visible={"payment.ledger": measured(hidden=True, unset=3, errors={"57": "AccessError"})},
        )
        verdict = module.evaluate(expected, observed)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("effective_visibility_matches_declared_semantics", failed)

    def test_dotted_anchor_decomposition_must_equal_the_raw_scan(self):
        # A dotted anchor cannot be measured with a single ``(anchor, '=', False)``
        # leaf: the head-missing rows the ceiling rule marks unowned would be
        # dropped. The raw scan and the decomposition must agree.
        decomposition = {"sc.document.admin.document": {
            "head_field": "project_id", "dotted": True,
            "head_missing_any_state": 9274, "head_missing_active": 9274,
            "tail_null_any_state": 0, "tail_null_active": 0,
            "dotted_predicate_any_state": 0,
            "unset_any_state": 9274, "unset_active": 9274,
        }}
        agreed = payload(
            unset_owner_rows={"sc.document.admin.document": 9274},
            unset_owner_rows_sql={"sc.document.admin.document": 9274},
            anchor_decomposition=decomposition,
            installed_rules={"sc.document.admin.document": [
                {"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
        )
        verdict = module.evaluate({}, agreed)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["unset_owner_total"], 9274)

        disagreed = payload(
            unset_owner_rows={"sc.document.admin.document": 9274},
            unset_owner_rows_sql={"sc.document.admin.document": 9274},
            anchor_decomposition={"sc.document.admin.document": dict(
                decomposition["sc.document.admin.document"], unset_any_state=0)},
        )
        verdict = module.evaluate({}, disagreed)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("anchor_decomposition_reconciles_with_the_raw_scan", failed)

    def test_dotted_predicate_translation_is_checked_not_assumed(self):
        observed = payload(
            installed_rules={"sc.business.category": [
                {"name": "r", "is_global": False, "domain": SHARED_DOMAIN, "active": True}]},
            unset_owner_rows_sql={"sc.business.category": 47},
            anchor_decomposition={"sc.business.category": {
                "head_field": "approval_policy_id", "dotted": True,
                "head_missing_any_state": 47, "head_missing_active": 47,
                "tail_null_any_state": 0, "tail_null_active": 0,
                "dotted_predicate_any_state": 0,
                "unset_any_state": 47, "unset_active": 47,
            }},
        )
        self.assertTrue(module.evaluate({}, observed)["passed"])

        # If the plain dotted leaf ever starts matching the head-missing rows, the
        # recorded translation must be re-examined rather than silently accepted.
        drifted = payload(
            installed_rules={"sc.business.category": [
                {"name": "r", "is_global": False, "domain": SHARED_DOMAIN, "active": True}]},
            unset_owner_rows_sql={"sc.business.category": 47},
            anchor_decomposition={"sc.business.category": {
                "head_field": "approval_policy_id", "dotted": True,
                "head_missing_any_state": 47, "head_missing_active": 47,
                "tail_null_any_state": 0, "tail_null_active": 0,
                "dotted_predicate_any_state": 47,
                "unset_any_state": 47, "unset_active": 47,
            }},
        )
        verdict = module.evaluate({}, drifted)
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("declared_anchor_translation_recorded", failed)

    def test_decomposition_does_not_clobber_the_principal_measurement(self):
        # Regression: the decomposition walk must not shadow the variable that
        # carries the per-principal measurement, or every declared model would be
        # silently reported as unmeasured.
        expected = {"payment.ledger": {"strict": True, "source": "x", "basis": "named rule"}}
        observed = payload(
            unset_owner_rows={"payment.ledger": 12194},
            unset_owner_rows_active={"payment.ledger": 12194},
            unset_owner_rows_sql={"payment.ledger": 12194},
            anchor_decomposition={"payment.ledger": {
                "head_field": "company_id", "dotted": False,
                "head_missing_any_state": 12194, "head_missing_active": 12194,
                "tail_null_any_state": 0, "tail_null_active": 0,
                "dotted_predicate_any_state": 12194,
                "unset_any_state": 12194, "unset_active": 12194,
            }},
            installed_rules={"payment.ledger": [
                {"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
            unset_owner_visible={"payment.ledger": measured(hidden=True, unset=12194)},
        )
        verdict = module.evaluate(expected, observed)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["rows_not_measured_against_a_principal"]["total"], 0)
        self.assertEqual(verdict["visibility_loss_rows"]["total"], 12194)

    def test_archived_only_hidden_rows_are_separated_from_live_loss(self):
        expected = {"sc.document.admin.document": {"strict": True, "source": "x", "basis": "unsetOwner=unknown"}}
        observed = payload(
            unset_owner_rows={"sc.document.admin.document": 9274},
            unset_owner_rows_active={},
            installed_rules={"sc.document.admin.document": [
                {"name": "r", "is_global": True, "domain": STRICT_DOMAIN, "active": True}]},
            unset_owner_visible={"sc.document.admin.document": measured(hidden=True, unset=9274)},
        )
        verdict = module.evaluate(expected, observed)
        self.assertTrue(verdict["passed"])
        self.assertEqual(verdict["visibility_loss_rows"]["total"], 9274)
        self.assertEqual(
            verdict["visibility_loss_that_is_archived_only"]["total"], 9274
        )

    def test_model_without_an_active_rule_is_reported(self):
        expected = {"sc.treasury.ledger": {"strict": False, "source": "x", "basis": "unsetOwner=shared"}}
        verdict = module.evaluate(expected, payload(unset_owner_rows={"sc.treasury.ledger": 9}))
        failed = {row["id"] for row in verdict["assertions"] if not row["passed"]}
        self.assertIn("every_unset_owner_model_has_an_active_rule", failed)


class ProgramTests(unittest.TestCase):
    def test_probe_program_is_read_only(self):
        template = module.PROBE_TEMPLATE
        for forbidden in ("unlink", ".write(", "create(", "commit("):
            self.assertNotIn(forbidden, template)

    def test_probe_uses_the_governed_shell_entry(self):
        self.assertEqual(module.REMOTE_ROOT, "/opt/projects/repos/sce-product-odoo")
        self.assertIn("odoo.shell.exec", Path(SCRIPT).read_text(encoding="utf-8"))

    def test_marker_payload_round_trip(self):
        line = module.MARKER + '{"a": 1}'
        self.assertEqual(module.marker_payload("noise\n" + line), {"a": 1})
        self.assertIsNone(module.marker_payload("noise only"))


class DataOwnershipDutyBindingTests(unittest.TestCase):
    """A database *name* stops being a target identity once two carriers share it.

    The refusal is read from the shipped declaration, not from a stub: it now
    names the rebuilt demo duty and the preserved historic source with the same
    ``sc_demo``, so an entry that receives only ``--database`` would otherwise
    have to guess which carrier it is measuring.
    """

    instances = Path(__file__).with_name("synthetic_duty_instances.sample.json")

    def reader(self, _path: str) -> str:
        return self.instances.read_text(encoding="utf-8")

    def options(self, **overrides):
        options = mock.Mock()
        options.duty = ""
        options.database = "sc_demo"
        options.ssh_host = "sc-root"
        for key, value in overrides.items():
            setattr(options, key, value)
        return options

    def test_a_bare_database_name_no_longer_binds_a_carrier(self) -> None:
        with self.assertRaisesRegex(module.ProbeError, "DUTY_IDENTITY_DATABASE_AMBIGUOUS:sc_demo"):
            module.bind_target(self.options(), instances_reader=self.reader)

    def test_naming_the_duty_binds_the_rebuilt_demo_carrier(self) -> None:
        binding = module.bind_target(
            self.options(duty="demo"), instances_reader=self.reader
        )
        self.assertEqual(binding["database"], "sc_demo")
        self.assertEqual(binding["database_role"], "sc_demo_app")
        self.assertEqual(binding["compose_project"], "sc-demo-dev")
        self.assertEqual(binding["database_container"], "sc-demo-dev-db-1")
        self.assertEqual(binding["database_volume"], "sc_demo_db_data")
        self.assertEqual(binding["data_purpose"], "demo")


if __name__ == "__main__":
    unittest.main()
