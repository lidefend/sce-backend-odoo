from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.verify.frontend_primitive_adapter_guard import PRIMITIVES, validate


class PrimitiveAdapterGuardTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        design = root / "frontend/apps/web/src/components/design-system"
        design.mkdir(parents=True)
        ui = root / "frontend/packages/ui/src"
        ui.mkdir(parents=True)
        theme = ui / "kits/tdesign/theme.css"
        theme.parent.mkdir(parents=True)
        (design / "index.ts").write_text(
            "\n".join(f"export {{ default as {name} }} from './{name}.vue';" for name in PRIMITIVES),
            encoding="utf-8",
        )
        (design / "tdesignPrimitiveBridge.ts").write_text(
            "export { TDesignAlert, TDesignButton, TDesignCheckbox, TDesignRadioGroup, TDesignRadio, TDesignDialog, TDesignDrawer, TDesignEmpty, TDesignInput, TDesignSelect, TDesignTextarea } from '@sc/ui/primitives';\n", encoding="utf-8"
        )
        (ui / "primitives.ts").write_text(
            "export { Alert as TDesignAlert } from 'tdesign-vue-next/es/alert';\n"
            "export { Button as TDesignButton } from 'tdesign-vue-next/es/button';\n"
            "export { Checkbox as TDesignCheckbox } from 'tdesign-vue-next/es/checkbox';\n"
            "export { RadioGroup as TDesignRadioGroup } from 'tdesign-vue-next/es/radio';\n"
            "export { Radio as TDesignRadio } from 'tdesign-vue-next/es/radio';\n"
            "export { Input as TDesignInput } from 'tdesign-vue-next/es/input';\n"
            "export { Select as TDesignSelect } from 'tdesign-vue-next/es/select';\n"
            "export { Textarea as TDesignTextarea } from 'tdesign-vue-next/es/textarea';\n"
            "export { Dialog as TDesignDialog } from 'tdesign-vue-next/es/dialog';\n"
            "export { Drawer as TDesignDrawer } from 'tdesign-vue-next/es/drawer';\n"
            "export { Empty as TDesignEmpty } from 'tdesign-vue-next/es/empty';\n",
            encoding="utf-8",
        )
        theme.write_text(
            ":root {\n"
            "  --td-bg-color-specialcomponent: var(--sc-semantic-surface-input);\n"
            "  --td-text-color-placeholder: var(--sc-semantic-text-muted);\n"
            "  --td-border-level-2-color: var(--sc-semantic-border-strong);\n"
            "}\n"
            ".sc-input.t-input__wrap[data-size='large'] > .t-input { min-height: calc(var(--sc-component-input-height-md) * 1px); }\n"
            ".sc-select[data-size='medium'] .t-input { min-height: calc(var(--sc-component-input-height-md) * 1px); }\n"
            ".sc-textarea .t-textarea__inner { min-height: calc(var(--sc-component-input-height-md) * 2px); }\n"
            ".sc-btn.t-button { height: calc(var(--sc-component-button-height-md) * 1px); }\n",
            encoding="utf-8",
        )
        for name in PRIMITIVES:
            overlay_kind = name.removeprefix("Sc").lower()
            modal_contract = (
                f'<TDesign{name.removeprefix("Sc")} role="dialog" aria-modal="true" data-overlay-kind="{overlay_kind}" '
                f':data-state="open ? \'open\' : \'closed\'" /><!-- --sc-component-{overlay_kind}-z-index -->'
                if name in {"ScDialog", "ScDrawer"} else ""
            )
            state_contract = {
                "ScButton": '<TDesignButton :data-loading="loading || undefined" :aria-disabled="disabled || loading || undefined" :loading="loading" /><!-- tdesignButtonPresentation -->',
                "ScCheckbox": '<TDesignCheckbox v-native-control-projection :data-checked="checked || undefined" :data-indeterminate="indeterminate || undefined" :data-disabled="disabled || undefined" /><!-- \'aria-checked\': props.indeterminate ? \'mixed\' : String(props.checked) \'aria-label\': props.label -->',
                "ScRadioGroup": '<TDesignRadioGroup :options="options" :aria-required="required || undefined" /><!-- semanticPrimitiveIdentity(\'ScRadioGroup\') -->',
                "ScRadio": '<TDesignRadio :checked="checked" :aria-required="required || undefined" /><!-- semanticPrimitiveIdentity(\'ScRadio\') -->',
                "ScInput": '<TDesignInput v-native-control-projection :data-loading="loading || undefined" :aria-busy="loading || undefined" :aria-describedby="describedBy" :aria-invalid="invalid" /><input data-primitive-driver="browser-specialized" />',
                "ScTextarea": '<TDesignTextarea v-native-control-projection :data-loading="loading || undefined" :aria-busy="loading || undefined" :aria-describedby="describedBy" :aria-invalid="invalid" />',
                "ScSelect": '<TDesignSelect v-native-control-projection :options="tdesignOptions" :data-readonly="readonly || undefined" :aria-readonly="readonly || undefined" />',
                "ScLoading": '<div data-state="loading" aria-busy="true" />',
                "ScInlineState": '<div :data-state="state" :aria-busy="state === \'loading\' || undefined" />',
                "ScEmptyState": '<TDesignEmpty data-state="empty" role="status" />',
                "ScErrorState": '<TDesignAlert data-state="error" role="alert" />',
                "ScFormField": '<label :data-state="state" :data-required="required" />',
            }.get(name, "")
            (design / f"{name}.vue").write_text(
                f'<template><div data-semantic-component="{name}" data-semantic-layer="primitive">{state_contract}</div></template>{modal_contract}\n',
                encoding="utf-8",
            )
        return root

    def test_valid_adapter_surface_passes(self) -> None:
        self.assertEqual(validate(self.make_root()), [])

    def test_missing_component_fails(self) -> None:
        root = self.make_root()
        (root / "frontend/apps/web/src/components/design-system/ScInput.vue").unlink()
        self.assertTrue(any("missing primitive source" in error for error in validate(root)))

    def test_private_tdesign_import_fails(self) -> None:
        root = self.make_root()
        bridge = root / "frontend/packages/ui/src/primitives.ts"
        bridge.write_text("export { Input } from 'tdesign-vue-next/src/input';\n", encoding="utf-8")
        self.assertTrue(any("public entrypoints" in error for error in validate(root)))

    def test_missing_semantic_identity_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScButton.vue"
        source.write_text("<template><button /></template>\n", encoding="utf-8")
        errors = validate(root)
        self.assertTrue(any("ScButton missing exact semantic" in error for error in errors))
        self.assertTrue(any("ScButton missing primitive layer" in error for error in errors))

    def test_business_identity_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScTable.vue"
        source.write_text(
            '<template><div data-semantic-component="ScTable" data-semantic-layer="primitive">payment.request</div></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("business-specific" in error for error in validate(root)))

    def test_modal_without_tdesign_driver_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScDrawer.vue"
        source.write_text(
            '<template><aside data-semantic-component="ScDrawer" data-semantic-layer="primitive" /></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("TDesign overlay driver" in error for error in validate(root)))

    def test_input_without_native_accessibility_fails(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScInput.vue"
        source.write_text(
            '<template><div data-semantic-component="ScInput" data-semantic-layer="primitive" /></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("native input control" in error for error in validate(root)))

    def test_interaction_state_markers_are_required(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScButton.vue"
        source.write_text(
            '<template><button data-semantic-component="ScButton" data-semantic-layer="primitive" /></template>\n',
            encoding="utf-8",
        )
        self.assertTrue(any("interaction-state marker" in error for error in validate(root)))

    def test_checkbox_indeterminate_state_markers_are_required(self) -> None:
        root = self.make_root()
        source = root / "frontend/apps/web/src/components/design-system/ScCheckbox.vue"
        source.write_text(
            '<template><label data-semantic-component="ScCheckbox" data-semantic-layer="primitive" '
            ':data-checked="checked || undefined" :data-disabled="disabled || undefined">'
            '<input type="checkbox" :aria-label="label" /></label></template>\n',
            encoding="utf-8",
        )
        errors = validate(root)
        self.assertTrue(any("data-indeterminate" in error for error in errors))
        self.assertTrue(any("aria-checked" in error for error in errors))

    def test_missing_visual_projection_fails(self) -> None:
        root = self.make_root()
        theme = root / "frontend/packages/ui/src/kits/tdesign/theme.css"
        theme.write_text(":root {}\n", encoding="utf-8")
        self.assertTrue(any("visual projection bridge missing marker" in error for error in validate(root)))

    def test_business_identity_in_visual_projection_fails(self) -> None:
        root = self.make_root()
        theme = root / "frontend/packages/ui/src/kits/tdesign/theme.css"
        theme.write_text(theme.read_text(encoding="utf-8") + "/* payment.request */\n", encoding="utf-8")
        self.assertTrue(any("visual projection bridge contains business-specific identity" in error for error in validate(root)))


if __name__ == "__main__":
    unittest.main()
