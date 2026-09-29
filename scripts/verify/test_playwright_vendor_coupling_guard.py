from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from scripts.verify.playwright_vendor_coupling_guard import (
    RULE_DOM_PSEUDO,
    RULE_GEOMETRY,
    RULE_TRANSITION,
    RULE_VENDOR,
    ZERO_TOLERANCE_RULES,
    scan_file,
    scope_files,
    selector_targets_vendor_internals,
)


class SelectorRuleTest(unittest.TestCase):
    def test_descendant_vendor_coupling_is_rejected(self) -> None:
        for selector in (
            ".t-popup",
            ".t-popup:visible",
            ".tree-scroll .t-tree__item",
            ".sc-table .t-table__body",
            "[data-semantic-component='ScInlineState'] .t-alert__content",
        ):
            with self.subTest(selector=selector):
                self.assertTrue(selector_targets_vendor_internals(selector))

    def test_sc_root_compound_stays_allowed(self) -> None:
        for selector in (
            ".tree-scroll [trigger='expand']",
            ".sc-menu-config.t-menu",
            "[data-semantic-component='ScInlineState']",
            ".tree-node[data-menu-id]",
        ):
            with self.subTest(selector=selector):
                self.assertFalse(selector_targets_vendor_internals(selector))


class ScanRuleTest(unittest.TestCase):
    def scan(self, source: str) -> dict[str, list[str]]:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "probe.mjs"
        path.write_text(source, encoding="utf-8")
        return scan_file(path, label="probe.mjs")

    def test_transition_state_class_is_zero_tolerance(self) -> None:
        findings = self.scan("await page.waitForSelector('.t-tree__item--enter-active');\n")
        self.assertEqual(len(findings[RULE_TRANSITION]), 1)
        self.assertEqual(findings[RULE_TRANSITION][0], "probe.mjs:1")

    def test_playwright_pseudo_in_dom_api_is_zero_tolerance(self) -> None:
        findings = self.scan("const rows = document.querySelectorAll('.t-popup:visible');\n")
        self.assertEqual(len(findings[RULE_DOM_PSEUDO]), 1)

    def test_settled_state_probe_stays_clean(self) -> None:
        source = (
            "const node = page.locator('.tree-node[data-menu-id=\"545\"]');\n"
            "await expect(node).toHaveAttribute('data-menu-expanded', 'true');\n"
        )
        findings = self.scan(source)
        for rule in (*ZERO_TOLERANCE_RULES, RULE_VENDOR, RULE_GEOMETRY):
            with self.subTest(rule=rule):
                self.assertEqual(findings[rule], [])

    def test_vendor_literal_and_geometry_are_recorded(self) -> None:
        source = (
            "const panel = page.locator('.t-popup');\n"
            "const box = await panel.boundingBox();\n"
            "const height = element.getBoundingClientRect().height;\n"
        )
        findings = self.scan(source)
        self.assertEqual(len(findings[RULE_VENDOR]), 1)
        self.assertEqual(findings[RULE_GEOMETRY], ["probe.mjs:3"])

    def test_rule_definition_file_is_not_self_scanned(self) -> None:
        self_path = Path(__file__).resolve().parent / "playwright_vendor_coupling_guard.py"
        self.assertNotIn(self_path, {path.resolve() for path in scope_files()})
        self.assertIn(
            Path("scripts/verify/menu_config_tree_editor_behavior_guard.ts"),
            {path.relative_to(Path(__file__).resolve().parents[2]) for path in scope_files()},
        )


if __name__ == "__main__":
    unittest.main()
