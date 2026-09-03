import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify.frontend_boq_import_preview_guard import validate

ROOT = Path(__file__).resolve().parents[2]


class BoqImportPreviewGuardTest(unittest.TestCase):
    def test_repository_contract_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_intent_marker_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "boqImportPreview.ts" and path.parent.name == "api":
                return value.replace(
                    "BOQ_IMPORT_PREVIEW_FETCH_INTENT = 'project.boq.import.preview.fetch'",
                    "BOQ_IMPORT_PREVIEW_FETCH_INTENT = 'renamed.intent'",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(
                any(
                    "boq import preview api missing BOQ_IMPORT_PREVIEW_FETCH_INTENT" in item
                    for item in validate()
                )
            )

    def test_model_impurity_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "boqImportPreview.ts" and path.parent.name == "presentation":
                return value.replace(
                    "export function projectBoqImportPreview(",
                    "export async function projectBoqImportPreview(\n  await fetch('/x'),",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(
                any(
                    "boq import preview model must stay pure: found fetch(" in item
                    for item in validate()
                )
            )

    def test_component_write_operation_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "BoqImportPreviewPanel.vue":
                return value.replace(
                    "data-boq-import-preview",
                    "data-boq-import-preview @click=\"doImport()\"",
                    1,
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(
                any(
                    "BoqImportPreviewPanel is readonly projection: found @click" in item
                    for item in validate()
                )
            )

    def test_missing_empty_state_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "BoqImportPreviewPanel.vue":
                return value.replace(
                    "v-else-if=\"model.viewState === 'missing_payload' || model.viewState === 'degraded_shape'\"",
                    "v-else-if=\"model.viewState === 'degraded_shape_only_marker'\"",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(
                any(
                    "BoqImportPreviewPanel must render missing_payload empty state" in item
                    for item in validate()
                )
            )

    def test_makefile_registration_required(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "frontend.mk":
                return value.replace(
                    "verify.frontend.boq_import_preview.unit",
                    "verify.frontend.boq_import_preview.removed",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertIn(
                "make/frontend.mk does not register verify.frontend.boq_import_preview.unit",
                validate(),
            )

    def test_generic_data_op_bypass_fails(self):
        real = Path.read_text

        def altered(path, *args, **kwargs):
            value = real(path, *args, **kwargs)
            if path.name == "boqImportPreview.ts" and path.parent.name == "api":
                return value.replace(
                    "export async function fetchBoqImportPreview",
                    "const bypass = { op: 'list' };\n\nexport async function fetchBoqImportPreview",
                )
            return value

        with patch("pathlib.Path.read_text", altered):
            self.assertTrue(
                any(
                    "must not use generic data op: op: 'list'" in item
                    for item in validate()
                )
            )


if __name__ == "__main__":
    unittest.main()
