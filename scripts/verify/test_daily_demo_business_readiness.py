import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from scripts.verify.daily_demo_business_readiness import observe, run_check, verdict, scenario_inventory


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

    def test_scenario_observation_uses_read_only_transaction(self):
        cursor = SimpleNamespace(dbname="sc_demo", rollback=Mock(), execute=Mock(), commit=Mock())
        with patch.dict("os.environ", {"DAILY_DEMO_OBSERVATION": "scenario"}), patch(
            "scripts.verify.daily_demo_business_readiness.scenario_inventory", return_value={"status": "PASS"}
        ) as inventory:
            environment = SimpleNamespace(cr=cursor)
            self.assertEqual(observe(environment)["status"], "PASS")
            inventory.assert_called_once_with(environment)
        cursor.execute.assert_any_call("SET TRANSACTION READ ONLY")
        self.assertEqual(cursor.rollback.call_count, 2)
        cursor.commit.assert_not_called()


class ScenarioInventoryTests(unittest.TestCase):
    def environment(self, has_exemption):
        menu = SimpleNamespace(id=7, sc_scenario_exempt=False)
        menus = Mock()
        menus.sudo.return_value = menus
        menus.with_context.return_value = menus
        menus._fields = {"sc_scenario_exempt": object()} if has_exemption else {}
        menus.search.return_value.ids = []
        params = Mock()
        params.sudo.return_value = params
        params.get_param.return_value = False

        class Env:
            cr = SimpleNamespace(dbname="sc_demo")
            def __contains__(self, name):
                return False
            def __getitem__(self, name):
                return {"ir.ui.menu": menus, "ir.config_parameter": params}[name]
            def ref(self, xmlid, raise_if_not_found=False):
                return menu
        return Env(), menus, params

    def test_old_schema_does_not_claim_missing_or_exempt(self):
        env, menus, params = self.environment(False)
        result = scenario_inventory(env)
        self.assertFalse(result["schema_available"]["explicit_exemption"])
        self.assertIsNone(result["searchable_exempt_menu_ids"])
        self.assertTrue(all(row["explicit_exemption"] is None for row in result["configuration_entries"]))
        menus.search.assert_not_called()
        params.set_param.assert_not_called()

    def test_revoked_declaration_is_reported_without_repair(self):
        env, menus, params = self.environment(True)
        result = scenario_inventory(env)
        self.assertEqual(len(result["configuration_entries"]), 5)
        self.assertTrue(all(row["explicit_exemption"] is False for row in result["configuration_entries"]))
        self.assertEqual(result["database_writes"], 0)
        menus.write.assert_not_called()
        params.set_param.assert_not_called()


class ApprovedScenarioConfigurationTests(unittest.TestCase):
    def test_exact_identity_and_binding_are_required(self):
        from scripts.ops.daily_demo_scenario_configuration import MENUS, EXPECTED_UUID, validate_checkpoint
        rows = [dict(xmlid=key, id=value, action='ir.actions.act_window(1,)', bound=False, exempt=False)
                for key, value in MENUS.items()]
        validate_checkpoint('sc_demo', EXPECTED_UUID, rows)
        with self.assertRaises(RuntimeError):
            validate_checkpoint('sc_demo', 'different', rows)
        with self.assertRaises(RuntimeError):
            validate_checkpoint('sc_demo', EXPECTED_UUID, rows[:-1])
        rows[0]['bound'] = True
        with self.assertRaises(RuntimeError):
            validate_checkpoint('sc_demo', EXPECTED_UUID, rows)

    def test_no_approval_means_no_environment_access(self):
        from scripts.ops.daily_demo_scenario_configuration import configure
        with patch.dict('os.environ', {'SC_SCENARIO_CONFIGURATION_PHASE': 'apply',
                                       'SC_SCENARIO_CONFIGURATION_CONFIRM': ''}):
            with self.assertRaisesRegex(RuntimeError, 'approval'):
                configure(None)


class NavigationAuthorityCoverageTests(unittest.TestCase):
    def test_menu_outside_scope_is_still_checked(self):
        from scripts.verify.daily_demo_business_readiness import navigation_authority_mismatches
        decision = Mock(side_effect=[True, False])
        result = navigation_authority_mismatches({(1, 10), (999, 20)}, {}, decision)
        self.assertEqual(result, [{'menu_id': 999, 'action_id': 20}])
        self.assertEqual(decision.call_count, 2)

    def test_no_navigation_is_not_acceptance(self):
        from scripts.verify.daily_demo_business_readiness import navigation_authority_mismatches
        with self.assertRaisesRegex(RuntimeError, 'Nonzero'):
            navigation_authority_mismatches(set(), {}, Mock())
