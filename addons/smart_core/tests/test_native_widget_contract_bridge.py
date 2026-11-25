# -*- coding: utf-8 -*-
"""P0 bridge tests: parsed native widget -> platform contract meaning."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ADDON_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADDON_ROOT))

from core.contract_runtime.native_widget_contract import (  # noqa: E402
    project_native_embedded_widget_contract,
    project_native_field_widget_contract,
)


class NativeWidgetContractBridgeTest(unittest.TestCase):
    def test_daterange_preserves_native_expression_and_projects_date_semantics(self) -> None:
        projection = project_native_field_widget_contract(
            field_type="date",
            native_widget_type="daterange",
            fallback_widget_type="display",
            legacy_descriptor={"type": "date"},
        )
        self.assertEqual(projection["widgetType"], "daterange")
        self.assertEqual(projection["nativeWidgetType"], "daterange")
        self.assertEqual(projection["canonicalWidgetType"], "date")
        self.assertEqual(projection["semanticType"], "date")
        self.assertEqual(projection["componentKey"], "sc.input.date")

    def test_fixed_field_semantics_cannot_be_downgraded_by_native_display(self) -> None:
        for field_type, semantic, component_key in (
            ("date", "date", "sc.input.date"),
            ("datetime", "datetime", "sc.input.datetime"),
            ("monetary", "money", "sc.value.money"),
            ("boolean", "boolean", "sc.input.boolean"),
        ):
            with self.subTest(field_type=field_type):
                projection = project_native_field_widget_contract(
                    field_type=field_type,
                    native_widget_type="display",
                    legacy_descriptor={"type": field_type},
                )
                self.assertEqual(projection["widgetType"], "display")
                self.assertEqual(projection["semanticType"], semantic)
                self.assertEqual(projection["componentKey"], component_key)

    def test_explicit_native_widget_rules_keep_their_declared_meaning(self) -> None:
        status = project_native_field_widget_contract(
            field_type="selection",
            native_widget_type="statusbar",
            legacy_descriptor={"type": "selection"},
        )
        self.assertEqual(status["semanticType"], "status")
        self.assertEqual(status["componentKey"], "sc.display.status")

        activity = project_native_field_widget_contract(
            field_type="one2many",
            native_widget_type="list_activity",
            legacy_descriptor={"type": "one2many"},
        )
        self.assertEqual(activity["semanticType"], "activity_collection")
        self.assertEqual(activity["componentKey"], "sc.relation.activity")

    def test_presentation_variant_uses_canonical_control_when_no_rule_matches(self) -> None:
        phone = project_native_field_widget_contract(
            field_type="char",
            native_widget_type="phone",
            legacy_descriptor={"type": "char"},
        )
        self.assertEqual(phone["widgetType"], "phone")
        self.assertEqual(phone["canonicalWidgetType"], "input")
        self.assertEqual(phone["semanticType"], "text")
        self.assertEqual(phone["componentKey"], "sc.input.text")

    def test_declared_semantic_is_consumed_for_non_fixed_field_types(self) -> None:
        projection = project_native_field_widget_contract(
            field_type="float",
            native_widget_type="number",
            declared_semantic="percentage",
            legacy_descriptor={"type": "float"},
        )
        self.assertEqual(projection["widgetType"], "number")
        self.assertEqual(projection["semanticType"], "percentage")
        self.assertEqual(projection["componentKey"], "sc.value.percentage")

    def test_embedded_widget_node_uses_the_same_contract_bridge(self) -> None:
        ribbon = project_native_embedded_widget_contract("web_ribbon")
        self.assertEqual(ribbon["nativeWidget"], "web_ribbon")
        self.assertEqual(ribbon["widgetStatus"], "ready")
        self.assertEqual(ribbon["componentKey"], "sc.display.ribbon")
        self.assertFalse(ribbon["payloadRequired"])
        self.assertEqual(ribbon["payloadSchema"], "")

        insight = project_native_embedded_widget_contract("sc_insight_banner")
        self.assertEqual(insight["widgetStatus"], "ready")
        self.assertEqual(insight["componentKey"], "sc.insight.summary")
        self.assertTrue(insight["payloadRequired"])
        self.assertEqual(insight["payloadSchema"], "insight_summary.v1")

        actions = project_native_embedded_widget_contract("sc_next_actions")
        self.assertTrue(actions["payloadRequired"])
        self.assertEqual(actions["payloadSchema"], "action_list.v1")

        unsupported = project_native_embedded_widget_contract("unknown_embedded_widget")
        self.assertEqual(unsupported["widgetStatus"], "unsupported")
        self.assertEqual(unsupported["componentKey"], "sc.unsupported.native_node")
        self.assertEqual(unsupported["reasonCode"], "NATIVE_VIEW_WIDGET_UNSUPPORTED")
        self.assertFalse(unsupported["payloadRequired"])
        self.assertEqual(unsupported["payloadSchema"], "")


if __name__ == "__main__":
    unittest.main()
