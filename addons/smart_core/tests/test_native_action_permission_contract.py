# -*- coding: utf-8 -*-
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..core.native_action_permission import (
    apply_native_action_permission_verdicts,
    button_access_mode,
)


class _Record:
    def __init__(self, *, exists=True, denied=False):
        self._exists = exists
        self._denied = denied

    def exists(self):
        return self if self._exists else False

    def check_access_rule(self, operation):
        if self._denied:
            raise AccessError("denied")


class _Model:
    _sc_readonly_navigation_button_methods = {"action_open_source"}

    def __init__(self, rights, record=None):
        self._rights = rights
        self._record = record or _Record()

    def action_open_source(self):
        return True

    def action_confirm(self):
        return True

    def check_access_rights(self, operation, raise_exception=False):
        return bool(self._rights.get(operation))

    def browse(self, record_id):
        return self._record


def _contract(button_type, name, *, action_key="test"):
    return {
        "actionContract": {
            "actionRuleList": [{
                "actionKey": action_key,
                "backendIdentity": "native:%s:%s" % (button_type, name),
                "button": {"type": button_type, "name": name},
            }],
        },
        "statusContract": {
            "buttonStatus": [{
                "btnId": "btn.%s" % action_key,
                "visible": True,
                "disabled": False,
            }],
        },
    }


@tagged("post_install", "-at_install", "native_action_permission_contract")
class TestNativeActionPermissionContract(TransactionCase):
    def _apply(self, model, contract, record_id=0):
        apply_native_action_permission_verdicts(
            {"record.model": model},
            contract,
            model="record.model",
            record_id=record_id,
        )
        return (
            contract["actionContract"]["actionRuleList"][0],
            contract["statusContract"]["buttonStatus"][0],
        )

    def test_readonly_navigation_uses_read_authority(self):
        model = _Model({"read": True, "write": False})
        self.assertEqual(button_access_mode(model, "action_open_source"), "read")
        row, status = self._apply(
            model,
            _contract("object", "action_open_source"),
        )
        self.assertTrue(row["entitlementEvaluated"])
        self.assertTrue(row["authorizationAllowed"])
        self.assertTrue(row["allowed"])
        self.assertTrue(row["enabled"])
        self.assertFalse(row["disabled"])
        self.assertFalse(status["disabled"])

    def test_write_button_denial_is_published_with_reason(self):
        row, status = self._apply(
            _Model({"read": True, "write": False}),
            _contract("object", "action_confirm"),
        )
        self.assertTrue(row["entitlementEvaluated"])
        self.assertFalse(row["authorizationAllowed"])
        self.assertFalse(row["allowed"])
        self.assertFalse(row["enabled"])
        self.assertTrue(row["disabled"])
        self.assertEqual(row["reasonCode"], "ACTION_PERMISSION_DENIED")
        self.assertFalse(status["visible"])
        self.assertTrue(status["disabled"])
        self.assertEqual(status["reasonCode"], "ACTION_PERMISSION_DENIED")

    def test_record_rule_denial_overrides_model_permission(self):
        model = _Model(
            {"read": True, "write": True},
            record=_Record(denied=True),
        )
        row, _status = self._apply(
            model,
            _contract("object", "action_confirm"),
            record_id=91,
        )
        self.assertFalse(row["authorizationAllowed"])
        self.assertEqual(row["reasonCode"], "ACTION_RECORD_PERMISSION_DENIED")

    def test_explicit_business_verdict_is_not_overwritten(self):
        contract = _contract("object", "action_confirm")
        row = contract["actionContract"]["actionRuleList"][0]
        row.update(
            entitlementEvaluated=True,
            authorizationAllowed=True,
            businessAvailable=False,
            allowed=True,
            enabled=False,
            disabled=True,
            reasonCode="BUSINESS_STATE_BLOCKED",
        )
        settled, _status = self._apply(
            _Model({"read": True, "write": True}),
            contract,
        )
        self.assertFalse(settled["businessAvailable"])
        self.assertFalse(settled["enabled"])
        self.assertEqual(settled["reasonCode"], "BUSINESS_STATE_BLOCKED")

    def test_action_button_uses_read_authority(self):
        row, _status = self._apply(
            _Model({"read": True, "write": False}),
            _contract("action", "123"),
        )
        self.assertTrue(row["authorizationAllowed"])
        self.assertTrue(row["enabled"])

    def test_missing_object_method_fails_closed(self):
        row, status = self._apply(
            _Model({"read": True, "write": True}),
            _contract("object", "missing_method"),
        )
        self.assertFalse(row["authorizationAllowed"])
        self.assertEqual(row["reasonCode"], "ACTION_METHOD_NOT_CALLABLE")
        self.assertEqual(status["reasonCode"], "ACTION_METHOD_NOT_CALLABLE")
