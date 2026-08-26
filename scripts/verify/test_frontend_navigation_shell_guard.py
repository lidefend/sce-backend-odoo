from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_navigation_shell_guard import COMPONENTS, ROOT, validate


PATHS = (
    "frontend/apps/web/src/layouts/AppShell.vue",
    "frontend/apps/web/src/layouts/AppShell.css",
    "frontend/apps/web/src/components/MenuTree.vue",
    "frontend/apps/web/src/components/design-system/tdesignPrimitiveBridge.ts",
    "frontend/apps/web/src/components/product-shell/CanonicalNavigationMenuNode.vue",
    "frontend/packages/ui/src/primitives.ts",
    "frontend/packages/ui/src/kits/tdesign/theme.css",
    "frontend/apps/web/src/stores/session.ts",
    "frontend/apps/web/src/app/canonicalNavigation.ts",
    "addons/smart_core/delivery/menu_service.py",
    "addons/smart_core/handlers/system_init.py",
    *(f"frontend/apps/web/src/components/product-shell/{component}.vue" for component in COMPONENTS),
)


class FrontendNavigationShellGuardTest(unittest.TestCase):
    def fixture(self) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        for relative in PATHS:
            source = ROOT / relative
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return temporary, root

    def test_repository_candidate_passes(self):
        self.assertEqual(validate(), [])

    def test_missing_component_identity_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/product-shell/ProductAppShell.vue"
        path.write_text(path.read_text().replace('data-semantic-component="ProductAppShell"', ''), encoding="utf-8")
        self.assertTrue(any("exact semantic identity" in error for error in validate(root)))

    def test_menu_tree_session_authority_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/MenuTree.vue"
        path.write_text(path.read_text() + "\n// useSessionStore\n", encoding="utf-8")
        self.assertTrue(any("presentation-only" in error for error in validate(root)))

    def test_hand_built_menu_tree_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/MenuTree.vue"
        path.write_text(path.read_text() + "\n<template><ul><li><button>legacy</button></li></ul></template>\n", encoding="utf-8")
        self.assertTrue(any("hand-built menu" in error for error in validate(root)))

    def test_missing_standard_menu_driver_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/design-system/tdesignPrimitiveBridge.ts"
        path.write_text(path.read_text().replace("TDesignSubmenu,", ""), encoding="utf-8")
        self.assertTrue(any("project bridge: TDesignSubmenu" in error for error in validate(root)))

    def test_parallel_navigation_component_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/product-shell/PrimaryNavigation.vue"
        path.write_text("<template><nav /></template>\n", encoding="utf-8")
        self.assertTrue(any("parallel shell authority" in error for error in validate(root)))

    def test_business_identity_in_shell_component_fails(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue"
        path.write_text(path.read_text() + "\n<!-- project.project -->\n", encoding="utf-8")
        self.assertTrue(any("business-specific identity" in error for error in validate(root)))

    def test_backend_projection_order_fails_closed(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "addons/smart_core/handlers/system_init.py"
        path.write_text(path.read_text().replace("project_canonical_navigation(", "removed_projection("), encoding="utf-8")
        self.assertTrue(any("filter authority" in error for error in validate(root)))

    def test_sidebar_child_root_must_keep_bounded_scroll_style(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/layouts/AppShell.css"
        path.write_text(path.read_text().replace(".shell :deep(.sidebar)", ".sidebar"), encoding="utf-8")
        self.assertTrue(any("deep boundary" in error for error in validate(root)))

    def test_desktop_sidebar_must_not_restore_parallel_activity_rail(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/layouts/AppShell.css"
        source = path.read_text().replace(
            "grid-template-columns: minmax(0, 1fr);\n    border-right-color",
            "grid-template-columns: 48px minmax(0, 1fr);\n    border-right-color",
        )
        path.write_text(source, encoding="utf-8")
        self.assertTrue(any("single-column" in error for error in validate(root)))

    def test_company_context_must_remain_visible_after_activity_rail_retirement(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/layouts/AppShell.vue"
        path.write_text(
            path.read_text().replace(
                "          <WorkspaceContextIndicator\n",
                '          <WorkspaceContextIndicator\n            v-if="showRecordContext"\n',
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("company context authority visible" in error for error in validate(root)))

    def test_published_apps_must_target_the_sc_button_content_adapter(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/layouts/AppShell.css"
        path.write_text(
            path.read_text().replace(
                ".published-app > .t-button__text > .sc-btn__content)",
                ".published-app > .t-button__text)",
            ),
            encoding="utf-8",
        )
        self.assertTrue(any("ScButton content adapter" in error for error in validate(root)))

    def test_navigation_search_must_use_the_input_prefix_adapter(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue"
        path.write_text(
            path.read_text().replace(
                '<template #prefix><ScIcon name="search" :size="16" /></template>',
                '',
            ).replace("        clearable\n", ""),
            encoding="utf-8",
        )
        self.assertTrue(any("canonical rendering detail" in error for error in validate(root)))

    def test_navigation_search_visual_chrome_cannot_return_to_the_page_component(self):
        temporary, root = self.fixture()
        self.addCleanup(temporary.cleanup)
        path = root / "frontend/apps/web/src/components/product-shell/ProductSideNavigation.vue"
        path.write_text(path.read_text() + "\n<style>.x { border-color: red; }</style>\n", encoding="utf-8")
        self.assertIn("ProductSideNavigation must not own ScInput visual chrome", validate(root))


if __name__ == "__main__":
    unittest.main()
