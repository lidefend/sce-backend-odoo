# -*- coding: utf-8 -*-
import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _load_policy():
    root = Path(__file__).resolve().parents[1]
    addons_mod = types.ModuleType("odoo.addons")
    smart_core_mod = types.ModuleType("odoo.addons.smart_core")
    core_mod = types.ModuleType("odoo.addons.smart_core.core")
    smart_core_mod.__path__ = [str(root)]
    core_mod.__path__ = [str(root / "core")]
    sys.modules.update(
        {
            "odoo.addons": addons_mod,
            "odoo.addons.smart_core": smart_core_mod,
            "odoo.addons.smart_core.core": core_mod,
        }
    )

    module_name = "odoo.addons.smart_core.core.api_data_execution_policy"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, root / "core" / "api_data_execution_policy.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestApiDataExecutionPolicy(unittest.TestCase):
    def setUp(self):
        self.policy = _load_policy()

    def test_client_sudo_flag_is_detectable_for_audit(self):
        self.assertTrue(self.policy.client_requested_sudo({"sudo": True}))
        self.assertTrue(self.policy.client_requested_sudo({"params": {"sudo": "yes"}}))
        self.assertFalse(self.policy.client_requested_sudo({"params": {"sudo": "no"}}))

    def test_client_sudo_never_enables_api_data_sudo(self):
        self.assertFalse(self.policy.resolve_api_data_sudo({"sudo": True}))
        self.assertFalse(self.policy.resolve_api_data_sudo({"params": {"sudo": "1"}}))
        self.assertFalse(self.policy.resolve_api_data_sudo({}))

    def test_context_defaults_only_accept_real_model_fields(self):
        fields = {"project_id": object(), "amount": object()}

        self.assertEqual(
            self.policy.authoritative_context_default_fields(
                {
                    "default_project_id": 7,
                    "default_amount": 0,
                    "default_unknown": 9,
                    "search_default_project": 1,
                },
                fields,
            ),
            ("amount", "project_id"),
        )

    def test_empty_or_unknown_context_has_no_create_default_authority(self):
        fields = {"project_id": object()}

        self.assertEqual(self.policy.authoritative_context_default_fields({}, fields), ())
        self.assertEqual(
            self.policy.authoritative_context_default_fields({"default_unknown": 9}, fields),
            (),
        )

    def test_empty_vals_resolve_authoritative_orm_defaults(self):
        class _Model:
            _fields = {"project_id": object(), "amount": object(), "__technical": object()}

            def default_get(self, names):
                self.requested = tuple(names)
                return {"project_id": 7, "amount": 0, "__technical": "blocked"}

        model = _Model()

        self.assertEqual(
            self.policy.merge_orm_create_defaults(model, {}),
            {"project_id": 7, "amount": 0},
        )
        self.assertEqual(model.requested, ("project_id", "amount"))

    def test_explicit_values_win_and_unknown_values_are_removed(self):
        class _Model:
            _fields = {"project_id": object(), "amount": object()}

            def default_get(self, names):
                return {"project_id": 7, "amount": 10}

        self.assertEqual(
            self.policy.merge_orm_create_defaults(
                _Model(),
                {"amount": 25, "unknown": "discard"},
            ),
            {"project_id": 7, "amount": 25},
        )


if __name__ == "__main__":
    unittest.main()
