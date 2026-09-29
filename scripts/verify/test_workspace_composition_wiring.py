import unittest
from pathlib import Path
from scripts.verify.frontend_home_layout_section_coverage_guard import workspace_section_errors
from scripts.verify.frontend_home_orchestration_consumption_guard import has_role_inference

ROOT = Path(__file__).resolve().parents[2] / 'frontend/apps/web/src/components'
class WorkspaceCompositionWiringTest(unittest.TestCase):
    def setUp(self):
        self.home = (ROOT / 'role-home/WorkspaceHome.vue').read_text()
        self.work = (ROOT / 'business/MyWorkApprovalWorkspace.vue').read_text()
        self.surface = (ROOT / 'product-page-patterns/ProductWorkspaceSurface.vue').read_text()
    def test_production_wiring(self):
        self.assertEqual(workspace_section_errors(self.home, self.work, self.surface), [])
    def test_home_cannot_lose_summary(self):
        self.assertTrue(workspace_section_errors(self.home.replace('<template #summary>', ''), self.work, self.surface))
    def test_home_cannot_lose_entries(self):
        self.assertTrue(workspace_section_errors(self.home.replace('<template #secondary>', ''), self.work, self.surface))
    def test_work_cannot_lose_query(self):
        self.assertTrue(workspace_section_errors(self.home, self.work.replace('<template #query>', ''), self.surface))
    def test_shared_cannot_drop_content(self):
        self.assertTrue(workspace_section_errors(self.home, self.work, self.surface.replace('<slot />', '')))
    def test_shared_cannot_drop_actions(self):
        self.assertTrue(workspace_section_errors(self.home, self.work, self.surface.replace('<slot name="main-actions" />', '')))

    def test_declared_fact_display_role_is_not_role_inference(self):
        self.assertFalse(has_role_inference("fact.display_role === 'money'"))
    def test_role_inference_still_rejected(self):
        self.assertTrue(has_role_inference("role === 'finance'"))
        self.assertTrue(has_role_inference("row.role_code === 'owner'"))
