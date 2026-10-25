import unittest

from scripts.verify import contract_assertion_validator as validator


def expectation(**overrides):
    payload = {
        "schema": "contract-assertion-expectation/v1",
        "config": {"model": "payment.request",
                   "action_xmlid": "smart_construction_core.action_payment_request_pay",
                   "role_xmlid": "smart_construction_demo.user_demo_role_finance"},
        "expect": {
            "fields": {
                "amount": {"type": "monetary", "readonly": True, "required": False, "visible": True},
                "state": {"type": "selection", "readonly": True, "visible": True},
            },
            "readable_fields": ["amount", "state"],
            "executable_actions": ["smart_construction_core.action_payment_request_pay"],
        },
    }
    payload.update(overrides)
    return payload


def contract(fields=None):
    nodes = [{
        "name": name,
        "widgetId": f"widget-{name}",
        "fieldInfo": {"type": spec.get("type", ""), "readonly": spec.get("readonly"),
                      "required": spec.get("required"), "visible": spec.get("visible")},
    } for name, spec in (fields or {}).items()]
    return {"dataContract": {"mainData": {name: spec.get("value") for name, spec in (fields or {}).items()}},
            "statusContract": {"widgetStatus": [
                {"widgetId": f"widget-{name}", "readonly": spec.get("readonly"),
                 "required": spec.get("required"), "visible": spec.get("visible")}
                for name, spec in (fields or {}).items()
            ]},
            "layout": {"nodes": nodes}}


class ContractAssertionValidatorTest(unittest.TestCase):
    def test_expectation_schema_rejects_invalid_input(self):
        validator.validate_expectation(expectation())
        for bad in ({}, {"schema": "other"}, {"schema": "contract-assertion-expectation/v1"},
                    {"schema": "contract-assertion-expectation/v1", "config": {}},
                    {"schema": "contract-assertion-expectation/v1", "config": {"model": "x"}, "expect": {"fields": {}}}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    validator.validate_expectation(bad)

    def test_field_semantics_extracts_declared_semantics(self):
        semantics = validator.field_semantics(contract({
            "amount": {"type": "monetary", "readonly": True, "required": False, "visible": True},
        }))
        self.assertEqual({"amount": {"type": "monetary", "readonly": True,
                                     "required": False, "visible": True}}, semantics)

    def test_validate_passes_when_contract_matches_declaration(self):
        result = validator.validate(expectation(), contract({
            "amount": {"type": "monetary", "readonly": True, "required": False, "visible": True},
            "state": {"type": "selection", "readonly": True, "required": None, "visible": True},
        }))
        self.assertEqual("passed", result["status"])
        self.assertEqual([], result["failed"])

    def test_validate_fails_on_semantic_drift(self):
        result = validator.validate(expectation(), contract({
            "amount": {"type": "monetary", "readonly": False, "required": False, "visible": True},
            "state": {"type": "selection", "readonly": True, "required": None, "visible": True},
        }))
        self.assertEqual("failed", result["status"])
        self.assertEqual(["field:amount.readonly"], [row["id"] for row in result["failed"]])

    def test_validate_fails_when_field_is_missing(self):
        result = validator.validate(expectation(), contract({
            "state": {"type": "selection", "readonly": True, "required": None, "visible": True},
        }))
        self.assertEqual("failed", result["status"])
        self.assertEqual(["field:amount"], [row["id"] for row in result["failed"]])


if __name__ == "__main__":
    unittest.main()
