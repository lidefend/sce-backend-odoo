from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "addons/smart_core/core/native_view_occurrence.py"
SCHEMA_PATH = ROOT / "docs/architecture/unified_page_contract_v2/unified_page_contract_v2.schema.json"
SPEC = importlib.util.spec_from_file_location("native_view_occurrence", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def view_identity(arch='<form><group name="main"><field name="amount" string="Amount"/></group></form>'):
    return MODULE.build_native_view_identity(
        model="payment.request",
        view_type="form",
        view_id=71,
        view_xmlid="demo.payment_request_form",
        arch=arch,
    )


class NativeViewOccurrenceIdentityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.schema_defs = schema["$defs"]

    def _validate_definition(self, definition, value):
        validator = Draft202012Validator({
            "$ref": f"#/$defs/{definition}",
            "$defs": self.schema_defs,
        })
        self.assertEqual(list(validator.iter_errors(value)), [])

    def test_display_copy_changes_content_hash_but_not_structure_or_occurrence(self):
        first = view_identity()
        second = view_identity(
            '<form><group name="main"><field name="amount" string="申请金额"/></group></form>'
        )

        self.assertNotEqual(first["viewContentHash"], second["viewContentHash"])
        self.assertEqual(first["viewStructureKey"], second["viewStructureKey"])
        self.assertEqual(
            MODULE.build_native_occurrence_identity(
                first, kind="field", name="amount",
                native_locator="/form[1]/group[1]/field[1]", occurrence_index=1,
            )["occurrenceKey"],
            MODULE.build_native_occurrence_identity(
                second, kind="field", name="amount",
                native_locator="/form[1]/group[1]/field[1]", occurrence_index=1,
            )["occurrenceKey"],
        )

    def test_structural_change_changes_structure_key(self):
        first = view_identity()
        second = view_identity(
            '<form><group name="main"><field name="partner_id"/>'
            '<field name="amount"/></group></form>'
        )

        self.assertNotEqual(first["viewStructureKey"], second["viewStructureKey"])

    def test_duplicate_same_name_occurrences_remain_distinct(self):
        identity = view_identity(
            '<form><group name="a"><field name="amount"/></group>'
            '<group name="b"><field name="amount"/></group></form>'
        )
        first = MODULE.build_native_occurrence_identity(
            identity, kind="field", name="amount",
            native_locator="/form[1]/group[1]/field[1]", occurrence_index=1,
        )
        second = MODULE.build_native_occurrence_identity(
            identity, kind="field", name="amount",
            native_locator="/form[1]/group[2]/field[1]", occurrence_index=2,
        )

        self.assertNotEqual(first["occurrenceKey"], second["occurrenceKey"])

    def test_source_position_is_evidence_not_identity(self):
        identity = view_identity()
        first = MODULE.build_native_occurrence_identity(
            identity, kind="field", name="amount",
            native_locator="/form[1]/group[1]/field[1]", occurrence_index=1,
            source_position=0,
        )
        second = MODULE.build_native_occurrence_identity(
            identity, kind="field", name="amount",
            native_locator="/form[1]/group[1]/field[1]", occurrence_index=1,
            source_position=9,
        )

        self.assertEqual(first["occurrenceKey"], second["occurrenceKey"])

    def test_xmlid_is_required_for_cross_environment_stability(self):
        stable = view_identity()
        unstable = MODULE.build_native_view_identity(
            model="payment.request",
            view_type="form",
            view_id=71,
            arch='<form><field name="amount"/></form>',
        )

        self.assertTrue(stable["crossEnvironmentStable"])
        self.assertFalse(unstable["crossEnvironmentStable"])

    def test_content_hash_excludes_runtime_view_id(self):
        first = MODULE.build_native_view_identity(
            model="payment.request",
            view_type="form",
            view_id=71,
            view_xmlid="demo.payment_request_form",
            arch='<form><field name="amount"/></form>',
        )
        second = MODULE.build_native_view_identity(
            model="payment.request",
            view_type="form",
            view_id=9071,
            view_xmlid="demo.payment_request_form",
            arch='<form><field name="amount"/></form>',
        )

        self.assertEqual(first["viewContentHash"], second["viewContentHash"])
        self.assertEqual(first["viewStructureKey"], second["viewStructureKey"])
        self.assertNotEqual(first["viewId"], second["viewId"])

    def test_native_behavior_is_preserved_as_non_identity_evidence(self):
        identity = view_identity()
        first = MODULE.build_native_occurrence_identity(
            identity,
            kind="field",
            name="amount",
            native_locator="/form[1]/group[1]/field[1]",
            occurrence_index=1,
            native_attributes={
                "domain": "[('state', '=', 'draft')]",
                "context": "{'default_company_id': 1}",
                "options": "{'no_open': True}",
            },
        )
        second = MODULE.build_native_occurrence_identity(
            identity,
            kind="field",
            name="amount",
            native_locator="/form[1]/group[1]/field[1]",
            occurrence_index=1,
            native_attributes={
                "domain": "[('state', '=', 'open')]",
                "context": "{'default_company_id': 2}",
                "options": "{'no_create': True}",
            },
        )

        self.assertEqual(first["occurrenceKey"], second["occurrenceKey"])
        self.assertNotEqual(first["nativeBehavior"], second["nativeBehavior"])
        self.assertEqual(first["sourceAuthority"]["kind"], "ir.ui.view")

    def test_embedded_widget_occurrence_is_distinct_and_display_copy_neutral(self):
        first_view = view_identity(
            '<form><widget name="web_ribbon" title="Draft"/>'
            '<widget name="web_ribbon" title="Draft"/></form>'
        )
        second_view = view_identity(
            '<form><widget name="web_ribbon" title="Paid"/>'
            '<widget name="web_ribbon" title="Paid"/></form>'
        )
        first = MODULE.build_native_occurrence_identity(
            first_view,
            kind="widget",
            name="web_ribbon",
            native_locator="/form[1]/widget[1]",
            occurrence_index=1,
            source_position=1,
            native_attributes={"options": "{'bg_color': 'text-bg-success'}"},
        )
        second = MODULE.build_native_occurrence_identity(
            first_view,
            kind="widget",
            name="web_ribbon",
            native_locator="/form[1]/widget[2]",
            occurrence_index=2,
            source_position=2,
        )
        renamed = MODULE.build_native_occurrence_identity(
            second_view,
            kind="widget",
            name="web_ribbon",
            native_locator="/form[1]/widget[1]",
            occurrence_index=1,
            source_position=1,
            native_attributes={"options": "{'bg_color': 'text-bg-success'}"},
        )

        self.assertEqual(first["kind"], "widget")
        self.assertNotEqual(first["occurrenceKey"], second["occurrenceKey"])
        self.assertEqual(first["occurrenceKey"], renamed["occurrenceKey"])
        self._validate_definition("nativeOccurrenceIdentity", first)

    def test_published_occurrence_shape_matches_strict_schema(self):
        identity = view_identity()
        occurrence = MODULE.build_native_occurrence_identity(
            identity,
            kind="field",
            name="amount",
            native_locator="/form[1]/group[1]/field[1]",
            occurrence_index=1,
            source_position=0,
            native_attributes={
                "domain": "[('state', '=', 'draft')]",
                "context": "{'default_company_id': 1}",
                "options": "{'no_open': True}",
            },
        )
        self._validate_definition("nativeOccurrenceIdentity", occurrence)
        self._validate_definition("listColumnOccurrence", {
            "occurrenceKey": occurrence["occurrenceKey"],
            "fieldCode": "amount",
            "nativeIdentity": {**occurrence, "kind": "column"},
            "label": "Amount",
            "widget": "",
            "optional": "",
            "sum": "",
            "modifiers": {},
            "domainRaw": occurrence["nativeBehavior"]["domainRaw"],
            "contextRaw": occurrence["nativeBehavior"]["contextRaw"],
            "optionsRaw": occurrence["nativeBehavior"]["optionsRaw"],
        })

        broken = dict(occurrence)
        broken.pop("occurrenceKey")
        validator = Draft202012Validator({
            "$ref": "#/$defs/nativeOccurrenceIdentity",
            "$defs": self.schema_defs,
        })
        self.assertNotEqual(list(validator.iter_errors(broken)), [])

    def test_incomplete_native_identity_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            MODULE.build_native_occurrence_identity(
                {"model": "payment.request"},
                kind="field",
                name="amount",
                native_locator="/form[1]/field[1]",
                occurrence_index=1,
            )


if __name__ == "__main__":
    unittest.main()
