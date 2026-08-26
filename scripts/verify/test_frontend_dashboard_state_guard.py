import unittest

from scripts.verify.frontend_dashboard_state_guard import BLOCK_ROOT, BLOCKS, validate


class FrontendDashboardStateGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {key: (BLOCK_ROOT / name).read_text(encoding="utf-8") for key, name in BLOCKS.items()}

    def altered(self, key: str, old: str, new: str = "") -> dict[str, str]:
        sources = dict(self.sources)
        sources[key] = sources[key].replace(old, new, 1)
        return sources

    def test_repository_blocks_pass(self):
        self.assertEqual(validate(self.sources), [])

    def test_empty_state_is_required(self):
        self.assertTrue(any("empty state" in error for error in validate(self.altered("progress", "<ScEmptyState"))))

    def test_compact_density_is_required(self):
        self.assertTrue(any("compact" in error for error in validate(self.altered("table", 'density="compact"'))))

    def test_block_heading_hierarchy_is_required(self):
        self.assertTrue(any("heading hierarchy" in error for error in validate(self.altered("activity", ':heading-level="5"'))))

    def test_command_button_is_required(self):
        self.assertTrue(any("command buttons" in error for error in validate(self.altered("summary", "<ScButton"))))

    def test_raw_command_button_fails(self):
        self.assertTrue(any("raw command" in error for error in validate(self.altered("todo", "<ScButton", "<button"))))

    def test_compact_container_rule_is_required(self):
        self.assertTrue(any("container adaptation" in error for error in validate(self.altered("entry", "@container (max-width: 480px)"))))

    def test_focus_state_is_required(self):
        self.assertTrue(any("focus-visible" in error for error in validate(self.altered("metric", "button.metric-item:focus-visible"))))

    def test_reduced_motion_is_required(self):
        self.assertTrue(any("reduced-motion" in error for error in validate(self.altered("metric", "prefers-reduced-motion"))))


if __name__ == "__main__":
    unittest.main()
