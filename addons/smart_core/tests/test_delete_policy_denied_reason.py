#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A delete policy that declares a state gate must also declare why it denies.

`allowed_states` tells a terminal which states may be deleted.  A record outside
those states is denied, and without a declared denial reason the terminal can
only invent one.  Two layers are proven here:

* the P0 normalizer (`smart_core.utils.delete_policy`) makes the reason
  non-optional for a declared state gate and never invents one for a policy that
  declares no gate;
* the P1 industry policy map (`smart_construction_core`) declares the business
  wording, and it survives normalization to the contract payload.
"""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SMART_CORE = ROOT / "addons/smart_core"
DELETE_POLICY_PATH = SMART_CORE / "utils/delete_policy.py"
CONSTRUCTION_POLICY_MAP_PATH = ROOT / "addons/smart_construction_core/core_extension_policy_maps.py"


def _install_module(name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _Hook:
    """Stands in for the extension hook so the P1 payload can be injected."""

    payload = None

    @classmethod
    def call(cls, _env, _name, _default=None):
        return cls.payload


def _load_delete_policy():
    for name in list(sys.modules):
        if name == "odoo" or name.startswith("odoo."):
            sys.modules.pop(name, None)
    _install_module("odoo")
    _install_module("odoo.addons")
    smart_core = _install_module("odoo.addons.smart_core")
    smart_core.__path__ = [str(SMART_CORE)]
    utils = _install_module("odoo.addons.smart_core.utils")
    utils.__path__ = [str(SMART_CORE / "utils")]
    _install_module("odoo.addons.smart_core.utils.extension_hooks", call_extension_hook_first=_Hook.call)
    module_name = "odoo.addons.smart_core.utils.delete_policy"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, DELETE_POLICY_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _load_policy_maps():
    module_name = "smart_construction_core.core_extension_policy_maps"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, CONSTRUCTION_POLICY_MAP_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class DeletePolicyDeniedReasonShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = _load_delete_policy()

    def _normalize(self, raw):
        return self.policy._normalize_policy("x.document", raw, source="test")

    def test_a_declared_state_gate_always_names_a_denial_reason(self):
        row = self._normalize({
            "allowed": True,
            "delete_mode": "unlink",
            "policy_kind": "state_limited_business_document",
            "state_field": "state",
            "allowed_states": ["draft", "cancel"],
            "reason_code": "DRAFT_BUSINESS_DOCUMENT_DELETE_ALLOWED",
        })
        self.assertEqual(row["allowed_states"], ["cancel", "draft"])
        self.assertEqual(row["reason_code"], "DRAFT_BUSINESS_DOCUMENT_DELETE_ALLOWED")
        self.assertEqual(row["denied_reason_code"], self.policy.DELETE_POLICY_STATE_DENIED)
        self.assertNotEqual(row["denied_reason_code"], row["reason_code"])

    def test_a_blocked_states_gate_is_covered_too(self):
        row = self._normalize({"allowed": True, "delete_mode": "unlink", "blocked_states": ["done"]})
        self.assertEqual(row["denied_reason_code"], self.policy.DELETE_POLICY_STATE_DENIED)

    def test_an_explicit_denial_reason_is_preserved(self):
        row = self._normalize({
            "allowed": True,
            "delete_mode": "unlink",
            "allowed_states": ["draft"],
            "denied_reason_code": "BUSINESS_DOCUMENT_STATE_NOT_DELETABLE",
            "denied_message": "该合同记录已形成业务事实，仅未提交状态可删除。",
        })
        self.assertEqual(row["denied_reason_code"], "BUSINESS_DOCUMENT_STATE_NOT_DELETABLE")
        self.assertEqual(row["denied_message"], "该合同记录已形成业务事实，仅未提交状态可删除。")

    def test_a_policy_without_a_state_gate_invents_no_denial_reason(self):
        row = self._normalize({"allowed": True, "delete_mode": "unlink"})
        self.assertNotIn("denied_reason_code", row)
        self.assertNotIn("denied_message", row)

    def test_a_denied_model_keeps_its_model_level_reason_and_no_state_reason(self):
        row = self._normalize({"allowed": False, "delete_mode": "none"})
        self.assertEqual(row["reason_code"], self.policy.DELETE_POLICY_DENIED)
        self.assertNotIn("denied_reason_code", row)

    def test_blank_declared_values_are_not_carried_as_reasons(self):
        row = self._normalize({
            "allowed": True,
            "delete_mode": "unlink",
            "allowed_states": ["draft"],
            "denied_reason_code": "   ",
            "denied_message": "",
        })
        self.assertEqual(row["denied_reason_code"], self.policy.DELETE_POLICY_STATE_DENIED)
        self.assertNotIn("denied_message", row)


class DeletePolicyEndToEndReasonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = _load_delete_policy()
        cls.maps = _load_policy_maps()

    def setUp(self):
        _Hook.payload = dict(self.maps.API_DATA_DRAFT_UNLINK_POLICIES)

    def tearDown(self):
        _Hook.payload = None

    def test_the_construction_policy_map_declares_a_business_denial_reason(self):
        policies = self.maps.API_DATA_DRAFT_UNLINK_POLICIES
        self.assertTrue(policies)
        for model, row in policies.items():
            with self.subTest(model=model):
                self.assertEqual(row["policy_kind"], "state_limited_business_document")
                self.assertTrue(str(row.get("state_field") or "").strip())
                self.assertTrue(row.get("allowed_states"))
                self.assertEqual(row["denied_reason_code"], "BUSINESS_DOCUMENT_STATE_NOT_DELETABLE")
                self.assertTrue(str(row.get("denied_message") or "").strip())
                self.assertNotEqual(row["denied_reason_code"], row["reason_code"])

    def test_the_declared_reason_survives_normalization(self):
        row = self.policy.resolve_unlink_policy(None, "payment.request")
        self.assertTrue(row["allowed"])
        self.assertEqual(row["delete_mode"], "unlink")
        self.assertEqual(row["allowed_states"], ["cancel", "cancelled", "draft"])
        self.assertEqual(row["denied_reason_code"], "BUSINESS_DOCUMENT_STATE_NOT_DELETABLE")
        self.assertIn("付款申请", row["denied_message"])

    def test_a_model_outside_the_map_still_denies_without_inventing_a_state_reason(self):
        row = self.policy.resolve_unlink_policy(None, "x.unlisted.model")
        self.assertFalse(row["allowed"])
        self.assertEqual(row["reason_code"], self.policy.DELETE_POLICY_DENIED)
        self.assertNotIn("denied_reason_code", row)

    def test_the_p1_denial_message_names_the_document_not_the_terminal(self):
        row = self.policy.resolve_unlink_policy(None, "sc.general.contract")
        self.assertIn("综合合同", row["denied_message"])
        self.assertNotIn("前端", row["denied_message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
