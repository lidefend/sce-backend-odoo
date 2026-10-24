#!/usr/bin/env python3
"""Validate the controlled draft-feedback schema with positive and negative cases."""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "addons/smart_core"))
from core.http_result_policy import result_http_status

SCHEMA = ROOT / "docs/architecture/onchange_feedback_evaluation_v1.schema.json"
ETAG = "a" * 64
BINDING = {
    "etag": ETAG,
    "model": "demo.feedback",
    "view_id": 7,
    "container_id": "feedback",
    "source_container_id": "source",
    "native_locator": "/form[1]/note[1]",
    "occurrence_index": 1,
    "component_key": "sc.feedback.message",
    "component_version": "1.0.0",
    "purpose": "advisory",
    "dependencies": [
        {"field": "business_date", "type": "date"},
        {"field": "note", "type": "text"},
    ],
    "visibility_owner": "feedback_evaluation",
}
RELATION_BINDING = {
    **BINDING,
    "container_id": "refund-feedback",
    "source_container_id": "refund-source",
    "native_locator": "/form[1]/sheet[1]/div[1]/field[1]",
    "dependencies": [
        {"field": "partner_id", "type": "many2one_presence"},
        {"field": "business_date", "type": "date"},
        {"field": "note", "type": "text"},
    ],
}


def main():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    valid = [
        {
            "version": "1.0.0",
            "operation": "describe",
            "request_id": "describe_1",
            "view_id": 7,
            "container_id": "feedback",
        },
        {
            "version": "1.0.0",
            "operation": "evaluate",
            "request_id": "evaluate_1",
            "view_id": 7,
            "container_id": "feedback",
            "binding_etag": ETAG,
            "inputs": [
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": ""},
            ],
        },
        {
            "version": "1.0.0",
            "request_id": "describe_1",
            "status": "described",
            "binding": BINDING,
        },
        {
            "version": "1.0.0",
            "request_id": "evaluate_1",
            "status": "ready",
            "binding_etag": ETAG,
            "container_id": "feedback",
            "result": {"content": "建议补充办理说明", "visible": True},
        },
        {
            "version": "1.0.0",
            "operation": "evaluate",
            "request_id": "evaluate_relation",
            "view_id": 7,
            "container_id": "refund-feedback",
            "binding_etag": ETAG,
            "inputs": [
                {"field": "partner_id", "present": True, "value": True},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": ""},
            ],
        },
        {
            "version": "1.0.0",
            "request_id": "describe_relation",
            "status": "described",
            "binding": RELATION_BINDING,
        },
        {
            "version": "1.0.0",
            "request_id": "evaluate_1",
            "status": "failed",
            "diagnostic": {"code": "FEEDBACK_INPUT_INVALID", "path": "feedback_evaluation.inputs"},
        },
    ]
    for index, payload in enumerate(valid):
        errors = list(validator.iter_errors(payload))
        assert not errors, f"valid case {index} rejected: {errors[0].message}"

    invalid = [
        {**valid[0], "extra": True},
        {
            **valid[3],
            "result": {"content": "must be cleared", "visible": False},
        },
        {
            **valid[3],
            "result": {"content": "", "visible": True},
        },
        {
            **valid[1],
            "inputs": [
                {"field": "business_date", "present": False, "value": False},
                {"field": "note", "present": True, "value": ""},
            ],
        },
        {
            **valid[4],
            "inputs": [
                {"field": "partner_id", "present": True, "value": 42},
                {"field": "business_date", "present": True, "value": False},
                {"field": "note", "present": True, "value": ""},
            ],
        },
        {
            **valid[5],
            "binding": {
                **RELATION_BINDING,
                "dependencies": [
                    {"field": "partner_id", "type": "many2many_presence"},
                    *RELATION_BINDING["dependencies"][1:],
                ],
            },
        },
    ]
    for index, payload in enumerate(invalid):
        assert list(validator.iter_errors(payload)), f"invalid case {index} accepted"
    for status in (400, 403, 409, 422, 500):
        assert result_http_status({"ok": False, "code": status}) == status
    print("onchange_feedback_evaluation_schema: PASS")


if __name__ == "__main__":
    main()
