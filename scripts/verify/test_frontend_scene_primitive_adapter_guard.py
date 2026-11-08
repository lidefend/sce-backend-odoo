from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_scene_primitive_adapter_guard import validate


class ScenePrimitiveAdapterGuardTest(unittest.TestCase):
    def make_root(self) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        adapter = root / "frontend/apps/web/src/components/design-system/scene-adapter"
        adapter.mkdir(parents=True)
        (adapter / "ScSceneButton.vue").write_text(
            """
<template>
  <ScButton
    :aria-label="accessibleLabel"
    @click="onClick"
  ><slot /></ScButton>
</template>
<script setup lang="ts">
import type { ButtonPortEmits, ButtonPortProps, ButtonPortSlots } from '@sc/ui/primitive-port';
import ScButton from '../ScButton.vue';
const props = defineProps<ButtonPortProps>();
const emit = defineEmits<ButtonPortEmits>();
defineSlots<ButtonPortSlots>();
function onClick(event: MouseEvent) {
  if (props.disabled || props.loading) return;
  emit('activate', { source: 'pointer', nativeEvent: event });
}
</script>
""",
            encoding="utf-8",
        )
        (adapter / "buttonContract.ts").write_text(
            """
import ScSceneButton from './ScSceneButton.vue';
export const scSceneButtonContract = {
  primitive: 'Button',
  portVersion: 1,
  capabilities: ['activate', 'focus', 'blur', 'keyboard', 'loading'],
};
export const scSceneButtonBinding = { component: ScSceneButton, contract: scSceneButtonContract };
""",
            encoding="utf-8",
        )
        (adapter / "index.ts").write_text(
            """
export { default as ScSceneButton } from './ScSceneButton.vue';
export { scSceneButtonBinding, scSceneButtonContract } from './buttonContract';
""",
            encoding="utf-8",
        )
        return root

    def test_valid_adapter_structure_passes(self) -> None:
        self.assertEqual(validate(self.make_root()), [])

    def test_missing_wrapper_fails(self) -> None:
        root = self.make_root()
        (root / "frontend/apps/web/src/components/design-system/scene-adapter/ScSceneButton.vue").unlink()
        self.assertTrue(any("missing scene-adapter files" in error for error in validate(root)))

    def test_vendor_import_escapes_authority(self) -> None:
        root = self.make_root()
        contract = root / "frontend/apps/web/src/components/design-system/scene-adapter/buttonContract.ts"
        contract.write_text(
            "import { Button } from 'tdesign-vue-next';\n" + contract.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.assertTrue(any("escapes the Sc/Port authority" in error for error in validate(root)))

    def test_compatibility_cast_fails(self) -> None:
        root = self.make_root()
        contract = root / "frontend/apps/web/src/components/design-system/scene-adapter/buttonContract.ts"
        contract.write_text(
            "declare const candidate: unknown;\n"
            "const proof = candidate as PrimitiveBinding<{}, {}, {}>;\n"
            + contract.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        self.assertTrue(any("compatibility cast" in error for error in validate(root)))

    def test_bundle_requires_real_sc_button_and_rejects_pages(self) -> None:
        root = self.make_root()
        metafile = root / "metafile.json"
        metafile.write_text(json.dumps({
            "inputs": {
                "frontend/apps/web/src/components/design-system/scene-adapter/ScSceneButton.vue": {},
                "frontend/apps/web/src/components/design-system/ScButton.vue": {},
                "frontend/apps/web/src/pages/ListPage.vue": {},
            },
        }), encoding="utf-8")
        errors = validate(root, metafile)
        self.assertTrue(any("forbidden input" in error for error in errors))

    def test_product_consumer_invalidates_fixture_only_exemption(self) -> None:
        root = self.make_root()
        page = root / "frontend/apps/web/src/pages/Consumer.vue"
        page.parent.mkdir(parents=True)
        page.write_text(
            "<script setup lang=\"ts\">\n"
            "import { ScSceneButton } from '../components/design-system/scene-adapter';\n"
            "</script>\n",
            encoding="utf-8",
        )
        self.assertTrue(any("fixture-only primitive adapter" in error for error in validate(root)))


if __name__ == "__main__":
    unittest.main()
