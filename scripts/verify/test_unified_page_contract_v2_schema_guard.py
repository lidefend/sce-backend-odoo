#!/usr/bin/env python3
"""Pin the Web business-purpose derivation check to an exact predicate.

`DECLARED_BUSINESS_PURPOSES` must be the complement of `NON_BUSINESS_PURPOSES`.
Matching only the `ACTION_PURPOSES.filter(` shape would accept a widened
predicate that silently drops a purpose from the derived set while the two
literal lists still compare equal -- the drift this guard exists to catch.
"""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from unified_page_contract_v2_schema_guard import (
    OPTIONAL_TOP_LEVEL_KEYS,
    TOP_LEVEL_PROPERTIES,
    ts_derives_business_list,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"

VALID_ACTION_SEMANTICS = {
    "kind": "business",
    "purpose": "complete",
    "executor": "contract.action",
    "origin": "workflow.contract.service",
}
VALID_CREATE_CATALOG = {
    "source": {
        "kind": "sc_backend_workflow_action_catalog",
        "projection_only": True,
    },
    "model": "payment.request",
    "availabilityScope": "declaration_only",
    "actions": [
        {
            "key": "done",
            "method": "action_done",
            "intent": "server.object",
            "kind": "transition",
            "action_semantics": VALID_ACTION_SEMANTICS,
        },
        {
            "key": "save_draft",
            "method": None,
            "intent": "data.write",
            "kind": "save",
        },
    ],
    "submissionRequirements": [],
}
VALID_RECORD_CONTRACT = {
    "source": {
        "kind": "sc_backend_workflow_contract",
        "authorities": ["odoo_model_state", "business_model_methods"],
        "projection_only": True,
        "rebuildable": True,
        "runtime_carrier": "sc.workflow.contract.service",
    },
    "model": "payment.request",
    "record_id": 101,
    "availabilityScope": "record",
    "stateField": "state",
    "rawState": "approved",
    "businessPhase": "approved",
    "approvalPhase": "approved",
    "editability": "readonly",
    "statusbar": {
        "field": "state",
        "current": "approved",
        "states": [
            {"value": "approved", "label": "已批准"},
            {"value": "done", "label": "已完成"},
        ],
        "readonly": True,
        "source": "workflowContract",
    },
    "evidenceGate": [
        {
            "reasonCode": "PAYMENT_EXECUTION_REQUIRED",
            "message": "付款申请必须通过专业付款登记完成实付。",
            "actionKeys": ["done"],
            "blocking": True,
            "severity": "block",
        }
    ],
    "submissionRequirements": [],
    "actions": VALID_CREATE_CATALOG["actions"],
    "availableActions": [
        {
            "key": "done",
            "label": "完成",
            "intent": "server.object",
            "kind": "transition",
            "action_semantics": VALID_ACTION_SEMANTICS,
            "method": "action_done",
            "enabled": False,
            "reason_code": "PAYMENT_EXECUTION_REQUIRED",
            "blocked_message": "付款申请必须通过专业付款登记完成实付。",
            "target": {
                "model": "payment.request",
                "id": 101,
                "method": "action_done",
            },
        }
    ],
}


def workflow_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator({
        "$ref": "#/properties/workflowContract",
        "properties": schema["properties"],
        "$defs": schema["$defs"],
    })


CONTROLLED = (
    "export const ACTION_PURPOSES = Object.freeze(['save_draft', 'submit', 'return'] as const);\n"
    "export const NON_BUSINESS_PURPOSES = Object.freeze(['save_draft', 'return'] as const);\n"
    "export const DECLARED_BUSINESS_PURPOSES = Object.freeze(\n"
    "  ACTION_PURPOSES.filter((purpose) => !(NON_BUSINESS_PURPOSES as readonly string[]).includes(purpose)),\n"
    ");\n"
)

WIDENED_PREDICATE = CONTROLLED.replace(
    ".includes(purpose)),",
    ".includes(purpose) && purpose !== 'submit'),",
)
RESTATED_LIST = (
    "export const DECLARED_BUSINESS_PURPOSES = Object.freeze(['submit'] as const);\n"
)


class BusinessPurposeDerivationTest(unittest.TestCase):
    def test_the_controlled_predicate_is_accepted(self) -> None:
        self.assertTrue(ts_derives_business_list(CONTROLLED))

    def test_an_extra_predicate_is_rejected(self) -> None:
        self.assertNotEqual(WIDENED_PREDICATE, CONTROLLED)
        self.assertFalse(ts_derives_business_list(WIDENED_PREDICATE))

    def test_a_restated_list_is_rejected(self) -> None:
        self.assertFalse(ts_derives_business_list(RESTATED_LIST))

    def test_notice_contract_remains_a_declared_optional_surface(self) -> None:
        self.assertIn("noticeContract", OPTIONAL_TOP_LEVEL_KEYS)
        self.assertIn("noticeContract", TOP_LEVEL_PROPERTIES)

    def test_create_and_record_contract_shapes_are_schema_valid(self) -> None:
        validator = workflow_validator()
        for label, payload in (
            ("create", VALID_CREATE_CATALOG),
            ("record", VALID_RECORD_CONTRACT),
        ):
            with self.subTest(shape=label):
                self.assertEqual(list(validator.iter_errors(payload)), [])

    def test_create_catalog_cannot_claim_record_execution_authority(self) -> None:
        validator = workflow_validator()
        invalid = copy.deepcopy(VALID_CREATE_CATALOG)
        invalid["record_id"] = 101
        invalid["availableActions"] = []
        self.assertTrue(list(validator.iter_errors(invalid)))

    def test_disabled_action_requires_reason_and_message(self) -> None:
        validator = workflow_validator()
        invalid = copy.deepcopy(VALID_RECORD_CONTRACT)
        invalid["availableActions"][0]["reason_code"] = ""
        invalid["availableActions"][0]["blocked_message"] = ""
        self.assertTrue(list(validator.iter_errors(invalid)))


if __name__ == "__main__":
    unittest.main()
