#!/usr/bin/env python3
from __future__ import annotations

import re
import unittest


TOGGLE_PATTERN = re.compile(
    r"<button\b(?=[^>]*\baria-controls=\"primary-sidebar\")"
    r"(?=[^>]*:aria-expanded=\"sidebarVisible\")[^>]*>",
    re.DOTALL,
)


class AppShellSidebarSemanticsTest(unittest.TestCase):
    def test_unified_visibility_state_controls_the_named_region(self):
        source = """
        <button aria-controls="primary-sidebar"
                :aria-expanded="sidebarVisible"></button>
        """
        self.assertIsNotNone(TOGGLE_PATTERN.search(source))

    def test_old_desktop_only_state_is_rejected(self):
        source = """
        <button aria-controls="primary-sidebar"
                :aria-expanded="!sidebarHidden"></button>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))

    def test_unrelated_aria_expanded_marker_is_rejected(self):
        source = """
        <button aria-controls="other-panel"
                :aria-expanded="sidebarVisible"></button>
        """
        self.assertIsNone(TOGGLE_PATTERN.search(source))


if __name__ == "__main__":
    unittest.main()
