from __future__ import annotations

import ast
import unittest

from scripts.verify.app_config_engine_boundary_guard import (
    _call_has_true_keyword,
    _called_get_keys,
    _called_get_keys_without_false_guard,
    _called_attribute_names,
    _function,
    _function_arg_names,
)


class AppConfigEngineAuthorityGuardTest(unittest.TestCase):
    def parse(self, source: str) -> ast.Module:
        return ast.parse(source)

    def test_detects_acl_keyword_on_real_call_shape(self):
        function = _function(
            self.parse("def assemble_page_contract():\n    cfg.get_action_contract(filter_runtime=True, check_model_acl=True)\n"),
            "assemble_page_contract",
        )
        self.assertTrue(_call_has_true_keyword(function, "get_action_contract", "check_model_acl"))

    def test_rejects_missing_or_false_acl_keyword(self):
        missing = _function(self.parse("def assemble_page_contract():\n    cfg.get_action_contract()\n"), "assemble_page_contract")
        denied = _function(
            self.parse("def assemble_page_contract():\n    cfg.get_action_contract(check_model_acl=False)\n"),
            "assemble_page_contract",
        )
        self.assertFalse(_call_has_true_keyword(missing, "get_action_contract", "check_model_acl"))
        self.assertFalse(_call_has_true_keyword(denied, "get_action_contract", "check_model_acl"))

    def test_only_counts_direct_ui_get_action_carriers(self):
        function = _function(
            self.parse(
                "def _append_ui_contract_actions(ui, other):\n"
                "    ui.get('buttons')\n"
                "    ui.get('action_groups')\n"
                "    other.get('business_actions')\n"
            ),
            "_append_ui_contract_actions",
        )
        self.assertEqual(_called_get_keys(function, "ui"), {"buttons", "action_groups"})

    def test_top_level_action_carriers_require_no_explicit_form_branch(self):
        guarded = _function(
            self.parse(
                "def _append_ui_contract_actions(ui, explicit_form_view):\n"
                "    if not explicit_form_view:\n"
                "        ui.get('business_actions')\n"
                "        ui.get('action_groups')\n"
                "    else:\n"
                "        ui.get('buttons')\n"
            ),
            "_append_ui_contract_actions",
        )
        unguarded = _function(
            self.parse(
                "def _append_ui_contract_actions(ui, explicit_form_view):\n"
                "    ui.get('business_actions')\n"
                "    if explicit_form_view:\n"
                "        ui.get('action_groups')\n"
            ),
            "_append_ui_contract_actions",
        )
        self.assertEqual(
            _called_get_keys_without_false_guard(guarded, "ui", "explicit_form_view"),
            {"buttons"},
        )
        self.assertEqual(
            _called_get_keys_without_false_guard(unguarded, "ui", "explicit_form_view"),
            {"business_actions", "action_groups"},
        )

    def test_function_argument_detection_is_structural(self):
        function = _function(
            self.parse("def get_search_contract(self, *, action_id=None):\n    return action_id\n"),
            "get_search_contract",
        )
        self.assertEqual(_function_arg_names(function), {"self", "action_id"})

    def test_server_action_execution_call_detection_is_structural(self):
        dispatch = _function(
            self.parse("def dispatch(self):\n    return self.resolver.materialize_server_action({}, {})\n"),
            "dispatch",
        )
        safe = _function(self.parse("def dispatch(self):\n    return self.resolver.map_server_to_window(1)\n"), "dispatch")

        self.assertIn("materialize_server_action", _called_attribute_names(dispatch))
        self.assertNotIn("materialize_server_action", _called_attribute_names(safe))


if __name__ == "__main__":
    unittest.main()
