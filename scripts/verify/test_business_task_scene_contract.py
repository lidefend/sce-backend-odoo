#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons" / "smart_scene" / "schemas" / "business_task_scene_contract.py"
SPEC = importlib.util.spec_from_file_location("business_task_scene_contract", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)
check_business_task_scene_contract = MODULE.check_business_task_scene_contract
sys.path.insert(0, str(ROOT))
from addons.smart_scene.core.business_task_scene_compiler import (  # noqa: E402
    BusinessTaskCompileError,
    compile_business_task_scene_contract,
    verify_business_task_scene_contract_seal,
)
from addons.smart_scene.core.scene_contract_builder import build_scene_contract  # noqa: E402


def valid_payload() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "document.review",
            "goal": "核对单据并作出决定",
            "outcome": "形成可追溯的审核结论",
            "mode": "readonly",
            "stage": "review",
            "state": "pending",
        },
        "facts": [
            {
                "key": "document_amount",
                "label": "单据金额",
                "source_authority": "domain.document.amount",
                "applicability": "always",
            }
        ],
        "inputs": [
            {
                "key": "review_comment",
                "label": "审核意见",
                "visible": True,
                "readonly": False,
                "required": False,
                "source_authority": "domain.document.review_policy",
                "applicability": "always",
            }
        ],
        "blockers": [],
        "capabilities": [
            {
                "key": "document.approve",
                "label": "审核通过",
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "blocked_by": [],
                "reason_code": "",
                "presentation": "primary",
                "safety": "confirm",
                "idempotency": "record_transition",
                "outcome": "approved",
                "source_authority": "domain.document.available_actions",
            }
        ],
        "evidence": [
            {
                "key": "audit_history",
                "label": "审核记录",
                "source_authority": "domain.document.audit",
            }
        ],
        "relations": [
            {
                "key": "source_document",
                "label": "来源单据",
                "source_authority": "domain.document.source_anchor",
            }
        ],
        "completion": {
            "complete": False,
            "next_capability_key": "document.approve",
            "outcome_code": "PENDING_REVIEW",
        },
    }


def valid_profile() -> dict:
    return {
        "profile_version": "v1",
        "task": {
            "key": "document.review",
            "goal": "核对单据并作出决定",
            "outcome": "形成可追溯的审核结论",
        },
        "facts": [{"key": "document_amount", "label": "单据金额", "importance": "primary"}],
        "inputs": [{"key": "review_comment", "label": "审核意见", "input_kind": "text"}],
        "blockers": [],
        "capabilities": [
            {
                "key": "document.approve",
                "label": "审核通过",
                "presentation": "primary",
                "safety": "confirm",
                "idempotency": "record_transition",
                "outcome": "approved",
                "blocked_by": [],
            }
        ],
        "evidence": [{"key": "audit_history", "label": "审核记录", "kind": "audit"}],
        "relations": [{"key": "source_document", "label": "来源单据", "kind": "anchor"}],
    }


def valid_supply() -> dict:
    return {
        "task": {"mode": "readonly", "stage": "review", "state": "pending"},
        "facts": {
            "document_amount": {
                "value": 100,
                "value_state": "known",
                "source_authority": "domain.document.amount",
                "applicability": "always",
                "model": "must.not.leak",
            }
        },
        "inputs": {
            "review_comment": {
                "value": "",
                "visible": True,
                "readonly": False,
                "required": False,
                "source_authority": "domain.document.review_policy",
                "applicability": "always",
                "modifiers": {"invisible": False},
            }
        },
        "blockers": {},
        "capabilities": {
            "document.approve": {
                "visible": True,
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "reason_code": "",
                "source_authority": "domain.document.available_actions",
                "server_action_id": 91,
            }
        },
        "evidence": {
            "audit_history": {
                "state": "ready",
                "count": 1,
                "required": True,
                "source_authority": "domain.document.audit",
            }
        },
        "relations": {
            "source_document": {
                "state": "linked",
                "count": 1,
                "summary": "来源单据",
                "source_authority": "domain.document.source_anchor",
            }
        },
        "completion": {
            "complete": False,
            "next_capability_key": "document.approve",
            "outcome_code": "PENDING_REVIEW",
        },
    }


class BusinessTaskSceneContractTest(unittest.TestCase):
    def test_accepts_explicit_task_semantics(self):
        ok, detail = check_business_task_scene_contract(valid_payload())
        self.assertTrue(ok, detail)
        self.assertEqual(detail["enabled_primary_count"], 1)

    def test_rejects_native_contract_vocabulary(self):
        payload = valid_payload()
        payload["facts"][0]["modifiers"] = {"invisible": False}
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "native_vocabulary_leak")

    def test_requires_explicit_authorization_verdict(self):
        payload = valid_payload()
        del payload["capabilities"][0]["authorization_allowed"]
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "capability_verdict_required")

    def test_requires_explicit_capability_visibility_verdict(self):
        payload = valid_payload()
        del payload["capabilities"][0]["visible"]
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "capability_verdict_required")

    def test_hidden_capability_cannot_be_executable(self):
        payload = valid_payload()
        payload["capabilities"][0]["visible"] = False
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "capability_verdict_inconsistent")

    def test_disabled_capability_cannot_report_ok(self):
        payload = valid_payload()
        capability = payload["capabilities"][0]
        capability["authorization_allowed"] = False
        capability["enabled"] = False
        capability["reason_code"] = "OK"
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "disabled_capability_reason_required")

    def test_active_blocker_requires_repair_and_disables_action(self):
        payload = valid_payload()
        payload["blockers"] = [
            {
                "key": "missing_evidence",
                "active": True,
                "reason_code": "EVIDENCE_REQUIRED",
                "message": "请补充审核凭证",
                "missing_items": ["attachment"],
                "repair_capability_key": "document.attach_evidence",
                "source_authority": "domain.document.evidence_policy",
            }
        ]
        capability = payload["capabilities"][0]
        capability["blocked_by"] = ["missing_evidence"]
        capability["enabled"] = False
        capability["reason_code"] = "EVIDENCE_REQUIRED"
        repair = copy.deepcopy(capability)
        repair.update(
            {
                "key": "document.attach_evidence",
                "label": "补充凭证",
                "business_available": True,
                "authorization_allowed": True,
                "enabled": True,
                "blocked_by": [],
                "reason_code": "",
                "presentation": "recommended",
                "outcome": "evidence_attached",
            }
        )
        payload["capabilities"].append(repair)
        ok, detail = check_business_task_scene_contract(payload)
        self.assertTrue(ok, detail)

    def test_rejects_two_enabled_primary_capabilities(self):
        payload = valid_payload()
        second = copy.deepcopy(payload["capabilities"][0])
        second["key"] = "document.reject"
        payload["capabilities"].append(second)
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "multiple_enabled_primary_capabilities")

    def test_input_requires_explicit_applicability(self):
        payload = valid_payload()
        del payload["inputs"][0]["applicability"]
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "input_applicability_required")

    def test_active_blocker_requires_user_message_and_missing_items(self):
        payload = valid_payload()
        payload["blockers"] = [
            {
                "key": "missing_evidence",
                "active": True,
                "reason_code": "EVIDENCE_REQUIRED",
                "repair_capability_key": "document.approve",
                "source_authority": "domain.document.evidence_policy",
                "missing_items": [],
            }
        ]
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "active_blocker_message_required")

    def test_incomplete_task_requires_next_capability(self):
        payload = valid_payload()
        payload["completion"]["next_capability_key"] = ""
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "incomplete_task_next_capability_required")

    def test_completed_task_cannot_keep_next_capability(self):
        payload = valid_payload()
        payload["completion"]["complete"] = True
        ok, detail = check_business_task_scene_contract(payload)
        self.assertFalse(ok)
        self.assertEqual(detail["code"], "completed_task_has_next_capability")


class BusinessTaskSceneCompilerTest(unittest.TestCase):
    def test_compiles_and_seals_explicit_semantics(self):
        first = compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=valid_supply())
        second = compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=valid_supply())
        self.assertEqual(first, second)
        self.assertEqual(first["task"]["mode"], "readonly")
        self.assertEqual(first["capabilities"][0]["authorization_allowed"], True)
        self.assertEqual(len(first["trace"]["sealed_contract_sha256"]), 64)
        self.assertTrue(verify_business_task_scene_contract_seal(first))

    def test_seal_rejects_terminal_semantic_tampering(self):
        compiled = compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=valid_supply())
        compiled["task"]["state"] = "approved"
        self.assertFalse(verify_business_task_scene_contract_seal(compiled))

    def test_compiled_contract_is_isolated_from_mutable_inputs(self):
        profile = valid_profile()
        supply = valid_supply()
        compiled = compile_business_task_scene_contract(profile=profile, semantic_supply=supply)
        profile["capabilities"][0]["blocked_by"].append("late_profile_mutation")
        supply["facts"]["document_amount"]["value"] = 999
        self.assertEqual(compiled["capabilities"][0]["blocked_by"], [])
        self.assertEqual(compiled["facts"][0]["value"], 100)
        self.assertTrue(verify_business_task_scene_contract_seal(compiled))

    def test_does_not_copy_native_supply_vocabulary(self):
        compiled = compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=valid_supply())
        serialized = str(compiled)
        self.assertNotIn("must.not.leak", serialized)
        self.assertNotIn("server_action_id", serialized)
        self.assertNotIn("modifiers", serialized)

    def test_rejects_native_vocabulary_in_task_profile(self):
        profile = valid_profile()
        profile["facts"][0]["view_type"] = "form"
        with self.assertRaises(BusinessTaskCompileError) as raised:
            compile_business_task_scene_contract(profile=profile, semantic_supply=valid_supply())
        self.assertEqual(raised.exception.code, "native_vocabulary_in_profile")

    def test_missing_semantic_supply_fails_closed(self):
        supply = valid_supply()
        del supply["capabilities"]["document.approve"]
        with self.assertRaises(BusinessTaskCompileError) as raised:
            compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=supply)
        self.assertEqual(raised.exception.code, "semantic_supply_missing")

    def test_unresolved_authorization_fails_closed(self):
        supply = valid_supply()
        del supply["capabilities"]["document.approve"]["authorization_allowed"]
        with self.assertRaises(BusinessTaskCompileError) as raised:
            compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=supply)
        self.assertEqual(raised.exception.code, "compiled_contract_invalid")
        self.assertEqual(raised.exception.detail["code"], "capability_verdict_required")

    def test_inconsistent_enabled_verdict_fails_closed(self):
        supply = valid_supply()
        supply["capabilities"]["document.approve"]["business_available"] = False
        with self.assertRaises(BusinessTaskCompileError) as raised:
            compile_business_task_scene_contract(profile=valid_profile(), semantic_supply=supply)
        self.assertEqual(raised.exception.detail["code"], "capability_verdict_inconsistent")

    def test_scene_builder_embeds_terminal_profile_without_changing_v1_shape(self):
        contract = build_scene_contract(
            scene={"scene_key": "document.review", "scene_type": "detail"},
            page={"model": "x.document", "view_type": "form"},
            zones={},
            business_task_profile=valid_profile(),
            business_task_semantic_supply=valid_supply(),
        )
        self.assertEqual(contract["business_task"], contract["scene_contract_v1"]["business_task"])
        self.assertEqual(contract["business_task"]["task"]["key"], "document.review")
        self.assertIn("business_task_scene_compiler", contract["diagnostics"]["build_pipeline"])
        self.assertIn(
            "business_task_scene_compiler",
            contract["scene_contract_v1"]["diagnostics"]["build_pipeline"],
        )

    def test_scene_builder_without_task_inputs_preserves_existing_pipeline(self):
        contract = build_scene_contract(
            scene={"scene_key": "document.review", "scene_type": "detail"},
            page={"model": "x.document", "view_type": "form"},
            zones={},
        )
        self.assertNotIn("business_task", contract)
        self.assertNotIn("business_task", contract["scene_contract_v1"])
        self.assertNotIn("business_task_scene_compiler", contract["diagnostics"]["build_pipeline"])


if __name__ == "__main__":
    unittest.main()
