import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from scripts.verify.daily_demo_business_readiness import observe, run_check, verdict


class ReadinessAdapterTests(unittest.TestCase):
    def test_no_checks_is_not_pass(self):
        self.assertEqual(verdict([]), "FAIL")

    def test_assertion_failure_is_preserved(self):
        def fail():
            raise AssertionError("missing settlement")
        result = run_check("chain", fail)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["error"], "missing settlement")
        self.assertEqual(verdict([result]), "FAIL")

    def test_error_is_not_a_pass(self):
        result = run_check("missing model", lambda: {}["absent"])
        self.assertEqual(result["error_type"], "KeyError")

    def test_success_retains_measurements(self):
        result = run_check("readiness", lambda: {"hard_checks": 24})
        self.assertEqual(result["detail"]["hard_checks"], 24)
        self.assertEqual(verdict([result]), "PASS")

    def test_wrong_database_stops_before_any_transaction(self):
        class Env:
            class cr:
                dbname = "sc_platform_control"
        with self.assertRaisesRegex(RuntimeError, "demo duty"):
            observe(Env())

    def test_read_only_and_rollback_survive_probe_failure(self):
        cursor = SimpleNamespace(dbname="sc_demo", rollback=Mock(), execute=Mock(), commit=Mock())
        original = cursor.commit
        def attempt_write(env):
            env.cr.commit()
        with patch.dict("os.environ", {"DAILY_DEMO_OBSERVATION": "inventory"}), patch(
            "scripts.verify.daily_demo_business_readiness.data_inventory", side_effect=attempt_write
        ):
            with self.assertRaisesRegex(RuntimeError, "forbids commit"):
                observe(SimpleNamespace(cr=cursor))
        self.assertEqual(cursor.rollback.call_count, 2)
        cursor.execute.assert_any_call("SET TRANSACTION READ ONLY")
        self.assertIs(cursor.commit, original)
        original.assert_not_called()

    def test_success_also_rolls_back(self):
        cursor = SimpleNamespace(dbname="sc_demo", rollback=Mock(), execute=Mock(), commit=Mock())
        with patch.dict("os.environ", {"DAILY_DEMO_OBSERVATION": "inventory"}), patch(
            "scripts.verify.daily_demo_business_readiness.data_inventory", return_value={"status": "PASS"}
        ):
            self.assertEqual(observe(SimpleNamespace(cr=cursor))["status"], "PASS")
        self.assertEqual(cursor.rollback.call_count, 2)
        cursor.commit.assert_not_called()
