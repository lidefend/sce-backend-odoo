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
    ASSEMBLER_SOURCE_PATH,
    NOTEBOOK_PROJECTION_CARRIERS,
    declared_action_authority_issues,
    is_unlabeled_group,
    resolve_projection_carriers,
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


class GroupSemanticHeadingAuditTest(unittest.TestCase):
    """The heading metric must read authored headings, not identity values.

    Every case proves the baseline verdict first and then injects the one
    condition it claims to detect.
    """

    def test_an_authored_native_title_counts_as_labeled(self):
        node = {"containerType": "group", "containerId": "group_basic_info", "title": "基本信息"}
        self.assertFalse(is_unlabeled_group(node))
        node["title"] = "group"
        self.assertTrue(is_unlabeled_group(node), "a container type echoed as a title is not a heading")
        node["title"] = "group_basic_info"
        self.assertTrue(is_unlabeled_group(node), "a technical container id echoed as a title is not a heading")

    def test_a_missing_sibling_label_must_not_mark_every_group_unlabeled(self):
        node = {"containerType": "group", "containerId": "group_basic_info", "label": "基本信息"}
        self.assertFalse(is_unlabeled_group(node))
        node.pop("label")
        self.assertTrue(is_unlabeled_group(node))

    def test_the_contract_semantic_title_satisfies_the_heading_channel(self):
        node = {"containerType": "group", "containerId": "main.info", "semanticTitle": "金额信息"}
        self.assertFalse(is_unlabeled_group(node))
        node.pop("semanticTitle")
        self.assertTrue(is_unlabeled_group(node))

    def test_a_group_with_no_label_at_all_is_unlabeled(self):
        self.assertTrue(is_unlabeled_group({"containerType": "group", "containerId": "top.wrapper"}))


class NotebookProjectionCarrierTest(unittest.TestCase):
    """A metric may only filter on a carrier the producer can really stamp."""

    def test_declared_carrier_is_accepted_when_the_producer_stamps_it(self):
        source = 'x = {"sourceAuthority": {"runtime_carrier": "carrier_x"}}'
        self.assertEqual(resolve_projection_carriers(("carrier_x",), source), ("carrier_x",))

    def test_invented_carrier_is_rejected_instead_of_reporting_a_zero(self):
        source = 'x = {"sourceAuthority": {"runtime_carrier": "carrier_x"}}'
        with self.assertRaises(RuntimeError):
            resolve_projection_carriers(("business_form_default_tab_standardizer",), source)

    def test_declared_notebook_carriers_exist_in_the_producer_source(self):
        source = ASSEMBLER_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            resolve_projection_carriers(NOTEBOOK_PROJECTION_CARRIERS, source),
            NOTEBOOK_PROJECTION_CARRIERS,
        )


if __name__ == "__main__":
    unittest.main()
