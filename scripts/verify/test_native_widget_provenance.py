from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADDON_ROOT = ROOT / "addons/smart_core"
if str(ADDON_ROOT) not in sys.path:
    sys.path.insert(0, str(ADDON_ROOT))

from core.contract_runtime import semantic_resolver  # noqa: E402
from core.native_widget_profile import (  # noqa: E402
    WIDGET_SOURCE_COMPATIBILITY,
    WIDGET_SOURCE_MODEL_DERIVED,
    WIDGET_SOURCE_NATIVE_EXPLICIT,
    build_widget_provenance,
    resolve_widget_contract,
    widget_source_and_value,
)


class NativeWidgetProvenanceTest(unittest.TestCase):
    def test_bare_widget_metadata_never_becomes_native_fact(self):
        source, native, declared = widget_source_and_value({
            "widget": "input",
            "widget_source": WIDGET_SOURCE_MODEL_DERIVED,
        })
        self.assertEqual(source, WIDGET_SOURCE_MODEL_DERIVED)
        self.assertEqual(native, "")
        self.assertEqual(declared, "input")

        provenance = build_widget_provenance({
            "widget": "input",
            "widget_source": WIDGET_SOURCE_MODEL_DERIVED,
        }, resolved_widget_type="input")
        self.assertEqual(provenance["widgetSource"], WIDGET_SOURCE_MODEL_DERIVED)
        self.assertEqual(provenance["nativeWidget"], "")
        self.assertEqual(provenance["resolutionStatus"], "not_applicable")

    def test_unmarked_widget_is_compatibility_not_native(self):
        provenance = build_widget_provenance({"widget": "daterange"}, resolved_widget_type="date")
        self.assertEqual(provenance["widgetSource"], WIDGET_SOURCE_COMPATIBILITY)
        self.assertEqual(provenance["nativeWidget"], "")

    def test_explicit_supported_widget_preserves_native_identity(self):
        field = {
            "widget": "daterange",
            "widget_source": WIDGET_SOURCE_NATIVE_EXPLICIT,
            "type": "date",
        }
        resolution = resolve_widget_contract(
            field,
            resolved_widget_type="date",
            semantic_widget_type=semantic_resolver.semantic_widget_type("daterange", "date"),
        )
        self.assertEqual(resolution["provenance"]["nativeWidget"], "daterange")
        self.assertEqual(resolution["provenance"]["widgetSource"], WIDGET_SOURCE_NATIVE_EXPLICIT)
        self.assertEqual(resolution["provenance"]["resolutionStatus"], "ready")
        self.assertEqual(resolution["componentKey"], "sc.input.date")

    def test_unknown_explicit_widget_fails_closed(self):
        field = {
            "widget": "future_editor",
            "widget_source": WIDGET_SOURCE_NATIVE_EXPLICIT,
            "type": "char",
        }
        resolution = resolve_widget_contract(
            field,
            resolved_widget_type="input",
            semantic_widget_type="input",
        )
        self.assertEqual(resolution["provenance"]["widgetSource"], WIDGET_SOURCE_NATIVE_EXPLICIT)
        self.assertEqual(resolution["provenance"]["resolutionStatus"], "unsupported")
        self.assertEqual(resolution["provenance"]["reasonCode"], "NATIVE_WIDGET_UNRECOGNIZED")
        self.assertEqual(resolution["semantic"], "unsupported_native_widget")
        self.assertEqual(resolution["componentKey"], "sc.unsupported.native_widget")

    def test_declared_unsupported_widget_uses_fail_closed_path(self):
        for widget, reason in (
            ("domain", "NATIVE_WIDGET_DOMAIN_EDITOR_UNSUPPORTED"),
            ("tier_validation", "NATIVE_WIDGET_QWEB_RENDERER_UNSUPPORTED"),
        ):
            with self.subTest(widget=widget):
                resolution = resolve_widget_contract(
                    {
                        "widget": widget,
                        "widget_source": WIDGET_SOURCE_NATIVE_EXPLICIT,
                        "type": "char",
                    },
                    resolved_widget_type="input",
                    semantic_widget_type="input",
                )
                self.assertEqual(resolution["provenance"]["resolutionStatus"], "unsupported")
                self.assertEqual(resolution["provenance"]["reasonCode"], reason)
                self.assertEqual(resolution["componentKey"], "sc.unsupported.native_widget")

    def test_fallback_widget_is_explicit_but_not_fail_closed(self):
        resolution = resolve_widget_contract(
            {
                "widget": "handle",
                "widget_source": WIDGET_SOURCE_NATIVE_EXPLICIT,
                "type": "integer",
            },
            resolved_widget_type="number",
            semantic_widget_type="number",
        )
        self.assertEqual(resolution["provenance"]["resolutionStatus"], "fallback")
        self.assertEqual(
            resolution["provenance"]["reasonCode"],
            "NATIVE_WIDGET_GENERIC_VISUAL_FALLBACK",
        )
        self.assertNotEqual(resolution["componentKey"], "sc.unsupported.native_widget")

    def test_common_base_odoo_field_widgets_use_registered_generic_controls(self):
        for widget, field_type, resolved_type, component in (
            ("boolean_favorite", "boolean", "boolean", "sc.input.boolean"),
            ("text", "char", "input", "sc.input.text"),
        ):
            with self.subTest(widget=widget):
                resolution = resolve_widget_contract(
                    {
                        "widget": widget,
                        "widget_source": WIDGET_SOURCE_NATIVE_EXPLICIT,
                        "type": field_type,
                    },
                    resolved_widget_type=resolved_type,
                    semantic_widget_type=resolved_type,
                )
                self.assertEqual(resolution["provenance"]["resolutionStatus"], "ready")
                self.assertEqual(resolution["componentKey"], component)

    def test_every_observed_repository_widget_has_a_declared_status(self):
        inventory = json.loads(
            (ROOT / "docs/audit/native-scene-01/inventories/native_view_inventory.json").read_text(
                encoding="utf-8"
            )
        )
        observed = inventory["summary"]["unique_widgets"]
        missing = [widget for widget in observed if widget not in semantic_resolver.NATIVE_WIDGET_STATUS]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
