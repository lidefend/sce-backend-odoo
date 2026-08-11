from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.verify import frontend_tdesign_boundary_guard as guard


class TDesignImportBoundaryTests(unittest.TestCase):
    def test_accepts_adapter_only_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            adapter = src / "components/design-system/tdesignAdapter.ts"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("export { Button } from 'tdesign-vue-next';", encoding="utf-8")
            page = src / "pages/Page.vue"
            page.parent.mkdir(parents=True)
            page.write_text("import { TButton } from '../components/design-system/tdesignAdapter';", encoding="utf-8")
            self.assertEqual(guard.collect_direct_imports(src, src, adapter.resolve()), [])

    def test_rejects_page_direct_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            adapter = src / "components/design-system/tdesignAdapter.ts"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("export { Button } from 'tdesign-vue-next';", encoding="utf-8")
            page = src / "pages/Page.vue"
            page.parent.mkdir(parents=True)
            page.write_text("import { Button } from 'tdesign-vue-next';", encoding="utf-8")
            self.assertEqual(guard.collect_direct_imports(src, src, adapter.resolve()), ["pages/Page.vue"])

    def test_rejects_icon_direct_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            adapter = src / "components/design-system/tdesignAdapter.ts"
            adapter.parent.mkdir(parents=True)
            adapter.write_text("export { SearchIcon } from 'tdesign-icons-vue-next';", encoding="utf-8")
            consumer = src / "components/SearchAction.ts"
            consumer.parent.mkdir(parents=True, exist_ok=True)
            consumer.write_text("import { SearchIcon } from 'tdesign-icons-vue-next';", encoding="utf-8")
            self.assertEqual(
                guard.collect_direct_imports(src, src, adapter.resolve()),
                ["components/SearchAction.ts"],
            )

    def test_data_entry_guard_rejects_unadapted_controls(self) -> None:
        for source in (
            '<input type="text" />',
            '<input type="search" />',
            '<select><option>one</option></select>',
            '<textarea rows="3"></textarea>',
        ):
            self.assertIsNotNone(guard.UNADAPTED_DATA_ENTRY_RE.search(source), source)

    def test_data_entry_guard_keeps_controlled_native_exceptions(self) -> None:
        for source in ('<input type="radio" />', '<input type="file" />'):
            self.assertIsNone(guard.UNADAPTED_DATA_ENTRY_RE.search(source), source)

    def test_full_source_data_entry_scan_reports_every_unadapted_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            (src / "pages").mkdir()
            (src / "pages/Text.vue").write_text('<template><input type="text" /></template>', encoding="utf-8")
            (src / "pages/Select.vue").write_text('<template><select /></template>', encoding="utf-8")
            (src / "pages/Allowed.vue").write_text('<template><input type="file" /></template>', encoding="utf-8")
            self.assertEqual(
                guard.collect_unadapted_data_entry_controls(src, src),
                ["pages/Select.vue", "pages/Text.vue"],
            )

    def test_full_source_data_entry_scan_allows_framework_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            (src / "ScFixture.vue").write_text(
                '<template><ScTextField/><ScSelect/><ScTextArea/><ScMultiSelect/></template>',
                encoding="utf-8",
            )
            self.assertEqual(guard.collect_unadapted_data_entry_controls(src, src), [])

    def test_native_control_inventory_is_structured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            src = Path(directory)
            (src / 'Fixture.vue').write_text(
                '<template><button/><input type="file"/><select/><textarea/><table/></template>',
                encoding='utf-8',
            )
            self.assertEqual(
                guard.collect_native_control_inventory(src),
                {"button": 1, "input": 1, "select": 1, "textarea": 1, "table": 1},
            )

    def test_real_product_audit_uses_unified_page_contract(self) -> None:
        audit = guard.PRODUCT_DESIGN_AUDIT.read_text(encoding="utf-8")
        self.assertNotIn('.financial-workspace[data-workspace-kind=', audit)
        self.assertIn('main [data-product-page-mode="form"]', audit)
        self.assertIn("payload.intent === 'ui.contract.v2'", audit)


if __name__ == "__main__":
    unittest.main()
