"""Focused self-test for the declared-action authority audit dimension.

The audit must expose a declared native form action whose projection published
no consumable authority verdict, because the consumer's declared-consistency
gate can only drop such an action.  Each case first proves the baseline is
clean, then injects one defect and proves it is detected, so a silently
disabled check cannot pass as a clean audit.
"""
from __future__ import annotations

import unittest

from scripts.verify.form_structure_contract_runtime_audit import (
    declared_action_authority_issues,
)

IDENTITY = "native_button:object:action_sc_submit:/form[1]/sheet[1]/div[1]/button[5]:1"
ISSUE_MISSING = f"declared_action_verdict_missing:{IDENTITY}"
ISSUE_INCOMPLETE = f"declared_action_verdict_incomplete:{IDENTITY}"


def _row(**overrides):
    row = {
        "actionId": "action.action_sc_submit",
        "actionKey": "action_sc_submit",
        "backendIdentity": IDENTITY,
        "sourceChannel": "native_form_layout_button",
        "nativeIdentity": {
            "authoritative": True,
            "canonical_region": "layout",
            "projection_region": "layout",
            "native_locator": "/form[1]/sheet[1]/div[1]/button[5]",
            "occurrence_index": 1,
        },
        "allowed": True,
        "enabled": True,
        "disabled": False,
        "entitlementEvaluated": True,
        "authorizationAllowed": True,
    }
    row.update(overrides)
    return row


def _contract(row):
    return {"actionContract": {"actionRuleList": [row]}}


class DeclaredActionAuthorityAuditTest(unittest.TestCase):
    def test_declared_native_action_with_published_verdict_is_clean(self):
        self.assertEqual(declared_action_authority_issues(_contract(_row())), [])

    def test_missing_entitlement_evaluation_is_detected(self):
        row = _row()
        row.pop("entitlementEvaluated")
        self.assertEqual(declared_action_authority_issues(_contract(row)), [ISSUE_MISSING])

    def test_incomplete_boolean_verdict_is_detected(self):
        row = _row(allowed=None)
        self.assertEqual(declared_action_authority_issues(_contract(row)), [ISSUE_INCOMPLETE])

    def test_state_hidden_action_still_owes_its_verdict(self):
        # A state-derived hide is not a permission denial, so the row keeps the
        # verdict; only a published row can be re-evaluated against live values.
        row = _row(visible={"attrs": {"invisible": {"kind": "static", "value": True}}})
        self.assertEqual(declared_action_authority_issues(_contract(row)), [])

    def test_non_authoritative_and_other_channels_are_out_of_scope(self):
        non_authoritative = _row(nativeIdentity={"authoritative": False, "native_locator": "/form[1]/sheet[1]/button[1]"})
        non_authoritative.pop("entitlementEvaluated")
        header_channel = _row(sourceChannel="native_form_header")
        header_channel.pop("entitlementEvaluated")
        self.assertEqual(declared_action_authority_issues(_contract(non_authoritative)), [])
        self.assertEqual(declared_action_authority_issues(_contract(header_channel)), [])
        self.assertEqual(declared_action_authority_issues({}), [])


if __name__ == "__main__":
    unittest.main()
