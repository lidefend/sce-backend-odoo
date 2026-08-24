from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.verify.frontend_navigation_shell_guard import COMPONENTS, ROOT, validate


PATHS = (
    "frontend/apps/web/src/layouts/AppShell.vue",
    "frontend/apps/web/src/components/MenuTree.vue",
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


if __name__ == "__main__":
    unittest.main()
